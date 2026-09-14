from django.contrib import admin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "ativa"]
    list_filter = ["ativa"]
    search_fields = ["nome", "cnpj"]
