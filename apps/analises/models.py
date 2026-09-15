from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class CategoriaStatus(models.TextChoices):
    """Fixa em código. Toda agregação e regra de negócio usa `categoria`, nunca `nome`."""

    EM_ANALISE = "em_analise", "Em análise"
    PENDENTE = "pendente", "Pendente"
    APROVADO = "aprovado", "Aprovado"
    REPROVADO = "reprovado", "Reprovado"
    CANCELADO = "cancelado", "Cancelado"


class StatusAnalise(TimestampedModel):
    """Rótulo configurável por empresa, ancorado numa categoria fixa.

    Sem `uuid`: é configuração, não vira rota própria — mesmo critério de `Membership`.
    """

    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="status_analise",
        # Coberto pelo prefixo de idx_status_empresa_categoria e uniq_status_empresa_nome.
        db_index=False,
    )
    nome = models.CharField("nome", max_length=50)
    categoria = models.CharField("categoria", max_length=20, choices=CategoriaStatus.choices)
    ordem = models.PositiveSmallIntegerField("ordem", default=0)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "status de análise"
        verbose_name_plural = "status de análise"
        ordering = ["ordem", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nome"], name="uniq_status_empresa_nome"),
        ]
        indexes = [
            models.Index(fields=["empresa", "categoria"], name="idx_status_empresa_categoria"),
        ]

    def __str__(self) -> str:
        return self.nome


class Analise(UUIDModel, TimestampedModel):
    """Uma análise de crédito. `empresa` é denormalizada de `Pessoa` para permitir
    índice composto com `empresa_id` como prefixo e RLS futuro sem remodelar."""

    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="analises",
        # Coberto pelo prefixo dos tres indices compostos que comecam em empresa_id.
        db_index=False,
    )
    pessoa = models.ForeignKey("pessoas.Pessoa", on_delete=models.PROTECT, related_name="analises")
    consorciorista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="analises_encaminhadas"
    )
    analista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="analises_realizadas",
        null=True,
        blank=True,
    )
    status = models.ForeignKey(StatusAnalise, on_delete=models.PROTECT, related_name="analises")
    valor_solicitado = models.DecimalField("valor solicitado", max_digits=12, decimal_places=2)
    observacoes = models.TextField("observações", blank=True)
    versao = models.PositiveIntegerField("versão", default=0)

    class Meta:
        verbose_name = "análise"
        verbose_name_plural = "análises"
        ordering = ["-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_solicitado__gt=0), name="ck_analise_valor_positivo"
            ),
        ]
        indexes = [
            models.Index(fields=["empresa", "-criado_em"], name="idx_analise_empresa_criado"),
            models.Index(fields=["empresa", "status"], name="idx_analise_empresa_status"),
            models.Index(fields=["empresa", "consorciorista"], name="idx_analise_empresa_consorc"),
        ]

    def __str__(self) -> str:
        # Sem tocar em self.pessoa: __str__ é chamado em listagem e viraria N+1.
        return f"Análise #{self.pk}"
