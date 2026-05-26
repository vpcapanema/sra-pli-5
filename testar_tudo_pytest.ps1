# SCRIPT PARA TESTAR TUDO COM PYTEST
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TESTANDO CONFIGURAÇÃO COMPLETA - PYTEST" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host

# PASSO 1: Verificar ambiente
Write-Host "1. VERIFICANDO AMBIENTE:" -ForegroundColor Yellow
. 'D:\REPOSITORIOS\sra-pli-5\.venv\Scripts\Activate.ps1'

Write-Host "   Python:" -ForegroundColor White
python --version

Write-Host "   Pytest:" -ForegroundColor White
python -m pytest --version

Write-Host

# PASSO 2: Executar testes pytest
Write-Host "2. EXECUTANDO TESTES PYTEST:" -ForegroundColor Yellow
$testFile = "D:\REPOSITORIOS\sra-pli-5\tests\test_pytest_simples.py"
if (Test-Path $testFile) {
    Write-Host "   ✅ Arquivo de teste encontrado" -ForegroundColor Green
    Write-Host "   Executando pytest..." -ForegroundColor White
    python -m pytest $testFile -v
} else {
    Write-Host "   ❌ Arquivo de teste não encontrado" -ForegroundColor Red
}

Write-Host

# PASSO 3: Executar todos os testes
Write-Host "3. EXECUTANDO TODOS OS TESTES:" -ForegroundColor Yellow
Write-Host "   Executando pytest em todos os testes..." -ForegroundColor White
python -m pytest tests/ -v

Write-Host

# PASSO 4: Instruções para Kiro
Write-Host "4. INSTRUÇÕES PARA KIRO:" -ForegroundColor Yellow
Write-Host
Write-Host "   A. ABRA qualquer arquivo de teste:" -ForegroundColor White
Write-Host "      tests/test_pytest_simples.py" -ForegroundColor Cyan
Write-Host "      tests/test_ativacao_python.py" -ForegroundColor Cyan
Write-Host
Write-Host "   B. AGUARDE a descoberta automática de testes" -ForegroundColor White
Write-Host "      (pode levar alguns segundos)" -ForegroundColor Gray
Write-Host
Write-Host "   C. VERIFIQUE se aparece:" -ForegroundColor White
Write-Host "      1. Ícone de TUBO DE ENSAIO na barra lateral" -ForegroundColor Green
Write-Host "      2. Número de testes descobertos no ícone" -ForegroundColor Green
Write-Host
Write-Host "   D. SE NÃO APARECER:" -ForegroundColor White
Write-Host "      Ctrl+Shift+P → 'Python: Discover Tests'" -ForegroundColor Cyan
Write-Host "      Ctrl+Shift+P → 'Test: Focus on Test Explorer'" -ForegroundColor Cyan
Write-Host
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CONFIGURAÇÃO ATUAL:" -ForegroundColor Yellow
Write-Host
Get-Content ".vscode/settings.json" | Select-String "python.testing" | ForEach-Object {
    Write-Host "   $_" -ForegroundColor Gray
}
Write-Host
Write-Host "==========================================" -ForegroundColor Cyan