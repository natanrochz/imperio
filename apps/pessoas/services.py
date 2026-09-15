from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from apps.core.db import nome_da_constraint
from apps.empresas.models import Empresa
from apps.pessoas.models import Pessoa


class CPFJaCadastrado(Exception):
    """Já existe pessoa com esse CPF nesta empresa."""

    def __init__(self, cpf: str) -> None:
        self.cpf = cpf
        super().__init__(f"CPF {cpf} já cadastrado nesta empresa.")


def criar_pessoa(*, empresa: Empresa, cpf: str, **campos: Any) -> Pessoa:
    """Cria a pessoa deixando o banco arbitrar a duplicata de CPF.

    Um `filter(cpf=...).exists()` antes do insert seria race condition: dois
    requests simultâneos passariam os dois pela checagem e o segundo estouraria
    sem tratamento. Aqui o insert é tentado e só o `IntegrityError` da constraint
    de CPF vira erro de domínio — qualquer outra violação é relançada.
    """
    try:
        with transaction.atomic():
            return Pessoa.objects.create(empresa=empresa, cpf=cpf, **campos)
    except IntegrityError as exc:
        if nome_da_constraint(exc) == "uniq_pessoa_empresa_cpf":
            raise CPFJaCadastrado(cpf) from exc
        raise
