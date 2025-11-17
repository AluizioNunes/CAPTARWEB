# Script para limpar cache npm e espaço em disco

Write-Host "🧹 Limpando cache npm..." -ForegroundColor Green

# Limpar cache npm
npm cache clean --force

# Remover node_modules
if (Test-Path "Frontend/node_modules") {
    Write-Host "Removendo node_modules..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "Frontend/node_modules"
}

# Limpar package-lock.json
if (Test-Path "Frontend/package-lock.json") {
    Remove-Item "Frontend/package-lock.json"
}

# Limpar Docker
Write-Host "Limpando Docker..." -ForegroundColor Yellow
docker system prune -f
docker volume prune -f

Write-Host "✅ Limpeza concluída!" -ForegroundColor Green
Write-Host "Agora execute: npm install" -ForegroundColor Cyan
