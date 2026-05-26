# Mapeamento entre Tipos Conceituais e Estilos DOCX

## Visão Geral

Este documento define o mapeamento entre os **tipos conceituais de capítulos** e os **estilos DOCX** correspondentes. Este mapeamento é essencial para:

1. **Classificação automática** durante extração canônica
2. **Atualização automática de índices** quando capítulos são adicionados/removidos
3. **Preservação da formatação** durante merge de documentos
4. **Geração consistente** de TOC (Table of Contents)

## Mapeamento Principal

| Tipo Conceitual | Estilos DOCX Correspondentes | Nível | Prefixo Índice | Exemplo de Índice |
|-----------------|-----------------------------|-------|----------------|-------------------|
| **Capítulo** | `Heading 1`, `Título 1`, `Titulo 1` | 1 | (nenhum) | `1`, `2`, `3` |
| **Subcapítulo** | `Heading 2`, `Título 2`, `Titulo 2` | 2 | (herda) | `1.1`, `1.2`, `2.1` |
| **Subcapítulo Nível 3** | `Heading 3`, `Título 3`, `Titulo 3` | 3 | (herda) | `1.1.1`, `2.1.1` |
| **Anexo** | `Heading 1` + estilo "Anexo", `Anexo` | 1 | `ANEXO_` | `ANEXO_A`, `ANEXO_B` |
| **Apêndice** | `Heading 1` + estilo "Apêndice", `Apêndice` | 1 | `APENDICE_` | `APENDICE_I`, `APENDICE_II` |
| **Pré-textual** | `Title`, `Capa`, `Resumo`, `Abstract` | 1 | (nenhum) | (não numerado) |
| **Pós-textual** | `Referências`, `Bibliografia` | 1 | (nenhum) | (não numerado) |

## Regras de Atualização Automática de Índices

### 1. Quando um capítulo é **adicionado**:
```python
# Exemplo: Adicionar novo capítulo entre 2 e 3
# Antes: 1, 2, 3, 4
# Depois: 1, 2, 2.1, 3, 4 (se for subcapítulo de 2)
# Ou: 1, 2, 3, 4, 5 (se for novo capítulo no final)
```

### 2. Quando um capítulo é **removido**:
```python
# Exemplo: Remover capítulo 2
# Antes: 1, 2, 3, 4
# Depois: 1, 2, 3 (renumerar: 3→2, 4→3)
```

### 3. Quando um **subcapítulo** é adicionado:
```python
# Exemplo: Adicionar subcapítulo 1.2 entre 1.1 e 1.3
# Antes: 1.1, 1.3
# Depois: 1.1, 1.2, 1.3
```

## Algoritmo de Atualização

```python
def atualizar_indices_capitulos(capitulos: List[CapituloDocumento], 
                                tipo_operacao: str,
                                capitulo_afetado: CapituloDocumento):
    """
    Atualiza índices após operação em capítulos.
    
    Args:
        capitulos: Lista de todos os capítulos do relatório
        tipo_operacao: 'adicao', 'remocao', 'reordenacao'
        capitulo_afetado: Capítulo que foi adicionado/removido/reordenado
    """
    
    # 1. Filtrar capítulos por tipo e nível
    capitulos_textuais = [c for c in capitulos if c.tipo_elemento == 'textual']
    anexos = [c for c in capitulos if c.classificacao == 'anexo']
    apendices = [c for c in capitulos if c.classificacao == 'apendice']
    
    # 2. Atualizar índices textuais
    for i, cap in enumerate(sorted(capitulos_textuais, key=lambda x: x.ordem_capitulo), 1):
        if cap.nivel_capitulo == 1:
            cap.indice_capitulo = str(i)
        elif cap.nivel_capitulo >= 2 and cap.capitulo_pai:
            # Subcapítulo: índice hierárquico
            seq = obter_sequencia_subcapitulo(cap.capitulo_pai, cap)
            cap.indice_capitulo = f"{cap.capitulo_pai.indice_capitulo}.{seq}"
    
    # 3. Atualizar índices de anexos (A, B, C...)
    for i, anexo in enumerate(sorted(anexos, key=lambda x: x.ordem_capitulo), 1):
        letra = chr(64 + i)  # A=65, B=66, etc.
        anexo.indice_capitulo = letra
    
    # 4. Atualizar índices de apêndices (I, II, III...)
    romanos = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
    for i, apendice in enumerate(sorted(apendices, key=lambda x: x.ordem_capitulo), 1):
        if i <= len(romanos):
            apendice.indice_capitulo = romanos[i-1]
        else:
            # Fallback para alfabético após X
            apendice.indice_capitulo = chr(64 + i - 10)
```

## Detecção Automática por Estilo DOCX

### Padrões de Estilo para Classificação:

```python
ESTILOS_PARA_CLASSIFICACAO = {
    # Capítulos
    'capitulo': [
        'Heading 1', 'Título 1', 'Titulo 1', 
        'TÍTULO 1', 'Titulo1', 'Heading1'
    ],
    
    # Subcapítulos
    'subcapitulo_nivel_2': [
        'Heading 2', 'Título 2', 'Titulo 2',
        'TÍTULO 2', 'Titulo2', 'Heading2'
    ],
    
    'subcapitulo_nivel_3': [
        'Heading 3', 'Título 3', 'Titulo 3',
        'TÍTULO 3', 'Titulo3', 'Heading3'
    ],
    
    # Anexos
    'anexo': [
        'Anexo', 'ANEXO', 'Anexo A', 'Anexo_A',
        'Heading 1 + Anexo', 'Título Anexo'
    ],
    
    # Apêndices
    'apendice': [
        'Apêndice', 'APÊNDICE', 'Apêndice I', 'Apêndice_I',
        'Heading 1 + Apêndice', 'Título Apêndice'
    ],
    
    # Pré-textuais
    'pre_textual': [
        'Title', 'Capa', 'Folha de Rosto', 'Resumo',
        'Abstract', 'Sumário', 'Sumario', 'Lista de Figuras'
    ],
    
    # Pós-textuais
    'pos_textual': [
        'Referências', 'Referencias', 'Bibliografia',
        'Glossário', 'Glossario', 'Índice', 'Indice'
    ]
}
```

## Integração com Serviço de Extração Canônica

### Fluxo de Classificação:

1. **Extrair estilos** do DOCX usando `python-docx`
2. **Mapear para tipo conceitual** usando a tabela acima
3. **Definir nível hierárquico** baseado no estilo
4. **Gerar índice apropriado** para o tipo
5. **Criar objeto** `CapituloDocumento` com todas as propriedades

### Exemplo de Código:

```python
def extrair_e_classificar_capitulos(docx_path: str) -> List[CapituloDocumento]:
    """Extrai e classifica capítulos de um DOCX."""
    from docx import Document
    
    doc = Document(docx_path)
    capitulos = []
    
    for i, paragraph in enumerate(doc.paragraphs):
        estilo = paragraph.style.name if paragraph.style else None
        
        if estilo in ESTILOS_PARA_CLASSIFICACAO['capitulo']:
            # É um capítulo
            cap = CapituloDocumento(
                nivel_capitulo=1,
                tipo_elemento='textual',
                estilo_docx=estilo,
                titulo_capitulo=paragraph.text,
                ordem_capitulo=i
            )
            capitulos.append(cap)
            
        elif estilo in ESTILOS_PARA_CLASSIFICACAO['anexo']:
            # É um anexo
            cap = CapituloDocumento(
                nivel_capitulo=1,
                tipo_elemento='pos_textual',
                classificacao='anexo',
                estilo_docx=estilo,
                titulo_capitulo=paragraph.text,
                ordem_capitulo=i
            )
            capitulos.append(cap)
    
    # Atualizar índices automaticamente
    atualizar_indices_capitulos(capitulos, 'adicao', None)
    
    return capitulos
```

## Considerações de Implementação

### 1. **Estilos Personalizados**:
- O sistema deve suportar estilos personalizados do usuário
- Usar fallback para detecção por título/conteúdo
- Permitir mapeamento manual via interface

### 2. **Atualização em Tempo Real**:
- Índices devem ser atualizados imediatamente após operações
- Notificar usuário sobre mudanças
- Oferecer opção de desfazer

### 3. **Consistência com TOC**:
- O TOC do DOCX deve ser regenerado após atualizações
- Manter bookmarks consistentes
- Preservar hyperlinks internos

### 4. **Performance**:
- Otimizar para documentos grandes (100+ capítulos)
- Usar transações em lote para atualizações
- Cache de índices quando possível

## Próximos Passos

1. **Implementar** o mapeamento no `ServicoClassificacaoCapitulos`
2. **Atualizar** serviço de extração canônica
3. **Criar** interface para mapeamento manual
4. **Testar** com documentos reais
5. **Documentar** casos de borda e exceções
