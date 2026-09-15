from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.analises.models import Analise, CategoriaStatus, StatusAnalise
from apps.empresas.models import Empresa
from apps.pessoas.models import Pessoa

SENHA = "senha-de-teste-bem-longa"


class AnaliseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.empresa = Empresa.objects.create(nome="Acme", cnpj="12345678000199")
        cls.consorciorista = User.objects.create_user(
            email="consorciorista@exemplo.com", password=SENHA, nome_completo="Ana"
        )
        cls.pessoa = Pessoa.objects.create(
            empresa=cls.empresa,
            nome_completo="Maria Silva",
            cpf="12345678901",
            data_nascimento=date(1990, 5, 20),
            renda_mensal=Decimal("4500.00"),
        )
        cls.status = StatusAnalise.objects.create(
            empresa=cls.empresa, nome="Em análise", categoria=CategoriaStatus.EM_ANALISE
        )

    def criar_analise(self, **overrides) -> Analise:
        base = {
            "empresa": self.empresa,
            "pessoa": self.pessoa,
            "consorciorista": self.consorciorista,
            "status": self.status,
            "valor_solicitado": Decimal("250000.00"),
        }
        return Analise.objects.create(**(base | overrides))


class StatusAnaliseTests(AnaliseTestCase):
    def test_nome_duplicado_na_mesma_empresa_e_rejeitado(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            StatusAnalise.objects.create(
                empresa=self.empresa, nome="Em análise", categoria=CategoriaStatus.PENDENTE
            )

    def test_mesmo_nome_em_empresas_diferentes_e_permitido(self) -> None:
        outra = Empresa.objects.create(nome="Globex", cnpj="98765432000188")
        StatusAnalise.objects.create(empresa=outra, nome="Em análise", categoria=CategoriaStatus.EM_ANALISE)
        self.assertEqual(StatusAnalise.objects.filter(nome="Em análise").count(), 2)


class AnaliseConstraintTests(AnaliseTestCase):
    def test_valor_zero_e_rejeitado(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_analise(valor_solicitado=Decimal("0.00"))

    def test_valor_negativo_e_rejeitado(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_analise(valor_solicitado=Decimal("-1.00"))

    def test_versao_comeca_em_zero(self) -> None:
        self.assertEqual(self.criar_analise().versao, 0)

    def test_analista_e_opcional(self) -> None:
        self.assertIsNone(self.criar_analise().analista)


class AnaliseReencaminhamentoTests(AnaliseTestCase):
    """O consorciorista fica na análise, não na pessoa: a mesma pessoa pode ser
    reencaminhada por outro consorciorista sem que o primeiro perca o histórico."""

    def test_mesma_pessoa_encaminhada_por_dois_consorcioristas(self) -> None:
        outro = User.objects.create_user(email="outro@exemplo.com", password=SENHA, nome_completo="Bruno")
        primeira = self.criar_analise()
        segunda = self.criar_analise(consorciorista=outro)

        self.assertEqual(self.pessoa.analises.count(), 2)
        self.assertEqual(primeira.consorciorista, self.consorciorista)
        self.assertEqual(segunda.consorciorista, outro)

    def test_str_nao_consulta_a_pessoa(self) -> None:
        analise = self.criar_analise()
        analise = Analise.objects.get(pk=analise.pk)
        with self.assertNumQueries(0):
            str(analise)
