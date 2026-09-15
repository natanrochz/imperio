from datetime import date
from decimal import Decimal

from django.db import DataError, IntegrityError, transaction
from django.test import TestCase

from apps.empresas.models import Empresa
from apps.pessoas.models import Pessoa

CPF = "12345678901"


def criar_empresa(nome: str, cnpj: str) -> Empresa:
    return Empresa.objects.create(nome=nome, cnpj=cnpj)


def dados_pessoa(**overrides) -> dict:
    base = {
        "nome_completo": "Maria Silva",
        "cpf": CPF,
        "data_nascimento": date(1990, 5, 20),
        "renda_mensal": Decimal("4500.00"),
    }
    return base | overrides


class PessoaCPFTests(TestCase):
    """CPF é único por empresa, nunca global: duas empresas podem ter a mesma pessoa."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = criar_empresa("Acme", "12345678000199")
        cls.globex = criar_empresa("Globex", "98765432000188")

    def test_cpf_duplicado_na_mesma_empresa_e_rejeitado(self) -> None:
        Pessoa.objects.create(empresa=self.acme, **dados_pessoa())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pessoa.objects.create(empresa=self.acme, **dados_pessoa(nome_completo="Outra"))

    def test_mesmo_cpf_em_empresas_diferentes_e_permitido(self) -> None:
        Pessoa.objects.create(empresa=self.acme, **dados_pessoa())
        Pessoa.objects.create(empresa=self.globex, **dados_pessoa())
        self.assertEqual(Pessoa.objects.filter(cpf=CPF).count(), 2)


class PessoaConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.empresa = criar_empresa("Acme", "12345678000199")

    def test_cpf_nao_numerico_e_rejeitado(self) -> None:
        """11 caracteres, mas não todos dígitos: quem barra é a check constraint."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pessoa.objects.create(empresa=self.empresa, **dados_pessoa(cpf="1234567890a"))

    def test_cpf_com_mascara_nao_cabe_no_campo(self) -> None:
        """Máscara tem 14 caracteres: o varchar(11) barra antes da check constraint,
        então o erro é DataError, não IntegrityError."""
        with self.assertRaises(DataError), transaction.atomic():
            Pessoa.objects.create(empresa=self.empresa, **dados_pessoa(cpf="123.456.789-01"))

    def test_cpf_com_menos_de_onze_digitos_e_rejeitado(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pessoa.objects.create(empresa=self.empresa, **dados_pessoa(cpf="1234567890"))

    def test_renda_negativa_e_rejeitada(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pessoa.objects.create(empresa=self.empresa, **dados_pessoa(renda_mensal=Decimal("-1.00")))

    def test_renda_zero_e_permitida(self) -> None:
        pessoa = Pessoa.objects.create(empresa=self.empresa, **dados_pessoa(renda_mensal=Decimal("0.00")))
        self.assertEqual(pessoa.renda_mensal, Decimal("0.00"))
