# Script para iniciar o Frontend CAPTAR v2.0
# Uso: .\iniciar_frontend.ps1

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         CAPTAR v2.0 - FRONTEND (Vite 7.2.2)                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Definir caminho
$frontendPath = "c:\www\Streamlit\Captar\CAPTAR\Frontend"

# Verificar se o diretorio existe
if (-not (Test-Path $frontendPath)) {
    Write-Host "❌ Erro: Diretorio nao encontrado: $frontendPath" -ForegroundColor Red
    exit 1
}

# Navegar para o diretorio
Set-Location $frontendPath
Write-Host "✅ Diretorio: $frontendPath" -ForegroundColor Green
Write-Host ""

# Verificar se node_modules existe
if (-not (Test-Path "$frontendPath\node_modules")) {
    Write-Host "⚠️  node_modules nao encontrado. Instalando dependencias..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao instalar dependencias" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencias instaladas" -ForegroundColor Green
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    INICIANDO FRONTEND                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "📍 Informacoes:" -ForegroundColor Yellow
Write-Host "   URL Local:    http://localhost:5175/" -ForegroundColor White
Write-Host "   URL Network:  http://$(hostname):5175/" -ForegroundColor White
Write-Host "   API:          http://localhost:5000 (FastAPI)" -ForegroundColor White
Write-Host ""

Write-Host "🔧 Opcoes de Login:" -ForegroundColor Yellow
Write-Host "   1. Acesso Direto (Desenvolvedor) - Sem precisar de API" -ForegroundColor White
Write-Host "   2. Login Normal - Requer FastAPI rodando" -ForegroundColor White
Write-Host ""

Write-Host "⏳ Iniciando servidor..." -ForegroundColor Cyan
Write-Host ""

# Iniciar o servidor
npm run dev

# Se chegou aqui, o servidor foi encerrado
Write-Host ""
Write-Host "✅ Servidor encerrado" -ForegroundColor Green
