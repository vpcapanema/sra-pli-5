# Design Document - Integração do Conceito de Capítulos com Seções DOCX

## Visão Geral do Design

Este documento descreve a arquitetura e design para integrar o novo conceito de capítulos (distinção seção DOCX vs capítulo conceitual) com os serviços existentes do SRA-PLI. O design foca em compatibilidade retroativa, modularidade e manutenibilidade.

## Arquitetura do Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Apresentação                    │
│  (Templates Jinja2, JavaScript, Componente React Editor)    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Camada de API/Rotas                       │
│  (Blueprints Flask: auth, relatorio, api, capitulos, etc.)  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Serviços                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Serviços Existentes                                │    │
│  │ • Extração Canônica                                │    │
│  │ • Sincronização Capítulos                          │    │
│  │ • TOC                                              │    │
│  │ • Cross-References                                 │    │
│  │ • Captioning                                       │    │
│  │ • Merge DOCX                                       │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Novos Serviços                                     │    │
│  │ • Classificação Capítulos                          │    │
│  │ • Extração Seções                                  │    │
│  │ • Numeração Unificada                              │    │
│  │ • Rastreamento Páginas                             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Modelos                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Modelos Existentes                                 │    │
│  │ • CapituloDocumento                                │    │
│  │ • RelatorioProducao                                │    │
│  │ • ElementoConteudo                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Novos Modelos                                      │    │
│  │ • SecaoDOCX                                        │    │
│  │ • QuebraPagina                                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Persistência                    │
│  (PostgreSQL/SQLite via SQLAlchemy + Flask-SQLAlchemy)      │
└─────────────────────────────────────────────────────────────┘
```

## Design Detalhado

### 1. Modelos de Dados

#### 1.1 Modelo `SecaoDOCX` (Novo)

```python
class SecaoDOCX(db.Model):
    """Representa uma seção técnica DOCX (w:sectPr)."""
    
    __tablename__ = 'secoes_docx'
    
    id_secao = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(db.Integer, db.ForeignKey('relatorios_producao.id_relatorio'), nullable=False)
    
    # Identificação
    ordem_secao = db.Column(db.Integer, nullable=False)  # Ordem no documento (0-based)
    tipo_quebra = db.Column(db.String(50))  # nextPage, continuous, evenPage, oddPage
    
    # Propriedades de página
    largura_pagina_mm = db.Column(db.Float)
    altura_pagina_mm = db.Column(db.Float)
    orientacao = db.Column(db.String(20))  # retrato, paisagem
    
    # Margens (mm)
    margem_top_mm = db.Column(db.Float)
    margem_right_mm = db.Column(db.Float)
    margem_bottom_mm = db.Column(db.Float)
    margem_left_mm = db.Column(db.Float)
    margem_header_mm = db.Column(db.Float)
    margem_footer_mm = db.Column(db.Float)
    margem_gutter_mm = db.Column(db.Float)
    
    # Numeração de páginas
    formato_numero_pagina = db.Column(db.String(50))  # decimal, lowerRoman, upperRoman, etc.
    inicio_numero_pagina = db.Column(db.Integer)
    
    # Colunas
    colunas = db.Column(db.Integer, default=1)
    espaco_colunas_mm = db.Column(db.Float)
    
    # Intervalo no documento
    inicio_paragrafo = db.Column(db.Integer, nullable=False)
    fim_paragrafo = db.Column(db.Integer, nullable=False)
    
    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relacionamentos
    relatorio = db.relationship('RelatorioProducao', backref=db.backref('secoes', lazy=True))
    quebras_pagina = db.relationship('QuebraPagina', backref='secao', lazy=True, cascade='all, delete-orphan')
    capitulos = db.relationship('CapituloDocumento', secondary='capitulo_secao', backref='secoes')
```

#### 1.2 Modelo `QuebraPagina` (Novo)

```python
class QuebraPagina(db.Model):
    """Representa uma quebra de página dentro de uma seção."""
    
    __tablename__ = 'quebras_pagina'
    
    id_quebra = db.Column(db.Integer, primary_key=True)
    id_secao = db.Column(db.Integer, db.ForeignKey('secoes_docx.id_secao'), nullable=False)
    
    # Posição
    indice_paragrafo = db.Column(db.Integer, nullable=False)  # Índice do parágrafo onde ocorre a quebra
    tipo_quebra = db.Column(db.String(50))  # page, column, textWrapping
    
    # Contexto
    numero_pagina = db.Column(db.Integer)  # Número da página após a quebra
    contexto_anterior = db.Column(db.Text)  # Texto do parágrafo anterior (para debug)
    
    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.now(timezone.utc))
```

#### 1.3 Atualização do Modelo `CapituloDocumento`

```python
class CapituloDocumento(db.Model):
    # Campos existentes preservados...
    
    # Novos campos para o conceito endurecido
    classificacao = db.Column(db.String(50))  # 'capitulo', 'subcapitulo', 'anexo', 'apendice'
    prefixo_indice = db.Column(db.String(20))  # 'ANEXO_', 'APENDICE_', ''
    estilo_docx = db.Column(db.String(100))  # Nome do estilo DOCX (ex: 'Heading 1', 'Título Anexo')
    
    # Campos para rastreamento de seções
    id_secao_inicio = db.Column(db.Integer, db.ForeignKey('secoes_docx.id_secao'))
    id_secao_fim = db.Column(db.Integer, db.ForeignKey('secoes_docx.id_secao'))
    
    # Campos para numeração unificada
    numero_unificado = db.Column(db.String(50))  # '1', '1.1', 'ANEXO_A', etc.
    ordem_global = db.Column(db.Integer)  # Ordem global entre todos os elementos indexáveis
    
    # Relacionamentos atualizados
    secao_inicio = db.relationship('SecaoDOCX', foreign_keys=[id_secao_inicio])
    secao_fim = db.relationship('SecaoDOCX', foreign_keys=[id_secao_fim])
```

#### 1.4 Tabela de Associação `capitulo_secao`

```python
capitulo_secao = db.Table('capitulo_secao',
    db.Column('id_capitulo', db.Integer, db.ForeignKey('capitulos_documento.id_capitulo_documento'), primary_key=True),
    db.Column('id_secao', db.Integer, db.ForeignKey('secoes_docx.id_secao'), primary_key=True),
    db.Column('tipo_associacao', db.String(20))  # 'inicio', 'fim', 'contem'
)
```

### 2. Serviços Novos

#### 2.1 `ServicoClassificacaoCapitulos`

**Responsabilidade**: Classificar capítulos por estilo DOCX e conteúdo.

```python
class ServicoClassificacaoCapitulos:
    
    @staticmethod
    def classificar_por_estilo(estilo_docx: str, titulo: str, nivel: int) -> dict:
        """
        Classifica um capítulo baseado no estilo DOCX e título.
        
        Retorna: {
            'classificacao': 'capitulo'|'subcapitulo'|'anexo'|'apendice',
            'prefixo_indice': 'ANEXO_'|'APENDICE_'|'',
            'estilo_docx': estilo_original
        }
        """
    
    @staticmethod
    def mapear_estilos_documento(doc: Document) -> dict:
        """
        Mapeia estilos DOCX para classificações.
        
        Retorna: {
            'Heading 1': {'classificacao': 'capitulo', 'prefixo': ''},
            'Heading 2': {'classificacao': 'subcapitulo', 'prefixo': ''},
            'Título Anexo': {'classificacao': 'anexo', 'prefixo': 'ANEXO_'},
            # etc.
        }
        """
```

#### 2.2 `ServicoExtracaoSecoes`

**Responsabilidade**: Extrair seções DOCX e quebras de página.

```python
class ServicoExtracaoSecoes:
    
    @classmethod
    def extrair_secoes(cls, doc: Document) -> List[Dict]:
        """
        Extrai todas as seções (w:sectPr) do documento.
        
        Retorna lista de dicionários com propriedades das seções.
        """
    
    @classmethod
    def extrair_quebras_pagina(cls, doc: Document) -> List[Dict]:
        """
        Extrai quebras de página (w:br type="page") do documento.
        
        Retorna lista de dicionários com posição das quebras.
        """
    
    @classmethod
    def mapear_capitulos_secoes(cls, capitulos: List[Dict], secoes: List[Dict]) -> Dict:
        """
        Mapeia capítulos para seções DOCX.
        
        Retorna dicionário com mapeamento capítulo → seção.
        """
```

#### 2.3 `ServicoNumeracaoUnificada`

**Responsabilidade**: Gerenciar numeração unificada de todos os elementos indexáveis.

```python
class ServicoNumeracaoUnificada:
    
    def __init__(self, id_relatorio: int):
        self.id_relatorio = id_relatorio
    
    def calcular_numeracao(self) -> Dict:
        """
        Calcula a numeração unificada para todos os elementos do relatório.
        
        Retorna: {
            'capitulos': [
                {'id': 1, 'numero': '1', 'ordem_global': 1},
                {'id': 2, 'numero': '1.1', 'ordem_global': 2},
                # etc.
            ],
            'tabelas': [...],
            'figuras': [...],
            'equacoes': [...]
        }
        """
    
    def atualizar_numeracao(self, elemento_tipo: str, elemento_id: int, acao: str) -> bool:
        """
        Atualiza a numeração após adição/remoção de elemento.
        
        acao: 'adicionar' | 'remover' | 'mover'
        """
    
    def obter_numero(self, elemento_tipo: str, elemento_id: int) -> str:
        """
        Obtém o número unificado de um elemento.
        """
```

#### 2.4 `ServicoRastreamentoPaginas`

**Responsabilidade**: Rastrear números de página de elementos.

```python
class ServicoRastreamentoPaginas:
    
    def __init__(self, id_relatorio: int):
        self.id_relatorio = id_relatorio
    
    def calcular_paginas(self, doc: Document) -> Dict:
        """
        Calcula números de página para todos os elementos.
        
        Considera:
        - Seções DOCX com diferentes formatos de numeração
        - Quebras de página
        - Elementos flutuantes
        
        Retorna: {
            'capitulos': [
                {'id': 1, 'pagina_inicio': 1, 'pagina_fim': 5},
                # etc.
            ],
            'tabelas': [...],
            'figuras': [...]
        }
        """
    
    def obter_pagina_elemento(self, elemento_tipo: str, elemento_id: int) -> int:
        """
        Obtém o número da página onde um elemento está.
        """
```

### 3. Integração com Serviços Existentes

#### 3.1 `ServicoExtracaoCanonica` - Atualização

```python
class ServicoExtracaoCanonica:
    
    @classmethod
    def extrair(cls, caminho_docx, diretorio_saida):
        # Extração existente...
        
        # Novas extrações
        secoes = ServicoExtracaoSecoes.extrair_secoes(doc)
        quebras = ServicoExtracaoSecoes.extrair_quebras_pagina(doc)
        
        # Classificação de capítulos
        capitulos_classificados = []
        for cap in capitulos:
            classificacao = ServicoClassificacaoCapitulos.classificar_por_estilo(
                cap['estilo'], cap['titulo'], cap['nivel']
            )
            capitulos_classificados.append({**cap, **classificacao})
        
        # Salvar novos arquivos
        caminho_secoes = os.path.join(diretorio_saida, 'canonico_secoes.json')
        with open(caminho_secoes, 'w', encoding='utf-8') as f:
            json.dump({'secoes': secoes, 'quebras': quebras}, f, ensure_ascii=False, indent=2)
        
        return {
            'formatacao': formatacao,
            'macro': macro,
            'capitulos': capitulos_classificados,  # Atualizado
            'secoes': {'secoes': secoes, 'quebras': quebras}  # Novo
        }
```

#### 3.2 `ServicoSincronizarCapitulos` - Atualização

```python
def ressincronizar_capitulos(rel, *, remover_sumidos: bool = False) -> dict:
    # Diff existente...
    
    # Novos passos:
    # 1. Extrair seções e quebras
    secoes = ServicoExtracaoSecoes.extrair_secoes(doc)
    quebras = ServicoExtracaoSecoes.extrair_quebras_pagina(doc)
    
    # 2. Classificar capítulos
    for entrada in info['criar']:
        classificacao = ServicoClassificacaoCapitulos.classificar_por_estilo(
            entrada.get('estilo', ''),
            entrada['titulo'],
            entrada['nivel']
        )
        entrada.update(classificacao)
    
    # 3. Mapear capítulos para seções
    mapeamento = ServicoExtracaoSecoes.mapear_capitulos_secoes(
        info['criar'] + [c for c in capitulos_banco], 
        secoes
    )
    
    # 4. Persistir seções e quebras
    for secao in secoes:
        secao_obj = SecaoDOCX(
            id_relatorio=rel.id,
            **secao
        )
        db.session.add(secao_obj)
    
    # 5. Atualizar capítulos com mapeamento
    for cap in capitulos_atualizados:
        if cap.id in mapeamento:
            cap.id_secao_inicio = mapeamento[cap.id]['inicio']
            cap.id_secao_fim = mapeamento[cap.id]['fim']
    
    # Commit...
```

#### 3.3 `ServicoTOC` - Atualização

```python
class ServicoTOC:
    
    @staticmethod
    def gerar_toc(rel) -> Dict:
        # Obter capítulos classificados
        capitulos = CapituloDocumento.query.filter_by(
            id_relatorio=rel.id,
            ativo=True
        ).order_by('ordem_global').all()
        
        # Obter números de página
        rastreamento = ServicoRastreamentoPaginas(rel.id)
        paginas = rastreamento.calcular_paginas(doc)
        
        # Gerar TOC com números de página
        toc = []
        for cap in capitulos:
            pagina = paginas['capitulos'].get(cap.id, {}).get('pagina_inicio', 0)
            
            item = {
                'titulo': cap.titulo_capitulo,
                'numero': cap.numero_unificado,
                'pagina': pagina,
                'nivel': cap.nivel_capitulo,
                'classificacao': cap.classificacao,
                'prefixo': cap.prefixo_indice
            }
            
            # Formatar baseado na classificação
            if cap.classificacao == 'anexo':
                item['titulo_formatado'] = f"ANEXO {cap.numero_unificado} - {cap.titulo_capitulo}"
            elif cap.classificacao == 'apendice':
                item['titulo_formatado'] = f"APÊNDICE {cap.numero_unificado} - {cap.titulo_capitulo}"
            else:
                item['titulo_formatado'] = f"{cap.numero_unificado} {cap.titulo_capitulo}"
            
            toc.append(item)
        
        return toc
```

### 4. Fluxos de Trabalho

#### 4.1 Fluxo de Extração e Classificação

```
1. Usuário carrega DOCX modelo
2. ServicoExtracaoCanonica.extrair() é chamado
3. Extrai estrutura existente + novas seções/classificação
4. Salva JSONs canônicos atualizados
5. Retorna estrutura classificada para frontend
```

#### 4.2 Fluxo de Sincronização

```
1. Coordenador edita DOCX de produção
2. ServicoSincronizarCapitulos.ressincronizar_capitulos() é chamado
3. Extrai seções e quebras do DOCX atual
4. Classifica capítulos atualizados
5. Mapeia capítulos para seções
6. Atualiza banco com nova classificação e mapeamento
7. Recalcula numeração unificada
8. Recalcula números de página
9. Retorna diff para frontend
```

#### 4.3 Fluxo de Geração de TOC

```
1. Usuário solicita geração de sumário
2. ServicoTOC.gerar_toc() é chamado
3. Obtém capítulos classificados do banco
4. Obtém números de página do ServicoRastreamentoPaginas
5. Formata entradas baseado na classificação
6. Gera TOC com números de página corretos
7. Insere TOC no DOCX
```

### 5. Estratégia de Migração

#### 5.1 Fase 1: Análise e Planejamento
- Analisar todos os serviços existentes
- Documentar dependências e fluxos
- Criar plano de migração faseado

#### 5.2 Fase 2: Implementação de Modelos e Serviços Base
- Criar modelos `SecaoDOCX` e `QuebraPagina`
- Implementar `ServicoClassificacaoCapitulos`
- Implementar `ServicoExtracaoSecoes`
- Adicionar campos ao modelo `CapituloDocumento`

#### 5.3 Fase 3: Integração com Extração Canônica
- Atualizar `ServicoExtracaoCanonica`
- Testar extração com classificação
- Validar com documentos reais

#### 5.4 Fase 4: Integração com Sincronização
- Atualizar `ServicoSincronizarCapitulos`
- Implementar mapeamento capítulo→seção
- Testar sincronização com documentos editados

#### 5.5 Fase 5: Sistema de Numeração e Rastreamento
- Implementar `ServicoNumeracaoUnificada`
- Implementar `ServicoRastreamentoPaginas`
- Testar numeração automática

#### 5.6 Fase 6: Integração com Serviços Dependentes
- Atualizar `ServicoTOC`
- Atualizar `ServicoCrossRefs`
- Atualizar `ServicoCaptioning`
- Atualizar `ServicoMergeDOCX`

#### 5.7 Fase 7: Migração de Dados
- Criar script de migração
- Executar migração em ambiente de teste
- Validar consistência
- Executar migração em produção

#### 5.8 Fase 8: Testes e Validação
- Testes unitários e de integração
- Testes de regressão
- Validação com usuários
- Documentação final

### 6. Considerações de Design

#### 6.1 Compatibilidade Retroativa
- Todos os campos existentes são preservados
- Novos campos são opcionais inicialmente
- Serviços existentes funcionam sem novos campos
- Migração gradual permite rollback

#### 6.2 Performance
- Extração de seções é incremental
- Numeração é calculada sob demanda
- Cache de números de página
- Indexação adequada no banco

#### 6.3 Manutenibilidade
- Serviços novos são independentes
- Baixo acoplamento com serviços existentes
- Interfaces claras entre serviços
- Documentação abrangente

#### 6.4 Testabilidade
- Testes unitários para cada novo serviço
- Testes de integração para fluxos completos
- Testes com documentos reais
- Mock de dependências externas

## Conclusão

Este design propõe uma integração gradual e compatível do novo conceito de capítulos com os serviços existentes do SRA-PLI. A abordagem faseada minimiza riscos e permite validação contínua. A arquitetura modular facilita manutenção e extensões futuras.