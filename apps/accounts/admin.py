from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Membership, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "nome_completo", "is_active", "is_staff"]
    search_fields = ["email", "nome_completo"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("nome_completo",)}),
        (
            _("Permissões"),
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("Datas"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nome_completo", "password1", "password2")}),
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "empresa", "papel", "ativo"]
    list_filter = ["papel", "ativo", "empresa"]
    search_fields = ["user__email", "empresa__nome"]
    autocomplete_fields = ["user", "empresa"]
