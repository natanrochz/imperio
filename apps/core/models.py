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


class TimestampedModel(models.Model):
    """Carimbo de criação e atualização.

    `atualizado_em` usa `auto_now`, que o Django aplica no `save()` do model —
    `QuerySet.update()` **não** dispara. Quem usa `update()` (a trava otimista de
    `Analise`, por exemplo) precisa passar `atualizado_em` explicitamente.
    """

    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        abstract = True
