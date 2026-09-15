from __future__ import annotations

from django.db import IntegrityError


def nome_da_constraint(exc: IntegrityError) -> str | None:
    """Nome da constraint que o Postgres violou, ou None se não der para saber.

    Permite reagir à regra específica que falhou em vez de tratar todo
    `IntegrityError` como a mesma coisa. Depende de o psycopg expor `diag` na
    exceção original — se um dia não expuser, o chamador deve relançar.
    """
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)
