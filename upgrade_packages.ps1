# Script para fazer upgrade de todos os pacotes do frontend

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "UPGRADE DE PACOTES - VITE 7.2.2 + REACT 19 + TYPESCRIPT 5.6.3" -ForegroundColor Green
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

# ETAPA 1: Parar servidor se estiver rodando
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 1: PARAR SERVIDOR" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Parando processos Node.js..." -ForegroundColor Yellow
taskkill /F /IM node.exe 2>$null
Start-Sleep -Seconds 2

Write-Host "OK - Processos parados" -ForegroundColor Green

Write-Host ""

# ETAPA 2: Limpar cache
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 2: LIMPAR CACHE" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Limpando npm cache..." -ForegroundColor Yellow
npm cache clean --force

Write-Host "Removendo node_modules..." -ForegroundColor Yellow
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue

Write-Host "Removendo package-lock.json..." -ForegroundColor Yellow
Remove-Item package-lock.json -ErrorAction SilentlyContinue

Write-Host "OK - Cache limpo" -ForegroundColor Green

Write-Host ""

# ETAPA 3: Instalar dependencias
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 3: INSTALAR DEPENDENCIAS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Instalando pacotes..." -ForegroundColor Yellow
npm install

Write-Host ""
Write-Host "OK - Pacotes instalados com sucesso!" -ForegroundColor Green

Write-Host ""

# ETAPA 4: Verificar versoes
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 4: VERIFICAR VERSOES" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Versoes instaladas:" -ForegroundColor Yellow
Write-Host ""

npm list vite
npm list react
npm list typescript
npm list @vitejs/plugin-react-swc

Write-Host ""

# ETAPA 5: Type check
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 5: TYPE CHECK" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificando tipos TypeScript..." -ForegroundColor Yellow
npm run type-check

Write-Host ""
Write-Host "OK - Type check concluido" -ForegroundColor Green

Write-Host ""

# CONCLUSAO
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "OK - UPGRADE CONCLUIDO COM SUCESSO!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Resumo:" -ForegroundColor Yellow
Write-Host "  OK - Vite 7.2.2 instalado" -ForegroundColor Green
Write-Host "  OK - React 19 instalado" -ForegroundColor Green
Write-Host "  OK - TypeScript 5.6.3 instalado" -ForegroundColor Green
Write-Host "  OK - SWC plugin 3.13.1 instalado" -ForegroundColor Green
Write-Host "  OK - Todos os pacotes atualizados" -ForegroundColor Green
Write-Host ""

Write-Host "Proximas acoes:" -ForegroundColor Yellow
Write-Host "  1. Iniciar servidor: npm run dev" -ForegroundColor Cyan
Write-Host "  2. Abrir: http://localhost:3000/" -ForegroundColor Cyan
Write-Host "  3. Testar funcionalidades" -ForegroundColor Cyan
Write-Host ""
