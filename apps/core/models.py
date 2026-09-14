from __future__ import annotations

from uuid import uuid4

from django.db import models


class UUIDModel(models.Model):
    """Identificador público para expor em URL, sem revelar contagem de registros.

    A PK continua BigAutoField: é menor, sequencial e melhor para índice e FK.
    `unique=True` já cria o índice — `db_index=True` junto geraria índice duplicado.
    """

    uuid = models.UUIDField("identificador público", default=uuid4, unique=True, editable=False)

    class Meta:
        abstract = True
