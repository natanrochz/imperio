# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Sistema de **análise de crédito multiempresa** em Django 6.1 / Python 3.14 / PostgreSQL 18, gerenciado com `uv`.

O nome `imperio` é usado de ponta a ponta: repositório, diretório, `name` do `pyproject.toml`, `name:` do `compose.yaml` (que dá os containers `imperio-web-1` / `imperio-db-1`) e `POSTGRES_DB`/`POSTGRES_USER`. Trocar o `name:` do `compose.yaml` renomeia o volume do Postgres junto (`<name>_pgdata`), o que na prática zera o banco local — depois é só `migrate`.

## Domínio

Plataforma multiempresa de análise de crédito habitacional. **Consorcioristas** (parceiros externos) captam pessoas interessadas e as encaminham para uma empresa; **analistas** da empresa cadastram, analisam e registram o resultado; o consorciorista acompanha apenas os resultados e gráficos das pessoas que ele mesmo encaminhou — nunca os dados internos da análise nem as indicações de outro consorciorista.

Os quatro perfis, e o que cada um alcança:

| Perfil | Alcance |
|---|---|
| Admin de plataforma | Gerencia as empresas pelo `/admin/`. Fica **fora** de `Membership` — é `is_superuser`, não um papel. |
| Admin de empresa | Gerencia analistas e consorcioristas da própria empresa. |
| Analista | Cadastra pessoas, vê todos os dados da própria empresa, analisa e registra o resultado. |
| Consorciorista | Encaminha pessoas; vê só resultado e gráficos das próprias indicações. |

Escala alvo: 100 consorcioristas, 10 analistas, 3.000 análises/mês. Trata nome, CPF, renda e informações de crédito — **sujeito à LGPD**.

Vocabulário de domínio em português (`Empresa`, `Pessoa`, `Analise`, `Consorciorista`); termos técnicos e de framework em inglês.

## Executando comandos

Tudo roda em containers. `POSTGRES_HOST` é `db`, que **só resolve dentro da rede do Compose** — `manage.py` executado direto no host não alcança o banco (comandos que não tocam no banco, como `check`, `makemigrations` e `collectstatic`, funcionam mesmo assim, com um warning de conexão).

```bash
docker compose up -d          # sobe db + web (runserver em 127.0.0.1:8000)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web pytest
docker compose exec web pytest apps/accounts/tests/test_models.py::NomeDaClasse::test_nome   # teste único
```

O banco também fica exposto no host em `127.0.0.1:5433` para acesso com cliente externo.

Lint (o `.venv/` local basta, não precisa de container):

```bash
.venv/bin/ruff check .
```

`ruff` está configurado com `E,F,I,UP,B,S,DTZ,DJ,C4,RUF` e `line-length = 110`, e o output está limpo — qualquer finding é regressão. `RUF012` está desligado globalmente porque exige `ClassVar` em atributos que o Django usa como lista mutável de classe (`Meta.ordering`, `constraints`, `ModelAdmin.list_display`…).

Os `models.py`/`admin.py`/`views.py` dos apps sem conteúdo são arquivos vazios de propósito, não stubs do `startapp` com import morto.

## Arquitetura

### Settings em camadas

`config/settings/base.py` é a base comum e lê o `.env` da raiz via `django-environ`. Sobre ela:

- `dev.py` — padrão do `manage.py`; adiciona `debug_toolbar`, e-mail no console.
- `prod.py` — HSTS, SSL redirect, cookies seguros, `CompressedManifestStaticFilesStorage`.
- `test.py` — usado pelo `pytest`, troca Argon2 por MD5 para acelerar.

O `pytest` seleciona as settings por `--ds=config.settings.test` no `addopts`, **não** pela chave `DJANGO_SETTINGS_MODULE` do `pyproject.toml`: o `compose.yaml` injeta `DJANGO_SETTINGS_MODULE` no ambiente via `env_file`, e a variável de ambiente tem precedência sobre o ini do pytest. Sem o `--ds` os testes rodam com as settings de `dev`. O `pytest` imprime `settings: … (from option)` no cabeçalho quando está correto.

`base.py` separa `DJANGO_APPS` de `LOCAL_APPS`; apps novos entram em `LOCAL_APPS`.

O e-mail é configurado por `MAILERS` (Django 6.0+), não por `EMAIL_BACKEND` — o setting antigo emite `RemovedInDjango70Warning` e some no Django 7.0.

O banco usa o pool nativo do `psycopg` (`OPTIONS.pool`) com `CONN_MAX_AGE = 0` — as duas coisas juntas são intencionais: quem mantém as conexões vivas é o pool, não o Django.

### Apps

Todos ficam sob `apps/`, mas usam **label curto**: cada `AppConfig` declara `name = "apps.<x>"` e `label = "<x>"`. Referências entre models usam o label (`"empresas.Empresa"`), não o caminho do pacote.

| App | Estado |
|---|---|
| `accounts` | `User` + `Membership` implementados |
| `empresas` | `Empresa` implementada |
| `core` | só `UUIDModel`, o abstract com o `uuid` público |
| `pessoas`, `analises` | stubs vazios do `startapp` |

`apps/core/models.py::UUIDModel` é abstract e dá o campo `uuid` (`default=uuid4`, `unique=True`, `editable=False`) a quem herda — hoje `Empresa` e `User`. `unique=True` já cria o índice; somar `db_index=True` geraria índice duplicado.

### Modelo de acesso

`AUTH_USER_MODEL = "accounts.User"` — `User` herda `AbstractUser` mas **remove `username`, `first_name` e `last_name`**; o identificador é `email` (`USERNAME_FIELD`), com `nome_completo` como campo obrigatório extra.

Duas consequências de remover esses campos, já tratadas e cobertas por teste em `apps/accounts/tests/test_models.py`:

- `get_full_name()` e `get_short_name()` são sobrescritos para usar `nome_completo`. As implementações de `AbstractUser` leem `first_name`/`last_name`, que aqui valem `None` — devolviam `'None None'` e `None` em vez de estourar.
- O e-mail é normalizado para minúsculas no `save()` do model, não só no `UserManager`. `unique=True` vira índice case-sensitive no Postgres, então normalizar apenas no manager deixaria o admin (que salva via `ModelForm`) criar contas duplicadas variando a caixa.

O vínculo usuário↔empresa é `Membership`, que carrega o papel (`Papel`: `admin_empresa`, `analista`, `consorciorista`) e é único por par `(user, empresa)`. **Esse é o eixo de multiempresa do sistema**: um usuário pode pertencer a várias empresas com papéis diferentes, e qualquer regra de permissão deve partir daí, não de `Group`/`Permission` do Django. A FK para `Empresa` é `PROTECT`.

`Empresa.cnpj` é `CharField(max_length=14)` com `CheckConstraint` de 14 dígitos — armazena **só dígitos**, sem máscara.

### Docker

`Dockerfile` multi-stage sobre uma base comum que instala o `uv` e cria o usuário `app`:

- `dev` — `uv sync --frozen` (com dev deps), `runserver`, código vem do bind mount `.:/app`.
- `prod` — `uv sync --frozen --no-dev`, `COPY . .`, roda `collectstatic` no build e sobe `gunicorn`.

O `collectstatic` do stage `prod` passa variáveis de ambiente dummy (`DJANGO_SECRET_KEY=build-only` etc.) só para as settings carregarem: `.env` está no `.dockerignore` e não existe na imagem, e `collectstatic` não toca no banco. Se `base.py` passar a exigir uma variável nova, esse `RUN` precisa ganhar o valor dummy correspondente ou o build quebra.

## Decisões de arquitetura fechadas

Decididas no início do projeto e **não reabertas**. As que já têm código estão descritas acima em "Arquitetura"; as demais valem para o que ainda vai ser escrito.

1. **Multi-tenant em schema compartilhado**, com FK `empresa` em toda tabela raiz de domínio. Nada de `django-tenants`.
2. **O papel é atributo do vínculo, não do usuário** — daí `Membership(user, empresa, papel, ativo)` em vez de FK direta em `User`: um consorciorista pode atuar em mais de uma empresa. A empresa ativa fica na sessão.
3. **PK interna `BigAutoField` + campo `uuid` separado**, único e indexado, para expor em URL. Nunca UUID como PK. Só em models que viram rota (`Empresa`, `User` têm; `Membership` não).
4. **`StatusAnalise` é configurável por empresa, mas com `categoria` fixa em código** (`em_analise`, `pendente`, `aprovado`, `reprovado`, `cancelado`). Toda agregação e regra de negócio usa `categoria`, **nunca `nome`** — o nome é rótulo editável pela empresa.
5. **CPF único por empresa**: `UniqueConstraint(empresa, cpf)`, nunca único global. Duplicata é tratada capturando `IntegrityError` dentro de `transaction.atomic()`, **nunca com check-then-insert** (que é race condition).
6. **`Pessoa` 1:N `Analise`** — a mesma pessoa pode ser reanalisada depois.
7. **`empresa` denormalizada em `Analise`**, além de estar em `Pessoa`, para permitir índice composto com `empresa_id` como prefixo e RLS futuro sem remodelar.
8. **Sem criptografia em nível de campo no CPF** — quebraria a unique constraint e a busca. A proteção vem de mascaramento na exibição, filtro de logging e trilha de auditoria.
9. **Bloqueio otimista por campo `versao` + update condicionado**, não `select_for_update`: o caso real é lost update entre dois POSTs sequenciais, não escrita concorrente.
10. **Regra de negócio mora em services/selectors**, fora de view, template e form. E **nada de signal para lógica de negócio** — criar os status padrão de uma empresa nova é um service chamado explicitamente, não um `post_save`.

## Isolamento entre empresas

Requisito de negócio, não detalhe de implementação.

- O filtro por empresa e por dono fica **centralizado em selectors que recebem um `Escopo(usuario_id, empresa_id, papel)`** explícito. Nunca repetido em view.
- **Proibido manager implícito** com `contextvars`/thread-local injetando `empresa_id`: quebra em Celery, management command e teste, e torna o filtro de segurança invisível em code review. O escopo é parâmetro, não ambiente.
- Acesso a registro de outra empresa ou de outro consorciorista retorna **404, nunca 403** — 403 confirma que o registro existe.
- O middleware **revalida `Membership` ativo a cada request**, não só na troca de empresa.

## Metas de performance

- Views/API: p95 < 200 ms. Painéis: p95 < 300 ms.
- Queries por request constantes, alvo ≤ 10. **Nunca N+1.**
- Dado de gráfico vem de `annotate`/`aggregate`/`TruncMonth` no banco, nunca de loop em Python.
- Paginação obrigatória em listagem.

## Convenções

- **Nenhuma dependência nova sem perguntar antes.**
- Django fixado em `>=6.1,<6.2` — não sugerir downgrade para 5.2 LTS. PostgreSQL apenas; nada que assuma SQLite.
- Commits pequenos, um assunto por commit, mensagem em português no formato Conventional Commits (`feat:`, `chore:`, `fix:`, `test:`).
- Type hints em tudo. Exceção específica, nunca `except` genérico silencioso.
- Teste junto do código, em `apps/<app>/tests/`.
- `ruff format` + `ruff check --fix` limpos antes de cada commit.
- Se alguma proposta introduzir N+1, race condition, falta de índice, vazamento entre empresas ou entre consorcioristas, ou decisão difícil de reverter, **apontar isso antes de escrever o código**.
