# Script para instalar dependencias faltantes do frontend

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "INSTALAR DEPENDENCIAS DO FRONTEND" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Navegar para frontend
$frontendDir = ".\Frontend"

if (Test-Path $frontendDir) {
    cd $frontendDir
    Write-Host "Diretorio: $(Get-Location)" -ForegroundColor Cyan
} else {
    Write-Host "ERRO - Diretorio Frontend nao encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Instalando dependencias faltantes..." -ForegroundColor Yellow
Write-Host ""

# Instalar react-router-dom
Write-Host "Instalando react-router-dom..." -ForegroundColor Yellow
npm install react-router-dom

Write-Host ""
Write-Host "OK - Dependencias instaladas com sucesso!" -ForegroundColor Green
Write-Host ""

Write-Host "Proximas acoes:" -ForegroundColor Yellow
Write-Host "  1. Volte ao terminal do frontend" -ForegroundColor Cyan
Write-Host "  2. Pressione: r (para reiniciar)" -ForegroundColor Cyan
Write-Host "  3. Ou execute: npm run dev" -ForegroundColor Cyan
Write-Host ""
