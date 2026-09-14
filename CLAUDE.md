# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Sistema de **análise de crédito multiempresa** em Django 6.1 / Python 3.14 / PostgreSQL 18, gerenciado com `uv`.

O nome `imperio` é usado de ponta a ponta: repositório, diretório, `name` do `pyproject.toml`, `name:` do `compose.yaml` (que dá os containers `imperio-web-1` / `imperio-db-1`) e `POSTGRES_DB`/`POSTGRES_USER`. Trocar o `name:` do `compose.yaml` renomeia o volume do Postgres junto (`<name>_pgdata`), o que na prática zera o banco local — depois é só `migrate`.

## Executando comandos

Tudo roda em containers. `POSTGRES_HOST` é `db`, que **só resolve dentro da rede do Compose** — `manage.py` executado direto no host não alcança o banco (comandos que não tocam no banco, como `check`, `makemigrations` e `collectstatic`, funcionam mesmo assim, com um warning de conexão).

```bash
docker compose up -d          # sobe db + web (runserver em 127.0.0.1:8000)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web pytest
docker compose exec web pytest apps/accounts/tests.py::NomeDaClasse::test_nome   # teste único
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
| `core`, `pessoas`, `analises` | stubs vazios do `startapp` |

### Modelo de acesso

`AUTH_USER_MODEL = "accounts.User"` — `User` herda `AbstractUser` mas **remove `username`, `first_name` e `last_name`**; o identificador é `email` (`USERNAME_FIELD`), com `nome_completo` como campo obrigatório extra.

Duas consequências de remover esses campos, já tratadas e cobertas por teste em `apps/accounts/tests.py`:

- `get_full_name()` e `get_short_name()` são sobrescritos para usar `nome_completo`. As implementações de `AbstractUser` leem `first_name`/`last_name`, que aqui valem `None` — devolviam `'None None'` e `None` em vez de estourar.
- O e-mail é normalizado para minúsculas no `save()` do model, não só no `UserManager`. `unique=True` vira índice case-sensitive no Postgres, então normalizar apenas no manager deixaria o admin (que salva via `ModelForm`) criar contas duplicadas variando a caixa.

O vínculo usuário↔empresa é `Membership`, que carrega o papel (`Papel`: `admin_empresa`, `analista`, `consorciorista`) e é único por par `(user, empresa)`. **Esse é o eixo de multiempresa do sistema**: um usuário pode pertencer a várias empresas com papéis diferentes, e qualquer regra de permissão deve partir daí, não de `Group`/`Permission` do Django. A FK para `Empresa` é `PROTECT`.

`Empresa.cnpj` é `CharField(max_length=14)` com `CheckConstraint` de 14 dígitos — armazena **só dígitos**, sem máscara.

### Docker

`Dockerfile` multi-stage sobre uma base comum que instala o `uv` e cria o usuário `app`:

- `dev` — `uv sync --frozen` (com dev deps), `runserver`, código vem do bind mount `.:/app`.
- `prod` — `uv sync --frozen --no-dev`, `COPY . .`, roda `collectstatic` no build e sobe `gunicorn`.

O `collectstatic` do stage `prod` passa variáveis de ambiente dummy (`DJANGO_SECRET_KEY=build-only` etc.) só para as settings carregarem: `.env` está no `.dockerignore` e não existe na imagem, e `collectstatic` não toca no banco. Se `base.py` passar a exigir uma variável nova, esse `RUN` precisa ganhar o valor dummy correspondente ou o build quebra.
