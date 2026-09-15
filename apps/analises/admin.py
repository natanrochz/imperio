from django.contrib import admin

from .models import Analise, StatusAnalise


@admin.register(StatusAnalise)
class StatusAnaliseAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "empresa", "ordem", "ativo"]
    list_filter = ["empresa", "categoria", "ativo"]
    search_fields = ["nome"]
    list_select_related = ["empresa"]
    autocomplete_fields = ["empresa"]


@admin.register(Analise)
class AnaliseAdmin(admin.ModelAdmin):
    """Visão administrativa. **Não é o fluxo do analista**: salvar por aqui não passa
    pelo `registrar_resultado`, então não há bloqueio otimista nem incremento de
    `versao`. Por isso `versao` é somente leitura."""

    list_display = ["__str__", "pessoa", "empresa", "status", "consorciorista", "valor_solicitado"]
    list_filter = ["empresa", "status"]
    search_fields = ["pessoa__nome_completo", "pessoa__cpf"]
    list_select_related = ["pessoa", "empresa", "status", "consorciorista"]
    autocomplete_fields = ["pessoa", "consorciorista", "analista", "status"]
    readonly_fields = ["uuid", "versao", "criado_em", "atualizado_em"]
