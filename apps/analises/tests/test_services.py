from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.analises.models import Analise, CategoriaStatus, StatusAnalise
from apps.analises.services import (
    STATUS_PADRAO,
    ConflitoDeVersao,
    criar_status_padrao,
    registrar_resultado,
)
from apps.empresas.models import Empresa
from apps.pessoas.models import Pessoa

SENHA = "senha-de-teste-bem-longa"


class StatusPadraoTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.empresa = Empresa.objects.create(nome="Acme", cnpj="12345678000199")

    def test_cria_um_status_por_categoria(self) -> None:
        criar_status_padrao(self.empresa)
        categorias = set(StatusAnalise.objects.values_list("categoria", flat=True))
        self.assertEqual(categorias, set(CategoriaStatus.values))

    def test_ordem_segue_a_sequencia_declarada(self) -> None:
        criar_status_padrao(self.empresa)
        nomes = list(StatusAnalise.objects.order_by("ordem").values_list("nome", flat=True))
        self.assertEqual(nomes, [nome for nome, _ in STATUS_PADRAO])

    def test_chamar_duas_vezes_viola_a_unique_de_nome(self) -> None:
        criar_status_padrao(self.empresa)
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_status_padrao(self.empresa)

    def test_empresas_diferentes_tem_seus_proprios_status(self) -> None:
        outra = Empresa.objects.create(nome="Globex", cnpj="98765432000188")
        criar_status_padrao(self.empresa)
        criar_status_padrao(outra)
        self.assertEqual(StatusAnalise.objects.filter(empresa=outra).count(), len(STATUS_PADRAO))


class RegistrarResultadoTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.empresa = Empresa.objects.create(nome="Acme", cnpj="12345678000199")
        criar_status_padrao(cls.empresa)
        cls.em_analise = StatusAnalise.objects.get(empresa=cls.empresa, categoria=CategoriaStatus.EM_ANALISE)
        cls.aprovado = StatusAnalise.objects.get(empresa=cls.empresa, categoria=CategoriaStatus.APROVADO)
        cls.reprovado = StatusAnalise.objects.get(empresa=cls.empresa, categoria=CategoriaStatus.REPROVADO)
        cls.analista = User.objects.create_user(
            email="analista@exemplo.com", password=SENHA, nome_completo="Ana Analista"
        )
        cls.consorciorista = User.objects.create_user(
            email="consorciorista@exemplo.com", password=SENHA, nome_completo="Bruno"
        )
        cls.pessoa = Pessoa.objects.create(
            empresa=cls.empresa,
            nome_completo="Maria Silva",
            cpf="12345678901",
            data_nascimento=date(1990, 5, 20),
            renda_mensal=Decimal("4500.00"),
        )

    def criar_analise(self) -> Analise:
        return Analise.objects.create(
            empresa=self.empresa,
            pessoa=self.pessoa,
            consorciorista=self.consorciorista,
            status=self.em_analise,
            valor_solicitado=Decimal("250000.00"),
        )

    def test_grava_resultado_e_incrementa_versao(self) -> None:
        analise = self.criar_analise()
        atualizada = registrar_resultado(
            analise=analise, status=self.aprovado, analista=self.analista, versao=analise.versao
        )
        self.assertEqual(atualizada.status, self.aprovado)
        self.assertEqual(atualizada.analista, self.analista)
        self.assertEqual(atualizada.versao, 1)

    def test_segundo_post_com_versao_velha_nao_sobrescreve_o_primeiro(self) -> None:
        """Dois analistas abrem a mesma análise na versão 0 e salvam em sequência.
        O segundo precisa falhar, não apagar o resultado do primeiro."""
        analise = self.criar_analise()
        versao_que_os_dois_leram = analise.versao

        registrar_resultado(
            analise=analise,
            status=self.aprovado,
            analista=self.analista,
            versao=versao_que_os_dois_leram,
        )

        with self.assertRaises(ConflitoDeVersao):
            registrar_resultado(
                analise=analise,
                status=self.reprovado,
                analista=self.analista,
                versao=versao_que_os_dois_leram,
            )

        analise.refresh_from_db()
        self.assertEqual(analise.status, self.aprovado)
        self.assertEqual(analise.versao, 1)

    def test_atualizado_em_avanca_mesmo_usando_update(self) -> None:
        """QuerySet.update() não dispara auto_now; o service passa o valor na mão."""
        analise = self.criar_analise()
        antes = analise.atualizado_em
        atualizada = registrar_resultado(
            analise=analise, status=self.aprovado, analista=self.analista, versao=analise.versao
        )
        self.assertGreater(atualizada.atualizado_em, antes)
