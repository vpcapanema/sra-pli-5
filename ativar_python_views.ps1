# Script para ativar views Python no Kiro
Write-Host "=== ATIVANDO VIEWS PYTHON NO KIRO ===" -ForegroundColor Cyan
Write-Host

# 1. Verificar extensão Python
$pythonExtPath = "C:\Users\Vinicius adm\.kiro\extensions\ms-python.python-*"
if (Test-Path $pythonExtPath) {
    Write-Host "✅ Extensão Python instalada" -ForegroundColor Green
    $extDir = Get-ChildItem $pythonExtPath | Select-Object -First 1
    Write-Host "   Versão: $($extDir.Name)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Extensão Python NÃO encontrada" -ForegroundColor Red
    Write-Host "   Instale via: Ctrl+Shift+X → Busque 'Python' → Instale" -ForegroundColor Yellow
}

Write-Host

# 2. Verificar ambiente virtual
$venvPath = "D:\REPOSITORIOS\sra-pli-5\.venv\Scripts\python.exe"
if (Test-Path $venvPath) {
    Write-Host "✅ Ambiente virtual encontrado" -ForegroundColor Green
    Write-Host "   Caminho: $venvPath" -ForegroundColor Yellow
} else {
    Write-Host "❌ Ambiente virtual NÃO encontrado" -ForegroundColor Red
}

Write-Host

# 3. Instruções para ativar views Python no Kiro
Write-Host "=== INSTRUÇÕES PARA ATIVAR VIEWS ===" -ForegroundColor Cyan
Write-Host
Write-Host "1. ABRA um arquivo Python (.py) no editor" -ForegroundColor Yellow
Write-Host "   Exemplo: exemplo_output.py" -ForegroundColor White
Write-Host
Write-Host "2. SELECIONE o interpretador Python:" -ForegroundColor Yellow
Write-Host "   Ctrl+Shift+P → 'Python: Select Interpreter'" -ForegroundColor White
Write-Host "   Escolha: $venvPath" -ForegroundColor White
Write-Host
Write-Host "3. ABRA as views Python:" -ForegroundColor Yellow
Write-Host "   Ctrl+Shift+P → 'View: Open View'" -ForegroundColor White
Write-Host "   Digite 'Python' e selecione:" -ForegroundColor White
Write-Host "   - 'Python: Test Explorer'" -ForegroundColor White
Write-Host "   - 'Python: Outline'" -ForegroundColor White
Write-Host
Write-Host "4. Se ainda não aparecer, RECARREGUE:" -ForegroundColor Yellow
Write-Host "   Ctrl+Shift+P → 'Developer: Reload Window'" -ForegroundColor White
Write-Host
Write-Host "=== CONFIGURAÇÃO ATUAL ===" -ForegroundColor Cyan
Write-Host
Write-Host "Arquivo .vscode/settings.json configurado com:" -ForegroundColor Yellow
Get-Content "D:\REPOSITORIOS\sra-pli-5\.vscode\settings.json" | ForEach-Object {
    Write-Host "   $_" -ForegroundColor Gray
}

Write-Host
Write-Host "=== SOLUÇÃO ALTERNATIVA ===" -ForegroundColor Cyan
Write-Host "Se as views ainda não aparecerem, pode ser que:" -ForegroundColor Yellow
Write-Host "1. O Kiro tenha interface personalizada" -ForegroundColor White
Write-Host "2. As views estejam em menus dropdown" -ForegroundColor White
Write-Host "3. Use atalhos diretos:" -ForegroundColor White
Write-Host "   - Test Explorer: Ctrl+Shift+P → 'Test: Focus on Test Explorer'" -ForegroundColor White
Write-Host "   - Outline: Ctrl+Shift+P → 'View: Open View' → 'Outline'" -ForegroundColor White