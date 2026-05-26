# Script de commit e push automatizado com feedback visual
# Uso: .\git-commit-push.ps1 "mensagem do commit"

param(
    [Parameter(Mandatory=$true)]
    [string]$CommitMessage
)

# Configurar encoding para UTF-8
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Função para exibir mensagens com formatação
function Write-Step {
    param(
        [string]$Message,
        [string]$Status = "INFO",
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $formattedMessage = "[$timestamp] [$Status] $Message"
    
    switch ($Status) {
        "SUCCESS" { $Color = "Green" }
        "ERROR" { $Color = "Red" }
        "WARNING" { $Color = "Yellow" }
        "INFO" { $Color = "Cyan" }
    }
    
    Write-Host $formattedMessage -ForegroundColor $Color
}

function Write-Section {
    param([string]$Title)
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor DarkGray
    Write-Host "  $Title" -ForegroundColor White
    Write-Host "=" * 60 -ForegroundColor DarkGray
    Write-Host ""
}

function Write-FinalStatus {
    param(
        [string]$Message,
        [bool]$Success = $true
    )
    
    Write-Host ""
    Write-Host "*" * 70 -ForegroundColor DarkGray
    if ($Success) {
        Write-Host "  [SUCCESS] $Message" -ForegroundColor Green -BackgroundColor DarkGray
    } else {
        Write-Host "  [ERROR] $Message" -ForegroundColor Red -BackgroundColor DarkGray
    }
    Write-Host "*" * 70 -ForegroundColor DarkGray
    Write-Host ""
}

# Início do processo
Write-Section -Title "INICIO DO PROCESSO DE COMMIT E PUSH"
Write-Step -Message "Iniciando processo de commit e push..." -Status "INFO"
Write-Step -Message "Mensagem do commit: '$CommitMessage'" -Status "INFO"

# ============================================
# ETAPA 1: Verificar status do git
# ============================================
Write-Section -Title "ETAPA 1: VERIFICAR STATUS DO GIT"

try {
    $status = git status
    if ($LASTEXITCODE -eq 0) {
        Write-Step -Message "Status do repositorio verificado com sucesso" -Status "SUCCESS"
        
        # Verificar se há mudanças
        if ($status -match "nothing to commit") {
            Write-Step -Message "Nenhuma mudanca para commitar" -Status "WARNING"
            Write-FinalStatus -Message "PROCESSO CONCLUIDO: Nenhuma mudanca para commitar" -Success $true
            exit 0
        } else {
            Write-Step -Message "Mudancas detectadas para commit" -Status "SUCCESS"
        }
    } else {
        Write-Step -Message "Erro ao verificar status do git" -Status "ERROR"
        Write-FinalStatus -Message "PROCESSO FALHOU: Erro ao verificar status" -Success $false
        exit 1
    }
} catch {
    Write-Step -Message "Erro inesperado: $_" -Status "ERROR"
    Write-FinalStatus -Message "PROCESSO FALHOU: Erro inesperado" -Success $false
    exit 1
}

# ============================================
# ETAPA 2: Adicionar todas as mudanças
# ============================================
Write-Section -Title "ETAPA 2: ADICIONAR MUDANCAS"

try {
    Write-Step -Message "Adicionando todas as mudancas..." -Status "INFO"
    git add .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Step -Message "Mudancas adicionadas com sucesso ao staging" -Status "SUCCESS"
    } else {
        Write-Step -Message "Erro ao adicionar mudancas" -Status "ERROR"
        Write-FinalStatus -Message "PROCESSO FALHOU: Erro ao adicionar mudancas" -Success $false
        exit 1
    }
} catch {
    Write-Step -Message "Erro inesperado: $_" -Status "ERROR"
    Write-FinalStatus -Message "PROCESSO FALHOU: Erro inesperado" -Success $false
    exit 1
}

# ============================================
# ETAPA 3: Fazer commit
# ============================================
Write-Section -Title "ETAPA 3: FAZER COMMIT"

try {
    Write-Step -Message "Fazendo commit com mensagem: '$CommitMessage'" -Status "INFO"
    git commit -m $CommitMessage
    
    if ($LASTEXITCODE -eq 0) {
        Write-Step -Message "Commit realizado com sucesso" -Status "SUCCESS"
        
        # Mostrar hash do commit
        $commitHash = git log --oneline -1
        Write-Step -Message "Commit: $commitHash" -Status "INFO"
    } else {
        Write-Step -Message "Erro ao fazer commit" -Status "ERROR"
        Write-FinalStatus -Message "PROCESSO FALHOU: Erro ao fazer commit" -Success $false
        exit 1
    }
} catch {
    Write-Step -Message "Erro inesperado: $_" -Status "ERROR"
    Write-FinalStatus -Message "PROCESSO FALHOU: Erro inesperado" -Success $false
    exit 1
}

# ============================================
# ETAPA 4: Fazer push para origin/master
# ============================================
Write-Section -Title "ETAPA 4: FAZER PUSH PARA ORIGIN/MASTER"

try {
    Write-Step -Message "Fazendo push para origin/master..." -Status "INFO"
    git push origin master
    
    if ($LASTEXITCODE -eq 0) {
        Write-Step -Message "Push realizado com sucesso para origin/master" -Status "SUCCESS"
    } else {
        Write-Step -Message "Erro ao fazer push" -Status "ERROR"
        Write-FinalStatus -Message "PROCESSO FALHOU: Erro ao fazer push" -Success $false
        exit 1
    }
} catch {
    Write-Step -Message "Erro inesperado: $_" -Status "ERROR"
    Write-FinalStatus -Message "PROCESSO FALHOU: Erro inesperado" -Success $false
    exit 1
}

# ============================================
# ETAPA 5: Verificar log final
# ============================================
Write-Section -Title "ETAPA 5: VERIFICAR LOG FINAL"

try {
    Write-Step -Message "Exibindo ultimos 3 commits..." -Status "INFO"
    $log = git log --oneline -3
    
    if ($LASTEXITCODE -eq 0) {
        Write-Step -Message "Log exibido com sucesso:" -Status "SUCCESS"
        Write-Host ""
        $log | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        Write-Host ""
    } else {
        Write-Step -Message "Erro ao exibir log" -Status "WARNING"
    }
} catch {
    Write-Step -Message "Erro ao exibir log: $_" -Status "WARNING"
}

# ============================================
# STATUS FINAL
# ============================================
Write-FinalStatus -Message "PROCESSO CONCLUIDO COM SUCESSO!" -Success $true
Write-Step -Message "Resumo:" -Status "INFO"
Write-Step -Message "  - Status verificado [OK]" -Status "INFO"
Write-Step -Message "  - Mudancas adicionadas [OK]" -Status "INFO"
Write-Step -Message "  - Commit realizado [OK]" -Status "INFO"
Write-Step -Message "  - Push para origin/master [OK]" -Status "INFO"
Write-Step -Message "  - Log verificado [OK]" -Status "INFO"
Write-Host ""

exit 0