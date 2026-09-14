from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User

SENHA = "senha-de-teste-bem-longa"


class UserNomeTests(TestCase):
    """AbstractUser.get_full_name/get_short_name leem first_name e last_name, que
    este User remove. Sem override, devolviam 'None None' e None."""

    def test_get_full_name_devolve_nome_completo(self):
        user = User.objects.create_user(
            email="maria@exemplo.com", password=SENHA, nome_completo="Maria Silva Souza"
        )
        self.assertEqual(user.get_full_name(), "Maria Silva Souza")

    def test_get_short_name_devolve_primeiro_nome(self):
        user = User.objects.create_user(
            email="maria@exemplo.com", password=SENHA, nome_completo="Maria Silva Souza"
        )
        self.assertEqual(user.get_short_name(), "Maria")

    def test_get_short_name_com_nome_vazio(self):
        self.assertEqual(User(email="x@exemplo.com", nome_completo="").get_short_name(), "")


class UserEmailTests(TestCase):
    """unique=True no Postgres diferencia maiusculas: sem normalizar no save(),
    o admin criava contas duplicadas variando a caixa."""

    def test_save_direto_normaliza_email(self):
        user = User(email="Dup@Exemplo.COM", nome_completo="Fulano")
        user.set_password(SENHA)
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.email, "dup@exemplo.com")

    def test_manager_normaliza_email(self):
        user = User.objects.create_user(email="Outro@Exemplo.COM", password=SENHA, nome_completo="Beltrano")
        self.assertEqual(user.email, "outro@exemplo.com")

    def test_caixa_diferente_nao_cria_segunda_conta(self):
        User.objects.create_user(email="dup@exemplo.com", password=SENHA, nome_completo="Fulano")
        duplicado = User(email="DUP@EXEMPLO.COM", nome_completo="Beltrano")
        duplicado.set_password(SENHA)
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicado.save()
        self.assertEqual(User.objects.count(), 1)


class UserManagerTests(TestCase):
    def test_create_superuser_define_flags(self):
        user = User.objects.create_superuser(email="root@exemplo.com", password=SENHA, nome_completo="Root")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_email_obrigatorio(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password=SENHA, nome_completo="Sem E-mail")

    def test_create_superuser_recusa_is_staff_falso(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root@exemplo.com", password=SENHA, nome_completo="Root", is_staff=False
            )
