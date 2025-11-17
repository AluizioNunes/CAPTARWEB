# Script para executar frontend React localmente
# Sem Docker, direto no seu computador

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "CAPTAR v2.0 - EXECUTAR FRONTEND REACT" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Configuracao:" -ForegroundColor Yellow
Write-Host "  Frontend: React com Vite" -ForegroundColor Cyan
Write-Host "  Porta: 5173 (padrao do Vite)" -ForegroundColor Cyan
Write-Host "  Modo: Desenvolvimento" -ForegroundColor Cyan
Write-Host ""

# ETAPA 1: VERIFICAR NODE
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 1: VERIFICAR NODE.JS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificando Node.js..." -ForegroundColor Yellow

try {
    $nodeVersion = node --version
    Write-Host "OK - Node.js encontrado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERRO - Node.js nao encontrado!" -ForegroundColor Red
    Write-Host "Instale Node.js de: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# ETAPA 2: VERIFICAR NPM
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 2: VERIFICAR NPM" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificando npm..." -ForegroundColor Yellow

try {
    $npmVersion = npm --version
    Write-Host "OK - npm encontrado: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "ERRO - npm nao encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ETAPA 3: NAVEGAR PARA FRONTEND
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 3: NAVEGAR PARA DIRETORIO FRONTEND" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$frontendDir = ".\Frontend"

if (Test-Path $frontendDir) {
    Write-Host "OK - Diretorio Frontend encontrado" -ForegroundColor Green
    cd $frontendDir
    Write-Host "Diretorio atual: $(Get-Location)" -ForegroundColor Cyan
} else {
    Write-Host "ERRO - Diretorio Frontend nao encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ETAPA 4: VERIFICAR DEPENDENCIAS
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 4: VERIFICAR DEPENDENCIAS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "node_modules") {
    Write-Host "OK - node_modules encontrado" -ForegroundColor Green
    $moduleCount = (Get-ChildItem node_modules -Directory | Measure-Object).Count
    Write-Host "Pacotes instalados: $moduleCount" -ForegroundColor Cyan
} else {
    Write-Host "AVISO - node_modules nao encontrado" -ForegroundColor Yellow
    Write-Host "Instalando dependencias..." -ForegroundColor Yellow
    npm install
    Write-Host "OK - Dependencias instaladas" -ForegroundColor Green
}

Write-Host ""

# ETAPA 5: VERIFICAR VITE
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 5: VERIFICAR VITE" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificando Vite..." -ForegroundColor Yellow

if (Test-Path "node_modules\.bin\vite.cmd") {
    Write-Host "OK - Vite encontrado" -ForegroundColor Green
} else {
    Write-Host "AVISO - Vite nao encontrado em node_modules" -ForegroundColor Yellow
    Write-Host "Instalando Vite..." -ForegroundColor Yellow
    npm install
}

Write-Host ""

# ETAPA 6: INICIAR FRONTEND
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 6: INICIAR FRONTEND" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Iniciando servidor de desenvolvimento..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Aguarde alguns segundos..." -ForegroundColor Yellow
Write-Host ""

npm run dev

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Frontend finalizado" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
