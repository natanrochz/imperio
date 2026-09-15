from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.analises.models import Analise, CategoriaStatus, StatusAnalise
from apps.empresas.models import Empresa

STATUS_PADRAO: tuple[tuple[str, str], ...] = (
    ("Em análise", CategoriaStatus.EM_ANALISE),
    ("Pendente", CategoriaStatus.PENDENTE),
    ("Aprovado", CategoriaStatus.APROVADO),
    ("Reprovado", CategoriaStatus.REPROVADO),
    ("Cancelado", CategoriaStatus.CANCELADO),
)


class ConflitoDeVersao(Exception):
    """A análise mudou no banco desde que este request a carregou."""


@transaction.atomic
def criar_status_padrao(empresa: Empresa) -> list[StatusAnalise]:
    """Cria os status iniciais de uma empresa nova.

    Chamado explicitamente por quem cria a empresa, nunca por `post_save`: assim a
    criação aparece no fluxo, pode ser testada isoladamente e pulada quando a
    empresa for cadastrada com um conjunto próprio de status.
    """
    return StatusAnalise.objects.bulk_create(
        [
            StatusAnalise(empresa=empresa, nome=nome, categoria=categoria, ordem=ordem)
            for ordem, (nome, categoria) in enumerate(STATUS_PADRAO)
        ]
    )


def registrar_resultado(
    *,
    analise: Analise,
    status: StatusAnalise,
    analista: User,
    versao: int,
    observacoes: str = "",
) -> Analise:
    """Grava o resultado da análise com bloqueio otimista.

    O UPDATE condicionado à versão que o request leu é o que impede lost update
    entre dois POSTs sequenciais: o segundo não encontra linha e falha, em vez de
    sobrescrever silenciosamente o resultado do primeiro.

    `QuerySet.update()` não dispara `auto_now`, daí `atualizado_em` explícito.
    """
    linhas = Analise.objects.filter(pk=analise.pk, versao=versao).update(
        status=status,
        analista=analista,
        observacoes=observacoes,
        versao=versao + 1,
        atualizado_em=timezone.now(),
    )
    if linhas == 0:
        raise ConflitoDeVersao(
            f"A análise {analise.uuid} foi alterada por outro usuário desde que você a abriu."
        )
    analise.refresh_from_db()
    return analise
