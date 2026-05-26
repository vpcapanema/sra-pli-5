# SCRIPT PARA EXECUTAR SOLUÇÃO CORRETA - ÍCONE PYTHON NO KIRO
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SOLUÇÃO CORRETA - ÍCONE PYTHON NO KIRO" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host

# PASSO 1: Verificar ambiente
Write-Host "1. VERIFICANDO AMBIENTE:" -ForegroundColor Yellow
. 'D:\REPOSITORIOS\sra-pli-5\.venv\Scripts\Activate.ps1'
$pythonExe = "D:\REPOSITORIOS\sra-pli-5\.venv\Scripts\python.exe"

if (Test-Path $pythonExe) {
    Write-Host "   ✅ Python encontrado: $pythonExe" -ForegroundColor Green
    & $pythonExe --version
} else {
    Write-Host "   ❌ Python não encontrado" -ForegroundColor Red
    exit 1
}

Write-Host

# PASSO 2: Executar testes
Write-Host "2. EXECUTANDO TESTES PARA ATIVAR TEST EXPLORER:" -ForegroundColor Yellow
$testFile = "D:\REPOSITORIOS\sra-pli-5\tests\test_ativacao_python.py"
if (Test-Path $testFile) {
    Write-Host "   ✅ Arquivo de teste encontrado" -ForegroundColor Green
    Write-Host "   Executando testes..." -ForegroundColor White
    & $pythonExe $testFile
} else {
    Write-Host "   ❌ Arquivo de teste não encontrado" -ForegroundColor Red
}

Write-Host

# PASSO 3: Instruções finais
Write-Host "3. INSTRUÇÕES PARA VER O ÍCONE NO KIRO:" -ForegroundColor Yellow
Write-Host
Write-Host "   A. ABRA o arquivo no Kiro:" -ForegroundColor White
Write-Host "      tests/test_ativacao_python.py" -ForegroundColor Cyan
Write-Host
Write-Host "   B. EXECUTE no terminal do Kiro:" -ForegroundColor White
Write-Host "      .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "      python tests/test_ativacao_python.py" -ForegroundColor Cyan
Write-Host
Write-Host "   C. SELECIONE interpretador (Ctrl+Shift+P):" -ForegroundColor White
Write-Host "      'Python: Select Interpreter'" -ForegroundColor Cyan
Write-Host "      → $pythonExe" -ForegroundColor Cyan
Write-Host
Write-Host "   D. DESCOBRIR TESTES (Ctrl+Shift+P):" -ForegroundColor White
Write-Host "      'Python: Discover Tests'" -ForegroundColor Cyan
Write-Host
Write-Host "   E. ABRIR TEST EXPLORER (Ctrl+Shift+P):" -ForegroundColor White
Write-Host "      'Test: Focus on Test Explorer'" -ForegroundColor Cyan
Write-Host
Write-Host "   F. RESULTADO ESPERADO:" -ForegroundColor White
Write-Host "      Ícone de TUBO DE ENSAIO na barra lateral" -ForegroundColor Green
Write-Host "      (Este é o 'ícone Python' no VS Code/Kiro)" -ForegroundColor Green
Write-Host
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "EXPLICAÇÃO TÉCNICA:" -ForegroundColor Yellow
Write-Host
Write-Host "A extensão Python NÃO tem ícone próprio na activity bar." -ForegroundColor White
Write-Host "Ela integra com:" -ForegroundColor White
Write-Host "1. Test Explorer (ícone de tubo de ensaio)" -ForegroundColor White
Write-Host "2. Outline view (estrutura do código)" -ForegroundColor White
Write-Host "3. Debug view (ícone de inseto)" -ForegroundColor White
Write-Host
Write-Host "O 'ícone Python' que você procura é o TEST EXPLORER" -ForegroundColor Green
Write-Host "que aparece quando há testes Python descobertos." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan