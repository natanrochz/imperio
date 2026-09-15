from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.empresas.models import Empresa
from apps.pessoas.models import Pessoa
from apps.pessoas.services import CPFJaCadastrado, criar_pessoa

CAMPOS = {
    "nome_completo": "Maria Silva",
    "data_nascimento": date(1990, 5, 20),
    "renda_mensal": Decimal("4500.00"),
}


class CriarPessoaTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Empresa.objects.create(nome="Acme", cnpj="12345678000199")
        cls.globex = Empresa.objects.create(nome="Globex", cnpj="98765432000188")

    def test_cria_pessoa(self) -> None:
        pessoa = criar_pessoa(empresa=self.acme, cpf="12345678901", **CAMPOS)
        self.assertEqual(Pessoa.objects.count(), 1)
        self.assertEqual(pessoa.empresa, self.acme)

    def test_cpf_repetido_na_empresa_vira_erro_de_dominio(self) -> None:
        criar_pessoa(empresa=self.acme, cpf="12345678901", **CAMPOS)
        with self.assertRaises(CPFJaCadastrado) as ctx:
            criar_pessoa(empresa=self.acme, cpf="12345678901", **CAMPOS)
        self.assertEqual(ctx.exception.cpf, "12345678901")

    def test_mesmo_cpf_em_outra_empresa_passa(self) -> None:
        criar_pessoa(empresa=self.acme, cpf="12345678901", **CAMPOS)
        criar_pessoa(empresa=self.globex, cpf="12345678901", **CAMPOS)
        self.assertEqual(Pessoa.objects.count(), 2)

    def test_outra_violacao_nao_e_confundida_com_cpf_duplicado(self) -> None:
        """Renda negativa viola outra constraint: o service relança em vez de
        rotular como CPF duplicado."""
        with self.assertRaises(IntegrityError) as ctx:
            criar_pessoa(
                empresa=self.acme,
                cpf="12345678901",
                **(CAMPOS | {"renda_mensal": Decimal("-1.00")}),
            )
        self.assertNotIsInstance(ctx.exception, CPFJaCadastrado)

    def test_transacao_nao_fica_quebrada_apos_duplicata(self) -> None:
        """O atomic() interno permite continuar usando a conexão depois do erro."""
        criar_pessoa(empresa=self.acme, cpf="12345678901", **CAMPOS)
        with self.assertRaises(CPFJaCadastrado):
            criar_pessoa(empresa=self.acme, cpf="12345678901", **CAMPOS)
        criar_pessoa(empresa=self.acme, cpf="99999999999", **CAMPOS)
        self.assertEqual(Pessoa.objects.count(), 2)
