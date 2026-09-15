from __future__ import annotations

from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class Pessoa(UUIDModel, TimestampedModel):
    """Pessoa interessada em crédito, cadastrada dentro de uma empresa.

    Quem encaminhou não é atributo da pessoa: fica em cada `Analise`, para que a
    mesma pessoa possa ser reencaminhada depois por outro consorciorista sem que
    o primeiro perca o histórico.
    """

    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="pessoas",
        # Coberto pelo prefixo de idx_pessoa_empresa_nome e uniq_pessoa_empresa_cpf.
        db_index=False,
    )
    nome_completo = models.CharField("nome completo", max_length=150)
    cpf = models.CharField("CPF", max_length=11)
    data_nascimento = models.DateField("data de nascimento")
    renda_mensal = models.DecimalField("renda mensal", max_digits=12, decimal_places=2)
    telefone = models.CharField("telefone", max_length=11, blank=True)
    email = models.EmailField("e-mail", blank=True)

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ["nome_completo"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "cpf"], name="uniq_pessoa_empresa_cpf"),
            models.CheckConstraint(condition=models.Q(cpf__regex=r"^\d{11}$"), name="ck_pessoa_cpf_digitos"),
            models.CheckConstraint(
                condition=models.Q(renda_mensal__gte=0), name="ck_pessoa_renda_nao_negativa"
            ),
        ]
        indexes = [
            models.Index(fields=["empresa", "nome_completo"], name="idx_pessoa_empresa_nome"),
        ]

    def __str__(self) -> str:
        return self.nome_completo
