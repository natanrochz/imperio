from django.contrib import admin

from apps.core.formatacao import mascarar_cpf

from .models import Pessoa


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ["nome_completo", "cpf_mascarado", "empresa", "renda_mensal", "criado_em"]
    list_filter = ["empresa"]
    search_fields = ["nome_completo", "cpf"]
    list_select_related = ["empresa"]
    autocomplete_fields = ["empresa"]
    readonly_fields = ["uuid", "criado_em", "atualizado_em"]

    @admin.display(description="CPF", ordering="cpf")
    def cpf_mascarado(self, obj: Pessoa) -> str:
        return mascarar_cpf(obj.cpf)
