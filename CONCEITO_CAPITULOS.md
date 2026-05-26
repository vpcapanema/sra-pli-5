# Conceito de Capítulos no SRA

## Definições Estruturais

### 1. Capítulo (nível 1)
- **Definição**: Divisão textual de primeiro nível
- **Nível**: `nivel_capitulo = 1`
- **Tipo**: `tipo_elemento = 'textual'`
- **Pai**: `id_capitulo_pai = NULL`
- **Índice**: Numeração arábica (1, 2, 3...)
- **Exemplo**: "1. Introdução", "2. Metodologia"

### 2. Subcapítulo (nível ≥ 2)
- **Definição**: Divisão dentro de um capítulo
- **Nível**: `nivel_capitulo ≥ 2`
- **Tipo**: Herda do capítulo pai (`textual`)
- **Pai**: Referência a um `CapituloDocumento`
- **Índice**: Hierárquico (1.1, 1.2, 2.1...)
- **Exemplo**: "1.1 Contexto", "2.1.1 Análise Preliminar"

### 3. Anexo (pós-textual)
- **Definição**: Documento complementar referenciado
- **Tipo**: `tipo_elemento = 'pos_textual'`
- **Classificação**: `classificacao = 'anexo'`
- **Prefixo**: `ANEXO_`
- **Índice**: Alfabético maiúsculo (A, B, C...)
- **Exemplo**: "ANEXO_A - Planilhas de Dados"

### 4. Apêndice (pós-textual)
- **Definição**: Conteúdo explicativo complementar
- **Tipo**: `tipo_elemento = 'pos_textual'`
- **Classificação**: `classificacao = 'apendice'`
- **Prefixo**: `APENDICE_`
- **Índice**: Romano maiúsculo (I, II, III...)
- **Exemplo**: "APENDICE_I - Glossário de Termos"

## Regras de Validação

### Para criação/atualização:
1. **Capítulo (nível 1)**:
   - `nivel_capitulo = 1`
   - `id_capitulo_pai IS NULL`
   - `tipo_elemento = 'textual'`

2. **Subcapítulo**:
   - `nivel_capitulo ≥ 2`
   - `id_capitulo_pai NOT NULL`
   - `tipo_elemento` igual ao do pai

3. **Anexo/Apêndice**:
   - `tipo_elemento = 'pos_textual'`
   - `classificacao IN ('anexo', 'apendice')`
   - Pode ter hierarquia própria

### Para índices:
- **Capítulos**: 1, 2, 3...
- **Subcapítulos**: 1.1, 1.2, 2.1...
- **Anexos**: ANEXO_A, ANEXO_B...
- **Apêndices**: APENDICE_I, APENDICE_II...

## Campos do Modelo Sugeridos

```python
class CapituloDocumento:
    # Campos existentes
    nivel_capitulo = db.Column(db.Integer, default=1)  # 1=capítulo, ≥2=subcapítulo
    tipo_elemento = db.Column(db.String(50), default='textual')  # pre_textual, textual, pos_textual
    
    # Novo campo sugerido
    classificacao = db.Column(db.String(50), nullable=True)  # 'anexo', 'apendice', None
    prefixo_indice = db.Column(db.String(20), nullable=True)  # 'ANEXO_', 'APENDICE_', None
```

## Fluxo de Trabalho

### Extração do Modelo DOCX:
1. Identificar seções de primeiro nível → **Capítulos**
2. Identificar subseções → **Subcapítulos**
3. Identificar conteúdo pós-textual → **Anexos/Apêndices**

### Atribuição:
1. Coordenador atribui **capítulos** a autores
2. **Subcapítulos** herdam responsável do pai
3. **Anexos/Apêndices** podem ter responsável específico

### Edição:
1. Autor edita **capítulo** atribuído
2. **Subcapítulos** editados junto com o capítulo
3. **Anexos/Apêndices** editados separadamente

## Benefícios da Abordagem

1. **Clareza conceitual**: Distinção clara entre níveis
2. **Consistência terminológica**: Alinhada com normas técnicas
3. **Flexibilidade**: Suporte a anexos/apêndices
4. **Validação robusta**: Regras claras para cada tipo
5. **Interface intuitiva**: Usuário entende a hierarquia

## Exemplo de Estrutura

```
RELATÓRIO TÉCNICO
├── 1. INTRODUÇÃO (capítulo, nivel=1)
│   ├── 1.1 Contexto (subcapítulo, nivel=2)
│   └── 1.2 Objetivos (subcapítulo, nivel=2)
├── 2. METODOLOGIA (capítulo, nivel=1)
│   └── 2.1 Procedimentos (subcapítulo, nivel=2)
├── ANEXO_A - DADOS BRUTOS (anexo, pos_textual)
└── APENDICE_I - GLOSSÁRIO (apêndice, pos_textual)
```

## Próximos Passos

1. Adicionar campo `classificacao` ao modelo
2. Implementar validações no modelo/serviço
3. Atualizar extração canônica para classificar
4. Ajustar UI para mostrar prefixos
5. Documentar nas regras de negócio
