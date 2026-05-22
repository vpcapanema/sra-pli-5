# Plano de Implementação — SRA PLI-SP

> Gerado em 21/05/2026. Base: `documento_conceitual_sra_v5.md`.

---

## Estado atual

### Implementado

| Camada | Artefato | Status |
|--------|----------|--------|
| Models | 20 modelos ORM + mixin de auditoria + Dominio | Completo |
| Auth | Login, cadastro, logout, seleção de perfil | Completo |
| Serviço | `servico_usuario.py` — CRUD + autenticação | Completo |
| Serviço | `servico_relatorio.py` — CRUD modelos, base, versões, capítulos | Completo |
| Rotas | `auth.py`, `principal.py`, `admin.py`, `relatorio.py` | Completo |
| Templates | Acesso (login, cadastro, recuperar senha) | Completo |
| Templates | Dashboard (painéis, relatórios) | Completo |
| Templates | Sidebar colapsável com ícones e minicard | Completo |
| Templates | Gestão de usuários (admin) | Completo |
| Templates | Modelos, relatórios base, versões de trabalho, árvore de capítulos | Completo |
| CSS | `app.css` (BEM) + `estilo.css` (overrides) | Completo |
| JS | Toggle de menus colapsáveis | Completo |
| Infra | `storage/` com subpastas | Completo |
| Infra | Flask-Migrate configurado | Completo |
| DB | SQLite (`sra.db`) | Em uso (será migrado) |

### Não implementado

| Item | Referência conceitual |
|------|----------------------|
| Migração para PostgreSQL | §5.6 |
| Tabela padrão completa (seleção, ações em lote, busca, paginação, ordenação) | §tabela_padrao.html |
| Atribuição de capítulos a autores | §atribuicao_autor.html |
| Upload DOCX pelo autor | §upload_docx.html |
| Extração de conteúdo do DOCX (pipeline) | §5.4 |
| Prévia do conteúdo (parcial e completa) | §previa_conteudo.html |
| Confirmação de importação/rejeição | §confirmacao_envio.html |
| Visualizador geral (leitura + edição inline) | §visualizador_geral.html |
| Revisão pelo coordenador | §revisao_conteudo.html |
| Bloqueio/desbloqueio de versão | §bloqueios |
| Exportação final em DOCX | §exportacao.html, §5.7 |
| Pipeline de extração canônica | §5.3 |
| Gestão da biblioteca de formatação canônica | §biblioteca_canonica.html |
| Configuração de numeração | §configuracao_numeracao.html |
| Notificações | §notificacoes.html |
| Barra de estado | §barra_estado.html |
| Modal de confirmação | §modal_confirmacao.html |
| Auditoria | §auditoria.html |
| Gestão de perfis | §gestao_perfis.html |
| Flask-WTF (formulários com validação) | §4.5 |
| Testes automatizados | §4.3.2 |
| CSS/JS por página (convenção do doc conceitual) | §4.3.1 |

---

## Fases de implementação

### Fase 0 — Migração para PostgreSQL

**Objetivo:** trocar o motor de banco de SQLite para PostgreSQL.

- [ ] 0.1 Instalar `psycopg2-binary` no `requirements.txt`
- [ ] 0.2 Criar banco PostgreSQL local (`sra_pli`)
- [ ] 0.3 Atualizar `config.py` para usar `DATABASE_URL` com PostgreSQL
- [ ] 0.4 Rodar `flask db upgrade` para criar o schema
- [ ] 0.5 Re-executar seed de domínios e usuários de teste
- [ ] 0.6 Validar todas as rotas existentes

---

### Fase 1 — Componentes compartilhados (base para tudo)

**Objetivo:** construir os blocos reutilizáveis que todas as telas dependem.

- [ ] 1.1 **Tabela padrão avançada** — refatorar `tabela.html`
  - Coluna de seleção (checkbox)
  - Barra de ações em lote
  - Busca/filtro por texto
  - Ordenação por coluna (JS)
  - Paginação server-side
  - Ações por linha (botões-ícone)
- [ ] 1.2 **Modal de confirmação** — `modal_confirmacao.html`
  - Título, mensagem, botão confirmar/cancelar
  - Acionado por JS antes de transições de estado
- [ ] 1.3 **Barra de estado** — `barra_estado.html`
  - Exibe estado atual do conteúdo/versão (ex: "Em edição", "Em revisão")
  - Badge colorido por estado
- [ ] 1.4 **Notificações** — `notificacoes.html`
  - Ícone de sino na sidebar ou topbar
  - Listagem de notificações com marcação de lida
  - Serviço `servico_notificacao.py`
- [ ] 1.5 **Flask-WTF** — criar forms para todos os formulários existentes
  - Validação server-side
  - Proteção CSRF

---

### Fase 2 — Gestão administrativa completa

**Objetivo:** completar o CRUD do administrador.

- [ ] 2.1 **Gestão de perfis** — `gestao_perfis.html`
  - CRUD de perfis (criar, editar, ativar/desativar)
  - Serviço `servico_perfil.py` (ou método em `servico_usuario.py`)
- [ ] 2.2 **Auditoria** — `auditoria.html`
  - Tabela de registros de auditoria (somente leitura)
  - Filtros por usuário, ação, entidade, data
  - Serviço `servico_auditoria.py`
  - Integrar registro automático nas operações de escrita
- [ ] 2.3 **Notificações administrativas**
  - Enviar notificação ao criar usuário, abrir ciclo, etc.

---

### Fase 3 — Biblioteca de formatação canônica

**Objetivo:** permitir que o coordenador cadastre e versione formatações.

- [ ] 3.1 **Biblioteca canônica** — `biblioteca_canonica.html`
  - CRUD de bibliotecas e versões
  - Upload do DOTX modelo
  - Serviço `servico_biblioteca_canonica.py`
- [ ] 3.2 **Pipeline de extração canônica**
  - Ler DOTX com `python-docx` + `lxml`
  - Extrair seções, estilos, elementos
  - Gerar JSON canônico consolidado
  - Salvar em `storage/canonicos/{id}/`
  - Serviço `servico_extracao_canonica.py`
- [ ] 3.3 **Configuração de numeração** — `configuracao_numeracao.html`
  - Exibir configurações auto-detectadas
  - Permitir override manual pelo coordenador
  - Serviço `servico_numeracao.py`

---

### Fase 4 — Ciclo do autor (upload → prévia → importação)

**Objetivo:** implementar o fluxo principal do autor.

- [ ] 4.1 **Atribuição de capítulos** — `atribuicao_autor.html`
  - Coordenador atribui capítulos a autores
  - Tabela com capítulos + select de autor
  - Adicionar FK `id_usuario_autor` em `capitulos_documento` (migração)
- [ ] 4.2 **Upload DOCX** — `upload_docx.html`
  - Form de upload vinculado ao capítulo atribuído
  - Salvar arquivo em `storage/uploads/{id}/`
  - Criar registro em `envios_conteudo`
  - Serviço `servico_envio.py`
- [ ] 4.3 **Extração de conteúdo do upload**
  - Ler DOCX com `python-docx`
  - Classificar elementos contra base canônica
  - Popular `elementos_conteudo` como rascunho
  - Serviço `servico_extracao_conteudo.py`
- [ ] 4.4 **Prévia parcial** — `previa_conteudo.html`
  - Renderizar HTML do conteúdo extraído
  - Aplicar CSS derivado da base canônica
  - Criar registro em `previsualizacoes_conteudo`
- [ ] 4.5 **Confirmação de envio** — `confirmacao_envio.html`
  - Botão importar / rejeitar
  - Se importar: persistir elementos na versão de trabalho
  - Se rejeitar: descartar envio e voltar ao upload
  - Transição de estado: `Em prévia → Importado` ou `Rejeitado`

---

### Fase 5 — Edição inline + envio ao coordenador

**Objetivo:** permitir ajustes no conteúdo importado.

- [ ] 5.1 **Visualizador geral** — `visualizador_geral.html`
  - Modo leitura e modo edição
  - Integrar editor rich-text (Quill, TipTap ou similar)
  - Renderizar conteúdo com formatação canônica
- [ ] 5.2 **Edição inline do autor**
  - Autor edita apenas seus capítulos atribuídos
  - Salvar alterações em `conteudo_processado`
  - Transição: `Importado → Em edição do autor`
- [ ] 5.3 **Confirmação e envio ao coordenador**
  - Modal de confirmação
  - Transição: `Em edição do autor → Confirmado → Em revisão`
  - Bloquear edição pelo autor (criar registro em `bloqueios`)
  - Notificar coordenador

---

### Fase 6 — Revisão do coordenador

**Objetivo:** coordenador revisa, edita e aprova/reprova.

- [ ] 6.1 **Revisão de conteúdo** — `revisao_conteudo.html`
  - Visualizador geral em modo edição
  - Criar registro em `revisoes`
  - Transição: `Em revisão → Em edição do coordenador`
- [ ] 6.2 **Ações de revisão**
  - Aprovar / reprovar com observação
  - Criar registros em `acoes_revisao`
  - Se aprovar: `Aprovado`
  - Se reprovar: `Reprovado` → desbloquear autor → notificar
  - Serviço `servico_revisao.py`
- [ ] 6.3 **Prévia completa**
  - Renderizar versão de trabalho inteira
  - Conteúdo novo + conteúdo existente

---

### Fase 7 — Exportação e finalização

**Objetivo:** gerar o DOCX final e fechar o ciclo.

- [ ] 7.1 **Exportação** — `exportacao.html`
  - Coordenador aciona após todos os capítulos aprovados
  - Montar DOCX via `python-docx` / `docxtpl`
  - Aplicar estilos canônicos + numeração
  - Salvar em `storage/exportacoes/{id}/`
  - Serviço `servico_exportacao.py`
- [ ] 7.2 **Finalização do ciclo**
  - Transição: `Aprovado → Finalizado`
  - Salvar como novo relatório-base
  - Notificar todos os envolvidos
- [ ] 7.3 **Download do DOCX**
  - Rota para download do arquivo exportado

---

### Fase 8 — Qualidade e polimento

- [ ] 8.1 Testes unitários para serviços
- [ ] 8.2 Testes de integração para rotas
- [ ] 8.3 CSS/JS por página (conforme convenção do doc conceitual)
- [ ] 8.4 Responsividade da sidebar e tabelas
- [ ] 8.5 Tratamento de erros e páginas 404/500
- [ ] 8.6 Logs estruturados

---

## Dependências entre fases

```
Fase 0 (PostgreSQL)
  └── Fase 1 (componentes compartilhados)
        ├── Fase 2 (admin completo)
        └── Fase 3 (biblioteca canônica)
              └── Fase 4 (upload + prévia)
                    └── Fase 5 (edição inline)
                          └── Fase 6 (revisão)
                                └── Fase 7 (exportação)
                                      └── Fase 8 (qualidade)
```

## Serviços a criar

| Serviço | Fase | Responsabilidade |
|---------|------|-----------------|
| `servico_notificacao.py` | 1 | CRUD notificações, marcar como lida |
| `servico_perfil.py` | 2 | CRUD perfis |
| `servico_auditoria.py` | 2 | Registro e consulta de auditoria |
| `servico_biblioteca_canonica.py` | 3 | CRUD bibliotecas e versões canônicas |
| `servico_extracao_canonica.py` | 3 | Pipeline de extração do DOTX |
| `servico_numeracao.py` | 3 | Configuração e override de numeração |
| `servico_envio.py` | 4 | Upload, armazenamento, registro |
| `servico_extracao_conteudo.py` | 4 | Extração de conteúdo do DOCX |
| `servico_revisao.py` | 6 | Revisão, ações, transições de estado |
| `servico_exportacao.py` | 7 | Montagem e exportação do DOCX final |

## Matriz de estados (referência rápida)

```
Clonado → Em prévia → Importado → Em edição (autor)
                   ↘ Rejeitado    → Confirmado (autor)
                                    → Em revisão
                                      → Em edição (coordenador)
                                        → Aprovado → Finalizado
                                        → Reprovado ↩ Em edição (autor)
```
