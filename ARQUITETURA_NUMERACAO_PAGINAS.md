# Arquitetura de Numeração Unificada e Rastreamento de Páginas

## Visão Geral

Sistema centralizado para:
1. **Extrair e normalizar** índices do DOCX
2. **Numerar automaticamente** todos os elementos
3. **Rastrear números de página** dinamicamente
4. **Gerar TOC e listas** precisas

## 1. Extração Inteligente de Índices do DOCX

### Problemas com extração direta:
- Índices podem estar quebrados: "1.", "1)", "(1)", "Capítulo 1"
- Numeração inconsistente: "1.1", "1.1.1", "1.1.a"
- Prefixos variados: "ANEXO A", "Apêndice I", "Anexo_A"

### Solução: Pipeline de Extração e Normalização

```python
class ExtratorIndicesDOCX:
    """Extrai e normaliza índices do DOCX."""
    
    def extrair_indices_do_paragrafo(paragrafo) -> Dict:
        """Extrai índice do texto do parágrafo."""
        texto = paragrafo.text
        
        # Padrões de busca
        padroes = [
            r'^(\d+)\.\s',           # "1. "
            r'^(\d+)\)\s',           # "1) "
            r'^\((\d+)\)\s',         # "(1) "
            r'^Cap[íi]tulo\s+(\d+)', # "Capítulo 1"
            r'^ANEXO\s+([A-Z])',     # "ANEXO A"
            r'^Ap[êe]ndice\s+([IVX]+)', # "Apêndice I"
        ]
        
        for padrao in padroes:
            match = re.match(padrao, texto, re.IGNORECASE)
            if match:
                return {
                    'indice_bruto': match.group(0),
                    'indice_normalizado': match.group(1),
                    'tipo': determinar_tipo_por_padrao(padrao)
                }
        
        return None
```

## 2. Sistema de Numeração Unificada

### Elementos numeráveis:
- **Capítulos/subcapítulos**: 1, 1.1, 1.2, 2, 2.1...
- **Anexos**: ANEXO_A, ANEXO_B...
- **Apêndices**: APENDICE_I, APENDICE_II...
- **Tabelas**: Tabela 1, Tabela 2...
- **Figuras**: Figura 1, Figura 2...
- **Equações**: (1), (2)...
- **Listas**: 1), 2) ou a), b)...

### Arquitetura Centralizada:

```python
class SistemaNumeracaoCentralizado:
    """Gerencia numeração de todos os elementos do documento."""
    
    def __init__(self):
        self.contadores = {
            'capitulo': 0,
            'subcapitulo_nivel_2': {},  # {capitulo_pai: contador}
            'subcapitulo_nivel_3': {},  # {subcapitulo_pai: contador}
            'anexo': 0,
            'apendice': 0,
            'tabela': 0,
            'figura': 0,
            'equacao': 0,
            'lista': {}
        }
        
        self.mapeamento_elementos = {}  # {id_elemento: numero_completo}
    
    def obter_proximo_numero(self, tipo_elemento: str, contexto: str = None) -> str:
        """Obtém próximo número para um tipo de elemento."""
        if tipo_elemento == 'capitulo':
            self.contadores['capitulo'] += 1
            return str(self.contadores['capitulo'])
        
        elif tipo_elemento == 'subcapitulo_nivel_2':
            if contexto not in self.contadores['subcapitulo_nivel_2']:
                self.contadores['subcapitulo_nivel_2'][contexto] = 0
            self.contadores['subcapitulo_nivel_2'][contexto] += 1
            return f"{contexto}.{self.contadores['subcapitulo_nivel_2'][contexto]}"
        
        elif tipo_elemento == 'tabela':
            self.contadores['tabela'] += 1
            return f"Tabela {self.contadores['tabela']}"
        
        elif tipo_elemento == 'figura':
            self.contadores['figura'] += 1
            return f"Figura {self.contadores['figura']}"
        
        elif tipo_elemento == 'anexo':
            self.contadores['anexo'] += 1
            return f"ANEXO_{chr(64 + self.contadores['anexo'])}"
        
        elif tipo_elemento == 'apendice':
            self.contadores['apendice'] += 1
            romanos = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
            if self.contadores['apendice'] <= len(romanos):
                return f"APENDICE_{romanos[self.contadores['apendice'] - 1]}"
            else:
                return f"APENDICE_{chr(64 + self.contadores['apendice'] - 10)}"
```

## 3. Rastreamento Dinâmico de Números de Página

### Desafios:
1. **DOCX muda** durante edição → páginas mudam
2. **Elementos movidos** → números de página mudam
3. **TOC/Listas** precisam ser atualizados

### Solução: Sistema de Bookmarks e Rastreamento

```python
class RastreadorPaginas:
    """Rastreia números de página de elementos no DOCX."""
    
    def __init__(self):
        self.bookmarks_por_elemento = {}  # {id_elemento: bookmark}
        self.paginas_por_bookmark = {}    # {bookmark: numero_pagina}
        self.elementos_por_pagina = {}    # {numero_pagina: [elementos]}
    
    def adicionar_bookmark(self, elemento_id: str, bookmark: str):
        """Adiciona bookmark para um elemento."""
        self.bookmarks_por_elemento[elemento_id] = bookmark
    
    def atualizar_paginas_do_docx(self, docx_path: str):
        """Atualiza números de página lendo o DOCX."""
        from docx import Document
        
        doc = Document(docx_path)
        
        # Simular paginação (simplificado - na prática usar python-docx + análise)
        pagina_atual = 1
        elementos_na_pagina = []
        
        for i, paragraph in enumerate(doc.paragraphs):
            # Verificar se parágrafo contém bookmark
            for elemento_id, bookmark in self.bookmarks_por_elemento.items():
                if bookmark in paragraph.text:
                    self.paginas_por_bookmark[bookmark] = pagina_atual
                    elementos_na_pagina.append(elemento_id)
            
            # Simular quebra de página (heurística simplificada)
            if i % 30 == 0 and i > 0:  # A cada ~30 parágrafos
                self.elementos_por_pagina[pagina_atual] = elementos_na_pagina.copy()
                pagina_atual += 1
                elementos_na_pagina = []
    
    def obter_pagina_do_elemento(self, elemento_id: str) -> Optional[int]:
        """Obtém número da página de um elemento."""
        bookmark = self.bookmarks_por_elemento.get(elemento_id)
        if bookmark:
            return self.paginas_por_bookmark.get(bookmark)
        return None
```

## 4. Geração de TOC e Listas

### TOC (Table of Contents):
```python
class GeradorTOC:
    """Gera Table of Contents com números de página."""
    
    def gerar_toc(self, capitulos: List, rastreador: RastreadorPaginas) -> List[Dict]:
        """Gera TOC com títulos, índices e números de página."""
        toc = []
        
        for cap in capitulos:
            pagina = rastreador.obter_pagina_do_elemento(cap.id_capitulo_documento)
            
            entrada = {
                'titulo': cap.titulo_capitulo,
                'indice': cap.indice_completo,
                'pagina': pagina,
                'nivel': cap.nivel_capitulo,
                'tipo': cap.tipo_conceitual
            }
            
            toc.append(entrada)
        
        return toc
```

### Lista de Figuras/Tabelas:
```python
class GeradorListas:
    """Gera listas de figuras, tabelas, etc."""
    
    def gerar_lista_figuras(self, figuras: List, rastreador: RastreadorPaginas) -> List[Dict]:
        """Gera lista de figuras com legendas e números de página."""
        lista = []
        
        for figura in figuras:
            pagina = rastreador.obter_pagina_do_elemento(figura.id)
            
            entrada = {
                'numero': figura.numero,  # "Figura 1"
                'legenda': figura.legenda,
                'pagina': pagina,
                'referencia': figura.referencia  # "Figura 1 - Descrição"
            }
            
            lista.append(entrada)
        
        return lista
```

## 5. Fluxo de Trabalho Integrado

### Durante extração canônica:
```python
def extrair_e_numerar_documento(docx_path: str):
    """Pipeline completo de extração e numeração."""
    
    # 1. Inicializar sistemas
    numeracao = SistemaNumeracaoCentralizado()
    rastreador = RastreadorPaginas()
    
    # 2. Extrair elementos do DOCX
    elementos = extrair_elementos_do_docx(docx_path)
    
    # 3. Numerar cada elemento
    for elemento in elementos:
        # Determinar tipo
        tipo = classificar_elemento(elemento)
        
        # Obter número
        numero = numeracao.obter_proximo_numero(tipo, elemento.contexto)
        elemento.numero = numero
        
        # Adicionar bookmark
        bookmark = criar_bookmark(elemento)
        rastreador.adicionar_bookmark(elemento.id, bookmark)
        
        # Registrar no mapeamento
        numeracao.mapeamento_elementos[elemento.id] = numero
    
    # 4. Atualizar números de página
    rastreador.atualizar_paginas_do_docx(docx_path)
    
    # 5. Gerar TOC e listas
    toc = GeradorTOC().gerar_toc(capitulos, rastreador)
    lista_figuras = GeradorListas().gerar_lista_figuras(figuras, rastreador)
    lista_tabelas = GeradorListas().gerar_lista_tabelas(tabelas, rastreador)
    
    return {
        'elementos': elementos,
        'toc': toc,
        'lista_figuras': lista_figuras,
        'lista_tabelas': lista_tabelas,
        'numeracao': numeracao,
        'rastreador': rastreador
    }
```

### Durante edição:
```python
def atualizar_apos_edicao(documento_atualizado, sistemas_anteriores):
    """Atualiza numeração e páginas após edição."""
    
    # 1. Recalcular numeração se necessário
    if elementos_foram_adicionados_ou_removidos(documento_atualizado):
        sistemas_anteriores['numeracao'].recalcular_numeracao(documento_atualizado)
    
    # 2. Atualizar números de página
    sistemas_anteriores['rastreador'].atualizar_paginas_do_docx(documento_atualizado.caminho)
    
    # 3. Regenerar TOC e listas
    novo_toc = GeradorTOC().gerar_toc(
        documento_atualizado.capitulos, 
        sistemas_anteriores['rastreador']
    )
    
    # 4. Atualizar DOCX com novos números e TOC
    atualizar_docx_com_numeracao(
        documento_atualizado.caminho,
        sistemas_anteriores['numeracao'],
        novo_toc
    )
```

## 6. Modelo de Dados Unificado

```python
class ElementoNumeravel(db.Model):
    """Modelo base para todos os elementos numeráveis."""
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50))  # 'capitulo', 'figura', 'tabela', etc.
    numero = db.Column(db.String(50))  # Número completo: "1", "Figura 1", "ANEXO_A"
    numero_sequencial = db.Column(db.Integer)  # Número sequencial: 1, 2, 3...
    contexto = db.Column(db.String(100))  # Contexto para numeração hierárquica
    bookmark = db.Column(db.String(200))  # Bookmark no DOCX
    pagina = db.Column(db.Integer)  # Número da página (atualizável)
    titulo = db.Column(db.String(500))
    legenda = db.Column(db.Text)  # Para figuras/tabelas
    
    # Relacionamentos
    capitulo_pai_id = db.Column(db.Integer, db.ForeignKey('capitulos_documento.id_capitulo_documento'))
    capitulo_pai = db.relationship('CapituloDocumento', backref='elementos_numeraveis')
    
    # Métodos
    def atualizar_pagina(self, nova_pagina: int):
        """Atualiza número da página."""
        self.pagina = nova_pagina
        # Atualizar bookmark no DOCX se necessário
    
    def obter_referencia_cruzada(self) -> str:
        """Gera referência cruzada: "Figura 1 (página 5)"."""
        if self.pagina:
            return f"{self.numero} (página {self.pagina})"
        return self.numero
```

## 7. Considerações de Implementação

### Desafios Técnicos:
1. **Performance**: Documentos grandes (1000+ elementos)
2. **Precisão**: Rastreamento exato de páginas
3. **Consistência**: Manter numeração durante colab

### Soluções:
- **Cache** de numeração e páginas
- **Processamento incremental** apenas de mudanças
- **Versionamento** de estados de numeração
- **Validação** cruzada entre extração e numeração

### Próximos Passos:
1. Implementar `SistemaNumeracaoCentralizado`
2. Criar `RastreadorPaginas` com python-docx
3. Integrar com extração canônica existente
4. Testar com documentos reais
5. Otimizar performance
