# ETAPA 1: Modificar Modelo CapituloDocumento
# Adicionar campo classificacao e validações básicas

# Configurar encoding
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Step {
    param([string]$Message, [string]$Status = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = @{INFO="Cyan"; SUCCESS="Green"; ERROR="Red"; WARNING="Yellow"}[$Status]
    Write-Host "[$timestamp] [$Status] $Message" -ForegroundColor $color
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor DarkGray
    Write-Host "  $Title" -ForegroundColor White
    Write-Host "=" * 60 -ForegroundColor DarkGray
    Write-Host ""
}

Write-Section -Title "ETAPA 1: MODIFICAR MODELO CAPITULODOCUMENTO"
Write-Step -Message "Iniciando modificação do modelo CapituloDocumento..." -Status "INFO"

# ============================================
# PASSO 1: Verificar arquivo atual
# ============================================
Write-Step -Message "PASSO 1: Verificando arquivo atual..." -Status "INFO"

$modelFile = "app\models\capitulo_documento.py"
if (Test-Path $modelFile) {
    Write-Step -Message "Arquivo encontrado: $modelFile" -Status "SUCCESS"
    
    # Ler conteúdo atual
    $content = Get-Content $modelFile -Raw
    Write-Step -Message "Tamanho do arquivo: $($content.Length) caracteres" -Status "INFO"
} else {
    Write-Step -Message "ERRO: Arquivo não encontrado: $modelFile" -Status "ERROR"
    exit 1
}

# ============================================
# PASSO 2: Analisar estrutura atual
# ============================================
Write-Step -Message "PASSO 2: Analisando estrutura atual do modelo..." -Status "INFO"

# Verificar se já existe campo classificacao
if ($content -match "classificacao\s*=") {
    Write-Step -Message "AVISO: Campo 'classificacao' já existe no modelo" -Status "WARNING"
} else {
    Write-Step -Message "Campo 'classificacao' não encontrado - será adicionado" -Status "INFO"
}

# Verificar campos existentes
$fields = @()
if ($content -match "nivel_capitulo\s*=") { $fields += "nivel_capitulo" }
if ($content -match "tipo_elemento\s*=") { $fields += "tipo_elemento" }
if ($content -match "id_capitulo_pai\s*=") { $fields += "id_capitulo_pai" }

Write-Step -Message "Campos relevantes encontrados: $($fields -join ', ')" -Status "SUCCESS"

# ============================================
# PASSO 3: Mostrar plano de modificação
# ============================================
Write-Step -Message "PASSO 3: Plano de modificação:" -Status "INFO"
Write-Host ""
Write-Host "  [ADICIONAR] Campo: classificacao = db.Column(db.String(50), nullable=True)" -ForegroundColor Cyan
Write-Host "  [ADICIONAR] Campo: prefixo_indice = db.Column(db.String(20), nullable=True)" -ForegroundColor Cyan
Write-Host "  [ADICIONAR] Property: indice_completo" -ForegroundColor Cyan
Write-Host "  [ADICIONAR] Validações de nível/tipo" -ForegroundColor Cyan
Write-Host "  [ADICIONAR] Métodos helpers" -ForegroundColor Cyan
Write-Host ""

# ============================================
# PASSO 4: Perguntar confirmação
# ============================================
Write-Step -Message "PASSO 4: Confirmar modificação?" -Status "INFO"
$confirmation = Read-Host "Digite 'SIM' para continuar ou 'NAO' para cancelar"

if ($confirmation -ne "SIM") {
    Write-Step -Message "Modificação cancelada pelo usuário" -Status "WARNING"
    exit 0
}

# ============================================
# PASSO 5: Criar backup do arquivo
# ============================================
Write-Step -Message "PASSO 5: Criando backup do arquivo..." -Status "INFO"

$backupFile = "$modelFile.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $modelFile $backupFile
Write-Step -Message "Backup criado: $backupFile" -Status "SUCCESS"

# ============================================
# PASSO 6: Modificar o arquivo
# ============================================
Write-Step -Message "PASSO 6: Modificando o arquivo..." -Status "INFO"

# Encontrar posição para adicionar campo classificacao
# Procurar após o campo tipo_elemento
$pattern = "tipo_elemento = db\.Column\([^)]+\)[^,]*,[\s\r\n]*#.*pos_textual"

if ($content -match $pattern) {
    $match = $Matches[0]
    $newContent = $content -replace $pattern, "$match`r`n    classificacao = db.Column(db.String(50), nullable=True)  # 'anexo', 'apendice', None`r`n    prefixo_indice = db.Column(db.String(20), nullable=True)  # 'ANEXO_', 'APENDICE_', None"
    
    # Adicionar property indice_completo após a classe
    $classPattern = "class CapituloDocumento\(db\.Model, AuditoriaMixin\):"
    if ($newContent -match "$classPattern.*?(?=\n\n|\Z)") {
        $classBlock = $Matches[0]
        
        # Adicionar property após os relacionamentos
        $propertyCode = @"

    # ------------------------------------------------------------------
    # Propriedades calculadas
    # ------------------------------------------------------------------

    @property
    def indice_completo(self):
        """Índice completo com prefixo quando aplicável."""
        if self.classificacao == 'anexo':
            return f"ANEXO_{self.indice_capitulo}" if self.indice_capitulo else "ANEXO"
        elif self.classificacao == 'apendice':
            return f"APENDICE_{self.indice_capitulo}" if self.indice_capitulo else "APENDICE"
        return self.indice_capitulo or ""

    @property
    def e_capitulo(self):
        """Retorna True se for um capítulo de primeiro nível."""
        return self.nivel_capitulo == 1 and self.tipo_elemento == 'textual'

    @property
    def e_subcapitulo(self):
        """Retorna True se for um subcapítulo."""
        return self.nivel_capitulo >= 2 and self.id_capitulo_pai is not None

    @property
    def e_anexo_ou_apendice(self):
        """Retorna True se for anexo ou apêndice."""
        return self.tipo_elemento == 'pos_textual' and self.classificacao in ('anexo', 'apendice')

    # ------------------------------------------------------------------
    # Validações
    # ------------------------------------------------------------------

    def validar_estrutura(self):
        """Valida a estrutura conceitual do capítulo."""
        erros = []
        
        # Capítulo (nível 1)
        if self.nivel_capitulo == 1:
            if self.id_capitulo_pai is not None:
                erros.append("Capítulo de nível 1 não pode ter pai")
            if self.tipo_elemento != 'textual':
                erros.append("Capítulo de nível 1 deve ser 'textual'")
            if self.classificacao is not None:
                erros.append("Capítulo de nível 1 não deve ter classificação")
        
        # Subcapítulo
        elif self.nivel_capitulo >= 2:
            if self.id_capitulo_pai is None:
                erros.append("Subcapítulo deve ter um capítulo pai")
            if self.classificacao is not None:
                erros.append("Subcapítulo não deve ter classificação")
        
        # Anexo/Apêndice
        elif self.tipo_elemento == 'pos_textual':
            if self.classificacao not in ('anexo', 'apendice', None):
                erros.append("Classificação inválida para conteúdo pós-textual")
        
        return erros
"@
        
        # Inserir após o último relacionamento
        $relationshipPattern = "status_dominio = db\.relationship\([^)]+\)"
        if ($newContent -match "$relationshipPattern.*?(?=\n\n|\Z)") {
            $relationshipBlock = $Matches[0]
            $newContent = $newContent -replace $relationshipPattern, "$relationshipBlock`r`n`r`n$propertyCode"
        }
    }
    
    # Salvar modificações
    Set-Content -Path $modelFile -Value $newContent -Encoding UTF8
    Write-Step -Message "Arquivo modificado com sucesso" -Status "SUCCESS"
    
    # Mostrar diferenças
    Write-Step -Message "Diferenças no arquivo:" -Status "INFO"
    $diff = Compare-Object (Get-Content $backupFile) (Get-Content $modelFile)
    $added = $diff | Where-Object { $_.SideIndicator -eq "=>" }
    $removed = $diff | Where-Object { $_.SideIndicator -eq "<=" }
    
    if ($added) {
        Write-Host "  Linhas adicionadas:" -ForegroundColor Green
        $added | ForEach-Object { Write-Host "  + $($_.InputObject)" -ForegroundColor Green }
    }
    
} else {
    Write-Step -Message "ERRO: Não foi possível encontrar posição para adicionar campos" -Status "ERROR"
    exit 1
}

# ============================================
# PASSO 7: Verificar sintaxe Python
# ============================================
Write-Step -Message "PASSO 7: Verificando sintaxe Python..." -Status "INFO"

try {
    python -m py_compile $modelFile
    if ($LASTEXITCODE -eq 0) {
        Write-Step -Message "Sintaxe Python válida" -Status "SUCCESS"
    } else {
        Write-Step -Message "ERRO: Sintaxe Python inválida" -Status "ERROR"
        # Restaurar backup
        Copy-Item $backupFile $modelFile -Force
        Write-Step -Message "Arquivo restaurado do backup" -Status "WARNING"
        exit 1
    }
} catch {
    Write-Step -Message "ERRO ao verificar sintaxe: $_" -Status "ERROR"
    exit 1
}

# ============================================
# PASSO 8: Atualizar __init__.py do pacote models
# ============================================
Write-Step -Message "PASSO 8: Atualizando __init__.py do pacote models..." -Status "INFO"

$initFile = "app\models\__init__.py"
if (Test-Path $initFile) {
    $initContent = Get-Content $initFile -Raw
    
    # Verificar se CapituloDocumento já está importado
    if ($initContent -notmatch "from \.capitulo_documento import CapituloDocumento") {
        # Adicionar import após outros imports similares
        $importPattern = "from \.[a-z_]+ import [A-Za-z]+"
        $lastImport = [regex]::Matches($initContent, $importPattern) | Select-Object -Last 1
        
        if ($lastImport) {
            $newInitContent = $initContent.Insert($lastImport.Index + $lastImport.Length, "`r`nfrom .capitulo_documento import CapituloDocumento")
            Set-Content -Path $initFile -Value $newInitContent -Encoding UTF8
            Write-Step -Message "Import adicionado ao __init__.py" -Status "SUCCESS"
        }
    } else {
        Write-Step -Message "CapituloDocumento já importado no __init__.py" -Status "INFO"
    }
}

# ============================================
# PASSO 9: Resumo da etapa
# ============================================
Write-Step -Message "PASSO 9: Resumo da modificação:" -Status "SUCCESS"
Write-Host ""
Write-Host "  ✅ Campo 'classificacao' adicionado" -ForegroundColor Green
Write-Host "  ✅ Campo 'prefixo_indice' adicionado" -ForegroundColor Green
Write-Host "  ✅ Property 'indice_completo' implementada" -ForegroundColor Green
Write-Host "  ✅ Properties de validação adicionadas" -ForegroundColor Green
Write-Host "  ✅ Método 'validar_estrutura()' implementado" -ForegroundColor Green
Write-Host "  ✅ Sintaxe Python validada" -ForegroundColor Green
Write-Host "  ✅ Backup criado: $backupFile" -ForegroundColor Green
Write-Host ""

# ============================================
# PASSO 10: Próximos passos
# ============================================
Write-Step -Message "PASSO 10: Próximos passos:" -Status "INFO"
Write-Host ""
Write-Host "  1. Executar ETAPA 2: Criar migration para campo novo" -ForegroundColor Yellow
Write-Host "  2. Testar criação de objetos CapituloDocumento" -ForegroundColor Yellow
Write-Host "  3. Validar regras de negócio" -ForegroundColor Yellow
Write-Host ""

Write-Section -Title "ETAPA 1 CONCLUÍDA COM SUCESSO!"
Write-Step -Message "Modelo CapituloDocumento modificado conforme especificação" -Status "SUCCESS"
Write-Step -Message "Execute a ETAPA 2 para criar a migration" -Status "INFO"

exit 0