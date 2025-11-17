# Script para iniciar o FastAPI CAPTAR v2.0
# Uso: .\iniciar_fastapi.ps1

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         CAPTAR v2.0 - BACKEND (FastAPI)                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Definir caminho
$backendPath = "c:\www\Streamlit\Captar\CAPTAR\Backend\FastAPI"

# Verificar se o diretorio existe
if (-not (Test-Path $backendPath)) {
    Write-Host "❌ Erro: Diretorio nao encontrado: $backendPath" -ForegroundColor Red
    exit 1
}

# Navegar para o diretorio
Set-Location $backendPath
Write-Host "✅ Diretorio: $backendPath" -ForegroundColor Green
Write-Host ""

# Verificar se Python esta instalado
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro: Python nao encontrado" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python: $pythonCheck" -ForegroundColor Green
Write-Host ""

# Verificar se main.py existe
if (-not (Test-Path "$backendPath\main.py")) {
    Write-Host "❌ Erro: main.py nao encontrado em $backendPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ main.py encontrado" -ForegroundColor Green
Write-Host ""

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    INICIANDO FASTAPI                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "📍 Informacoes:" -ForegroundColor Yellow
Write-Host "   URL Local:    http://localhost:5000" -ForegroundColor White
Write-Host "   Docs:         http://localhost:5000/docs" -ForegroundColor White
Write-Host "   ReDoc:        http://localhost:5000/redoc" -ForegroundColor White
Write-Host "   Frontend:     http://localhost:5175" -ForegroundColor White
Write-Host ""

Write-Host "⏳ Iniciando servidor..." -ForegroundColor Cyan
Write-Host ""

# Iniciar o servidor
python main.py

# Se chegou aqui, o servidor foi encerrado
Write-Host ""
Write-Host "✅ Servidor encerrado" -ForegroundColor Green
