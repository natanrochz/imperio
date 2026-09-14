from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager que usa e-mail como identificador, sem campo username."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra: Any) -> User:
        if not email:
            raise ValueError("E-mail é obrigatório.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Superusuário precisa de is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa de is_superuser=True.")
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField("e-mail", unique=True)
    nome_completo = models.CharField("nome completo", max_length=150)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    objects = UserManager()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # unique=True no Postgres diferencia maiusculas, entao normalizar so no
        # manager deixaria passar duplicata criada por ModelForm (admin) ou save()
        # direto. Normalizar aqui cobre todos os caminhos do ORM.
        self.email = UserManager.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        return self.nome_completo

    def get_short_name(self) -> str:
        return self.nome_completo.split()[0] if self.nome_completo else ""

    def __str__(self) -> str:
        return self.email


class Papel(models.TextChoices):
    ADMIN_EMPRESA = "admin_empresa", "Administrador da empresa"
    ANALISTA = "analista", "Analista"
    CONSORCIORISTA = "consorciorista", "Consorciorista"


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    empresa = models.ForeignKey("empresas.Empresa", on_delete=models.PROTECT, related_name="memberships")
    papel = models.CharField(max_length=20, choices=Papel.choices)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "vínculo"
        verbose_name_plural = "vínculos"
        constraints = [
            models.UniqueConstraint(fields=["user", "empresa"], name="uniq_membership_user_empresa"),
        ]
        indexes = [
            models.Index(fields=["user", "ativo"], name="idx_membership_user_ativo"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.empresa.nome} ({self.papel})"
