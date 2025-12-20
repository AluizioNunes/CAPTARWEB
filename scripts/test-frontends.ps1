# Script de teste para os frontends CAPTAR e Evolution

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Teste de Acesso aos Frontends" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$FRONTEND_PORT = $env:FRONTEND_HOST_PORT
if (-not $FRONTEND_PORT) { $FRONTEND_PORT = "5501" }

$EV_API_PORT = $env:EV_API_HOST_PORT
if (-not $EV_API_PORT) { $EV_API_PORT = "4400" }

$EV_FRONTEND_PORT = $env:EV_FRONTEND_HOST_PORT
if (-not $EV_FRONTEND_PORT) { $EV_FRONTEND_PORT = "4401" }

$NGINX_PORT = "5500"

Write-Host "1. Verificando status dos containers..." -ForegroundColor Yellow
Write-Host ""

try {
    $containers = docker ps --format "{{.Names}}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ERRO: Docker nao esta acessivel ou nao esta rodando" -ForegroundColor Red
        exit 1
    }

    $captarFrontend = $containers | Select-String -Pattern "captar-frontend"
    $evolutionFrontend = $containers | Select-String -Pattern "evolution_frontend"
    $evolutionApi = $containers | Select-String -Pattern "^evolution_api$"
    $nginx = $containers | Select-String -Pattern "captar-nginx"

    Write-Host "   CAPTAR Frontend: " -NoNewline
    if ($captarFrontend) { Write-Host "RODANDO" -ForegroundColor Green } else { Write-Host "NAO ENCONTRADO" -ForegroundColor Red }

    Write-Host "   Evolution Frontend: " -NoNewline
    if ($evolutionFrontend) { Write-Host "RODANDO" -ForegroundColor Green } else { Write-Host "NAO ENCONTRADO" -ForegroundColor Red }

    Write-Host "   Evolution API: " -NoNewline
    if ($evolutionApi) { Write-Host "RODANDO" -ForegroundColor Green } else { Write-Host "NAO ENCONTRADO" -ForegroundColor Red }

    Write-Host "   Nginx: " -NoNewline
    if ($nginx) { Write-Host "RODANDO" -ForegroundColor Green } else { Write-Host "NAO ENCONTRADO" -ForegroundColor Red }
} catch {
    Write-Host "   ERRO ao verificar containers: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "2. Testando acesso HTTP..." -ForegroundColor Yellow
Write-Host ""

function Test-Url {
    param (
        [string]$Url,
        [string]$Name
    )

    Write-Host "   ${Name}: ${Url}" -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
        Write-Host "   OK: HTTP $($response.StatusCode)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "   ERRO: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

$captarDirect = Test-Url -Url "http://localhost:$FRONTEND_PORT" -Name "CAPTAR Frontend (direto)"
Write-Host ""
$captarNginx = Test-Url -Url "http://localhost:$NGINX_PORT" -Name "CAPTAR via Nginx"
Write-Host ""
$evolutionDirect = Test-Url -Url "http://localhost:$EV_FRONTEND_PORT" -Name "Evolution Frontend"
Write-Host ""
$evolutionApiDirect = Test-Url -Url "http://localhost:$EV_API_PORT/" -Name "Evolution API"
Write-Host ""
$evolutionApiViaEvo = Test-Url -Url "http://localhost:$EV_FRONTEND_PORT/evo/" -Name "Evolution API (via /evo/)"

Write-Host ""
Write-Host "3. Verificando endpoints..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   FastAPI /api/health via Nginx: http://localhost:$NGINX_PORT/api/health" -ForegroundColor Gray
try {
    $fastApiHealth = Invoke-WebRequest -Uri "http://localhost:$NGINX_PORT/api/health" -Method Get -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
    Write-Host "   OK: HTTP $($fastApiHealth.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ERRO: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Resumo dos Testes" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$results = @{
    "CAPTAR Frontend (direto)" = $captarDirect
    "CAPTAR via Nginx" = $captarNginx
    "Evolution Frontend" = $evolutionDirect
    "Evolution API" = $evolutionApiDirect
    "Evolution API (via /evo/)" = $evolutionApiViaEvo
}

$allPassed = $true
foreach ($test in $results.Keys) {
    Write-Host "   ${test}: " -NoNewline
    if ($results[$test]) {
        Write-Host "PASSOU" -ForegroundColor Green
    } else {
        Write-Host "FALHOU" -ForegroundColor Red
        $allPassed = $false
    }
}

Write-Host ""
if ($allPassed) {
    exit 0
} else {
    exit 1
}

