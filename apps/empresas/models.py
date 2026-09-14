from django.db import models

from apps.core.models import UUIDModel


class Empresa(UUIDModel):
    nome = models.CharField(max_length=150)
    cnpj = models.CharField(max_length=14, unique=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nome"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cnpj__regex=r"^\d{14}$"),
                name="ck_empresa_cnpj_digitos",
            ),
        ]

    def __str__(self) -> str:
        return self.nome
