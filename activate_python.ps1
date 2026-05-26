# Script de ativação alternativa para ambiente virtual Python
# Para uso quando a extensão Python do VS Code não detecta o ambiente

$venvPath = "D:\REPOSITORIOS\sra-pli-5\.venv"
$pythonExe = "$venvPath\Scripts\python.exe"

if (Test-Path $pythonExe) {
    Write-Host "Python encontrado em: $pythonExe" -ForegroundColor Green
    Write-Host "Versão do Python:"
    & $pythonExe --version
    Write-Host "`nPara usar este ambiente no VS Code:"
    Write-Host "1. Pressione Ctrl+Shift+P"
    Write-Host "2. Digite 'Python: Select Interpreter'"
    Write-Host "3. Selecione: $pythonExe"
} else {
    Write-Host "ERRO: Python não encontrado em $pythonExe" -ForegroundColor Red
}