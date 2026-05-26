# Estrutura do projeto

## Visão geral

Aplicação Flask organizada por **camadas funcionais** dentro de `app/` (models, routes, services, templates, static, utils). Scripts utilitários, migrações e testes ficam na raiz ou em pastas dedicadas.

```
sra-pli-5/
├── app/                       # Pacote principal da aplicação Flask
│   ├── __init__.py            # create_app (factory), inicialização de extensões
│   ├── config.py              # Classe Config (lê .env)
│   ├── models/                # Modelos SQLAlchemy
│   ├── routes/                # Blueprints Flask (endpoints HTTP)
│   ├── services/              # Lógica de negócio (camada de serviço)
│   ├── templates/             # Jinja2 templates
│   ├── static/                # CSS, JS, assets, editor-react/
│   └── utils/                 # Helpers (logger, htmx, etc.)
├── migrations/                # Alembic (Flask-Migrate)
│   ├── versions/              # Versões geradas
│   ├── env.py
│   └── *.sql                  # Migrações SQL ad-hoc
├── storage/                   # Arquivos persistidos (DOCX, uploads, exports)
│   ├── modelos_relatorio/
│   ├── relatorios_base/
│   ├── relatorios_producao/
│   ├── relatorios_finalizados/
│   ├── relatorios_previews/
│   ├── canonicos/
│   ├── exportacoes/
│   └── uploads/
├── tests/                     # Testes formais
├── instance/                  # Instance folder do Flask (DB SQLite, segredos)
├── .kiro/                     # Configuração Kiro (specs, steering, hooks)
├── docs/                      # Documentação adicional
├── docker-compose.yml         # Postgres local
├── requirements.txt           # Dependências Python
├── run.py                     # Entry point (cria app e roda)
└── .env / .env.example        # Variáveis de ambiente
```

## Convenções por camada

### `app/models/`

- Um arquivo por modelo, em `snake_case` (`relatorio_producao.py`).
- Classes em `PascalCase` (`RelatorioProducao`).
- Todos os modelos importados em `app/models/__init__.py` (registro central para o SQLAlchemy e Alembic).
- Mixins reutilizáveis em `mixins.py` (ex.: `AuditoriaMixin`).
- Tabelas de domínio (enums persistidos) unificadas em `dominio.py` na classe `Dominio` (tabela `public.dominios`). Cada registro é identificado por `(tipo, valor)` — ex.: `tipo='perfil_usuario'`, `tipo='status_relatorio'`, `tipo='status_capitulo'`, etc.

### `app/routes/`

- Cada arquivo expõe um Blueprint nomeado `<area>_bp` (ex.: `auth_bp`, `relatorio_bp`, `api_bp`).
- Blueprints registrados explicitamente em `create_app`.
- Rotas concentram parsing de request e delegam para serviços; pouca lógica direta.
- API JSON em `routes/api.py` com proteções CSRF, rate limit e validação de perfil.

### `app/services/`

- Arquivos com prefixo `servico_*.py` contendo classes `Servico*`.
- Métodos geralmente `@staticmethod`; estado em parâmetros, não em instâncias.
- Concentram regra de negócio, transações de banco, integrações externas (e-mail, DOCX).
- Serviços conhecidos:
  - `servico_usuario` — autenticação, convite, recuperação de senha.
  - `servico_relatorio`, `servico_acoes_relatorio`, `servico_finalizar_relatorio` — ciclo do relatório.
  - `servico_envio_autor`, `servico_sincronizar_capitulos` — fluxo de capítulos.
  - `servico_extracao_canonica`, `servico_perfil_formatacao`, `servico_sanitizar_docx` — manipulação canônica do DOCX.
  - `servico_merge_docx`, `servico_capa`, `servico_toc`, `servico_cross_refs`, `servico_captioning` — montagem do documento final.
  - `servico_email` — Brevo.

### `app/templates/`

- Layouts base em `layouts/`, fragmentos reutilizáveis em `components/`.
- Páginas por área: `admin/`, `configuracoes/`, `relatorio/`, `dev/`.
- Cache-busting via `{{ static_v('caminho') }}`.

### `app/static/`

- `css/`, `js/` para assets vanilla.
- `editor-react/` é um sub-projeto isolado (componente React `docx-editor`).

### `migrations/`

- Gerenciado pelo Flask-Migrate (Alembic).
- Versões em `migrations/versions/`.
- Migrações SQL manuais (numeradas) coexistem na raiz da pasta para mudanças fora do ORM.

### `storage/`

- Layout fixo por tipo de artefato. Não criar pastas ad-hoc fora desse padrão.
- Caminho configurável via `STORAGE_PATH`.

## Onde adicionar novo código

| Tipo de mudança                        | Local                                       |
|---------------------------------------|---------------------------------------------|
| Nova entidade persistida              | `app/models/<nome>.py` + registrar no `__init__.py` + migration |
| Novo endpoint HTTP/HTML               | Blueprint existente em `app/routes/` ou novo blueprint registrado em `create_app` |
| Novo endpoint JSON/API                | `app/routes/api.py` (seguir padrões CSRF, rate limit, perfil) |
| Nova regra de negócio                 | `app/services/servico_<area>.py`            |
| Helper transversal                    | `app/utils/`                                |
| Tela nova                             | `app/templates/<area>/` + assets em `static/` |
| Manipulação de DOCX                   | Serviço dedicado em `app/services/`         |
| Script de manutenção/seed             | Raiz do projeto (`seed_*.py`, `migrar_*.py`) |
| Teste                                 | `tests/test_*.py` (ou `test_*.py` na raiz para checks rápidos) |

## Arquivos de referência

- `documento_conceitual_sra_v5.md` — especificação conceitual consolidada do produto.
- `PLANO_IMPLEMENTACAO.md` — plano de implementação e gaps.
- `prompt_agente_ia_pendencias_sra.txt` — instruções históricas para agentes IA.

## Itens a evitar

- Não commitar `.env`, `credenciais.txt`, `credenciais_render.txt`.
- Não usar `datetime.utcnow()`; sempre `datetime.now(timezone.utc)`.
- Não escrever lógica de negócio diretamente em rotas — delegar a `services/`.
- Não acessar arquivos fora de `STORAGE_PATH` para artefatos de relatório.
- Não introduzir nomes em inglês em domínios/modelos/serviços; manter PT-BR.
