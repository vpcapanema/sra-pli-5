# Modelo: Seções DOCX vs Capítulos Conceituais

## Definições Fundamentais

### 1. **Seção DOCX (w:sectPr)**
- **O que é**: Elemento técnico do OOXML que define propriedades de layout
- **Propriedades**:
  - Cabeçalhos/rodapés diferentes
  - Numeração de páginas (reiniciar, estilo diferente)
  - Orientação da página (retrato/paisagem)
  - Margens, tamanho do papel
  - Colunas (1, 2, 3 colunas)
- **Quando usar**: 
  - Nova página com cabeçalho diferente (ex: capa vs conteúdo)
  - Reiniciar numeração de páginas (ex: após sumário)
  - Mudar orientação (ex: apêndice em paisagem)

### 2. **Capítulo Conceitual**
- **O que é**: Unidade lógica de conteúdo com ciclo editorial próprio
- **Propriedades**:
  - Título e índice
  - Responsável atribuído
  - Status editorial (em_edicao, aprovado, etc.)
  - Conteúdo editável
  - Hierarquia (capítulo → subcapítulo)
- **Quando usar**:
  - Divisão temática do documento
  - Atribuição de trabalho colaborativo
  - Controle de revisão independente

### 3. **Quebra de Página (w:br)**
- **O que é**: Instrução de layout para forçar nova página
- **Propriedades**:
  - Apenas muda a posição visual
  - Não afeta formatação ou numeração
- **Quando usar**:
  - Início de novo capítulo em nova página
  - Isolar tabelas/figuras grandes
  - Requisitos estéticos

## Modelo de Dados Integrado

```python
class SecaoDOCX(db.Model):
    """Representa uma seção técnica do DOCX (w:sectPr)."""
    
    __tablename__ = 'secoes_docx'
    
    id_secao = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(db.Integer, db.ForeignKey('relatorios_producao.id'))
    ordem_secao = db.Column(db.Integer)  # Ordem no documento
    tipo_secao = db.Column(db.String(50))  # 'continuo', 'nova_pagina', 'nova_coluna', 'par_impar'
    propriedades = db.Column(db.JSON)  # Propriedades OOXML em JSON
    
    # Propriedades específicas
    reiniciar_numero_pagina = db.Column(db.Boolean, default=False)
    numero_pagina_inicial = db.Column(db.Integer, nullable=True)
    estilo_numero_pagina = db.Column(db.String(50))  # 'decimal', 'roman', 'alphabetic'
    orientacao = db.Column(db.String(20), default='portrait')  # 'portrait', 'landscape'
    colunas = db.Column(db.Integer, default=1)
    
    # Relacionamentos
    relatorio = db.relationship('RelatorioProducao', back_populates='secoes')
    capitulos = db.relationship('CapituloDocumento', back_populates='secao')


class CapituloDocumento(db.Model, AuditoriaMixin):
    """Representa um capítulo conceitual (pode abranger múltiplas seções)."""
    
    __tablename__ = 'capitulos_documento'
    
    id_capitulo_documento = db.Column(db.Integer, primary_key=True)
    id_secao_inicio = db.Column(db.Integer, db.ForeignKey('secoes_docx.id_secao'))
    id_secao_fim = db.Column(db.Integer, db.ForeignKey('secoes_docx.id_secao'), nullable=True)
    
    # Propriedades conceituais
    nivel_capitulo = db.Column(db.Integer, default=1)  # 1=capítulo, ≥2=subcapítulo
    tipo_elemento = db.Column(db.String(50), default='textual')  # pre_textual, textual, pos_textual
    classificacao = db.Column(db.String(50), nullable=True)  # 'anexo', 'apendice', None
    
    # Relacionamentos
    secao = db.relationship('SecaoDOCX', foreign_keys=[id_secao_inicio], back_populates='capitulos')
    secao_fim = db.relationship('SecaoDOCX', foreign_keys=[id_secao_fim])
    
    @property
    def abrange_multiplas_secoes(self):
        """Retorna True se o capítulo abrange mais de uma seção."""
        return self.id_secao_fim is not None and self.id_secao_fim != self.id_secao_inicio


class QuebraPagina(db.Model):
    """Representa uma quebra de página dentro de uma seção."""
    
    __tablename__ = 'quebras_pagina'
    
    id_quebra = db.Column(db.Integer, primary_key=True)
    id_secao = db.Column(db.Integer, db.ForeignKey('secoes_docx.id_secao'))
    posicao_na_secao = db.Column(db.Integer)  # Posição relativa dentro da seção
    tipo_quebra = db.Column(db.String(50))  # 'page', 'column', 'textWrapping'
    forcar_nova_pagina = db.Column(db.Boolean, default=True)
    
    # Relacionamento
    secao = db.relationship('SecaoDOCX', back_populates='quebras')
```

## Fluxo de Extração Canônica

### 1. **Extrair Seções do DOCX**
```python
def extrair_secoes_do_docx(docx_path: str) -> List[SecaoDOCX]:
    """Extrai todas as seções (w:sectPr) do DOCX."""
    from docx import Document
    
    doc = Document(docx_path)
    secoes = []
    
    # python-docx expõe seções através de document.sections
    for i, section in enumerate(doc.sections):
        secao = SecaoDOCX(
            ordem_secao=i,
            tipo_secao=determinar_tipo_secao(section),
            propriedades=extrair_propriedades_secao(section),
            reiniciar_numero_pagina=section.start_type != 'continuous',
            orientacao='landscape' if section.page_width > section.page_height else 'portrait',
            colunas=section.sectPr.xpath('count(w:cols/w:col)') or 1
        )
        secoes.append(secao)
    
    return secoes
```

### 2. **Extrair Capítulos dentro das Seções**
```python
def extrair_capitulos_dentro_secoes(docx_path: str, secoes: List[SecaoDOCX]) -> List[CapituloDocumento]:
    """Extrai capítulos conceituais dentro das seções."""
    from docx import Document
    
    doc = Document(docx_path)
    capitulos = []
    secao_atual = 0
    
    for i, paragraph in enumerate(doc.paragraphs):
        # Verificar se mudou de seção
        if paragraph.contains_page_break or paragraph.style.name in ESTILOS_TITULO:
            # É início de novo capítulo
            
            # Determinar em qual seção está
            secao = determinar_secao_do_paragrafo(i, secoes)
            
            # Classificar como capítulo ou subcapítulo
            nivel = determinar_nivel_por_estilo(paragraph.style.name)
            
            cap = CapituloDocumento(
                id_secao_inicio=secao.id_secao,
                nivel_capitulo=nivel,
                tipo_elemento=classificar_tipo_elemento(paragraph.text, i, len(doc.paragraphs)),
                classificacao=classificar_anexo_apendice(paragraph.text),
                titulo_capitulo=extrair_titulo_sem_indice(paragraph.text),
                indice_capitulo=extrair_indice_do_titulo(paragraph.text)
            )
            
            capitulos.append(cap)
    
    return capitulos
```

### 3. **Extrair Quebras de Página**
```python
def extrair_quebras_pagina(docx_path: str, secoes: List[SecaoDOCX]) -> List[QuebraPagina]:
    """Extrai quebras de página dentro das seções."""
    from docx import Document
    
    doc = Document(docx_path)
    quebras = []
    secao_atual = 0
    posicao_na_secao = 0
    
    for i, paragraph in enumerate(doc.paragraphs):
        # Verificar se parágrafo contém quebra de página
        if hasattr(paragraph, 'runs'):
            for run in paragraph.runs:
                if run.element.xpath('.//w:br[@w:type="page"]'):
                    quebra = QuebraPagina(
                        id_secao=secao_atual,
                        posicao_na_secao=posicao_na_secao,
                        tipo_quebra='page',
                        forcar_nova_pagina=True
                    )
                    quebras.append(quebra)
        
        posicao_na_secao += 1
        
        # Verificar se mudou de seção
        if paragraph.contains_section_break:
            secao_atual += 1
            posicao_na_secao = 0
    
    return quebras
```

## Regras de Mapeamento

### 1. **Um capítulo pode:**
- Começar em uma seção e terminar em outra (capítulos longos)
- Conter múltiplas quebras de página internas
- Ter subcapítulos que compartilham a mesma seção

### 2. **Uma seção pode:**
- Conter múltiplos capítulos (seções longas)
- Ter propriedades de formatação específicas
- Reiniciar numeração de páginas

### 3. **Quebras de página:**
- São sempre dentro de uma seção
- Não afetam propriedades da seção
- Apenas controlam layout visual

## Exemplo Prático

### Documento com estrutura:
```
SEÇÃO 1 (capa, numeração romana)
  - Capa (pré-textual)
  - Folha de rosto (pré-textual)
  QUEBRA DE PÁGINA

SEÇÃO 2 (conteúdo, numeração arábica, reinicia em 1)
  - Sumário (pré-textual)
  QUEBRA DE PÁGINA
  
  CAPÍTULO 1: Introdução
    - 1.1 Contexto (subcapítulo)
    QUEBRA DE PÁGINA
    - 1.2 Objetivos (subcapítulo)
  
  CAPÍTULO 2: Metodologia
    - 2.1 Procedimentos (subcapítulo)

SEÇÃO 3 (anexos, numeração continua)
  - ANEXO A: Dados
  - ANEXO B: Planilhas
```

### Mapeamento no banco:
- **3 Seções DOCX** (capa, conteúdo, anexos)
- **4 Capítulos conceituais** (Capa+Folha, Sumário, Cap1, Cap2, Anexos)
- **2 Subcapítulos** (1.1, 1.2, 2.1)
- **2 Quebras de página** (após capa, após sumário)

## Benefícios da Abordagem

### 1. **Clareza conceitual**
- Seção ≠ Capítulo
- Cada um com responsabilidades claras

### 2. **Preservação técnica**
- Propriedades OOXML mantidas intactas
- Formatação complexa preservada

### 3. **Flexibilidade editorial**
- Capítulos podem cruzar seções
- Controle granular de formatação

### 4. **Rastreabilidade**
- Saber exatamente onde cada elemento está
- Atualizar apenas o necessário

## Próximos Passos

1. **Implementar modelos** `SecaoDOCX` e `QuebraPagina`
2. **Atualizar extração canônica** para capturar seções
3. **Criar serviço** de mapeamento seção→capítulo
4. **Testar** com documentos reais complexos
5. **Documentar** casos de borda
