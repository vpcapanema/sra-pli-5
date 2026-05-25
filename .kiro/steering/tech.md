# Tecnologia

## Stack principal

- **Linguagem**: Python 3 (não há `pyproject.toml`; dependências em `requirements.txt`).
- **Framework web**: Flask 3.0 com pattern de Application Factory (`app/__init__.py::create_app`).
- **ORM**: SQLAlchemy 2.0 + Flask-SQLAlchemy 3.1.
- **Migrations**: Flask-Migrate + Alembic (pasta `migrations/`).
- **Autenticação**: Flask-Login com `user_loader` em `Usuario`.
- **Formulários/CSRF**: Flask-WTF (CSRF customizado também em endpoints API mutantes).
- **Templates**: Jinja2 (`app/templates/`), com helper `static_v(path)` para cache-busting.
- **Frontend**: Jinja2 + JavaScript vanilla + componente React isolado em `app/static/editor-react/` (editor DOCX inline).
- **Preview DOCX (cliente)**: `docx-preview` via CDN.

## Banco de dados

- **Produção**: PostgreSQL 16 (via Docker Compose, porta `5433`, banco `sra_pli`).
- **Desenvolvimento**: PostgreSQL local ou SQLite como fallback (`sqlite:///sra.db`).
- **Driver**: `psycopg[binary]` 3.x.
- Configuração via variável `DATABASE_URL` em `.env`.

## Geração e manipulação de DOCX

- `python-docx` — leitura/escrita de documentos.
- `docxtpl` — templates DOCX com Jinja.
- `docxcompose` — merge de múltiplos DOCX.
- `mammoth` — DOCX → HTML.
- `lxml` — manipulação direta do OOXML quando necessário.
- `WeasyPrint` — exportação HTML → PDF.
- `openpyxl` — planilhas auxiliares.

## E-mail transacional

- **Brevo** (variáveis `BREVO_API_KEY`, `BREVO_FROM_EMAIL`, `BREVO_FROM_NAME`).

## Configuração

- Variáveis de ambiente carregadas via `python-dotenv` em `app/config.py`.
- Arquivo `.env` (ver `.env.example`); chaves principais: `SECRET_KEY`, `DATABASE_URL`, `STORAGE_PATH`, `APP_BASE_URL`.
- Armazenamento de arquivos no diretório `storage/` (configurável).

## Comandos comuns

> Ambiente Windows com shell `cmd`. Use `&` como separador de comandos.

### Setup inicial

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Banco (Postgres via Docker)

```cmd
docker-compose up -d
```

### Migrations

```cmd
flask db migrate -m "descricao"
flask db upgrade
flask db downgrade
```

> Use `set FLASK_APP=run.py` antes dos comandos `flask` se necessário.

### Executar a aplicação

```cmd
python run.py
```

### Seeds e utilitários

- `python seed_dominios.py` — popula tabelas de domínio.
- `python migrar_schema_sra.py` — migrações ad-hoc de schema.
- `python migrar_usuarios.py` — migração de usuários.

### Testes

Testes ad-hoc em `tests/` e na raiz (`test_*.py`, `check_*.py`). Não há runner configurado; executar arquivos diretamente:

```cmd
python tests\test_envio_autor.py
python test_merge_docx.py
```

## Convenções de código

- **Idioma**: nomes de classes, funções, variáveis, comentários e docstrings em **português do Brasil**.
- **Docstrings**: estilo curto em PT-BR, geralmente uma linha descrevendo o propósito.
- **Classes de serviço**: prefixo `Servico*` (ex.: `ServicoUsuario`, `ServicoRelatorio`); métodos geralmente `@staticmethod`.
- **Models**: classes em `PascalCase`, arquivos em `snake_case` (`relatorio_producao.py` → `RelatorioProducao`).
- **Models** centralizam imports em `app/models/__init__.py`.
- **Mixins**: ver `AuditoriaMixin` (`criado_por`, `criado_em`, `atualizado_por`, `atualizado_em`).
- **Datas**: sempre `datetime.now(timezone.utc)` (UTC), nunca `datetime.utcnow()` (deprecated).
- **Blueprints**: cada rota em arquivo próprio em `app/routes/`, registrados em `create_app`.
- **Segurança da API**: CSRF token, rate limiting (60 req/min/IP), validação de perfil, limite de upload 50 MB.
