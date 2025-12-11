# Script de teste para os frontends CAPTAR e Evolution
# Pode ser executado localmente ou no servidor onde os containers estão rodando

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Teste de Acesso aos Frontends" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configurações das portas (padrões do docker-compose.yml)
$FRONTEND_PORT = $env:FRONTEND_HOST_PORT
if (-not $FRONTEND_PORT) { $FRONTEND_PORT = "5501" }

$EV_FRONTEND_PORT = $env:EV_FRONTEND_HOST_PORT
if (-not $EV_FRONTEND_PORT) { $EV_FRONTEND_PORT = "4380" }

$NGINX_PORT = "5500"

# Verificar se os containers estão rodando
Write-Host "1. Verificando status dos containers..." -ForegroundColor Yellow
Write-Host ""

try {
    $containers = docker ps --format "{{.Names}}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ERRO: Docker não está acessível ou não está rodando" -ForegroundColor Red
        Write-Host "   Verifique se o Docker está instalado e rodando" -ForegroundColor Red
        exit 1
    }
    
    $captarFrontend = $containers | Select-String -Pattern "captar-frontend"
    $evolutionFrontend = $containers | Select-String -Pattern "evolution_frontend"
    $nginx = $containers | Select-String -Pattern "captar-nginx"
    
    Write-Host "   CAPTAR Frontend: " -NoNewline
    if ($captarFrontend) {
        Write-Host "✓ Rodando" -ForegroundColor Green
    } else {
        Write-Host "✗ Não encontrado" -ForegroundColor Red
    }
    
    Write-Host "   Evolution Frontend: " -NoNewline
    if ($evolutionFrontend) {
        Write-Host "✓ Rodando" -ForegroundColor Green
    } else {
        Write-Host "✗ Não encontrado" -ForegroundColor Red
    }
    
    Write-Host "   Nginx: " -NoNewline
    if ($nginx) {
        Write-Host "✓ Rodando" -ForegroundColor Green
    } else {
        Write-Host "✗ Não encontrado" -ForegroundColor Red
    }
    
} catch {
    Write-Host "   ERRO ao verificar containers: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "2. Testando acesso HTTP aos frontends..." -ForegroundColor Yellow
Write-Host ""

# Função para testar URL
function Test-Url {
    param (
        [string]$Url,
        [string]$Name
    )
    
    Write-Host "   Testando $Name..." -NoNewline
    Write-Host " ($Url)" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "   ✓ Status: $($response.StatusCode) - OK" -ForegroundColor Green
        if ($response.Content.Length -gt 0) {
            Write-Host "   ✓ Conteúdo recebido: $($response.Content.Length) bytes" -ForegroundColor Green
        }
        return $true
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode) {
            Write-Host "   ✗ Status: $statusCode" -ForegroundColor Red
        } else {
            Write-Host "   ✗ Erro: $($_.Exception.Message)" -ForegroundColor Red
        }
        return $false
    }
}

# Testar CAPTAR Frontend direto
Write-Host "   --- CAPTAR Frontend (Porta $FRONTEND_PORT) ---" -ForegroundColor Cyan
$captarDirect = Test-Url -Url "http://localhost:$FRONTEND_PORT" -Name "CAPTAR Frontend Direto"

Write-Host ""

# Testar CAPTAR via Nginx
Write-Host "   --- CAPTAR via Nginx (Porta $NGINX_PORT) ---" -ForegroundColor Cyan
$captarNginx = Test-Url -Url "http://localhost:$NGINX_PORT" -Name "CAPTAR via Nginx"

Write-Host ""

# Testar Evolution Frontend
Write-Host "   --- Evolution Frontend (Porta $EV_FRONTEND_PORT) ---" -ForegroundColor Cyan
$evolutionDirect = Test-Url -Url "http://localhost:$EV_FRONTEND_PORT" -Name "Evolution Frontend"

Write-Host ""
Write-Host "3. Verificando endpoints de API..." -ForegroundColor Yellow
Write-Host ""

# Testar API do FastAPI
Write-Host "   --- FastAPI Health Check ---" -ForegroundColor Cyan
try {
    $fastApiHealth = Invoke-WebRequest -Uri "http://localhost:$NGINX_PORT/api/health" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ FastAPI Health: $($fastApiHealth.StatusCode) - OK" -ForegroundColor Green
    $fastApiContent = $fastApiHealth.Content | ConvertFrom-Json
    Write-Host "   ✓ Resposta: $($fastApiContent | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ FastAPI não está respondendo: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Testar Evolution API
Write-Host "   --- Evolution API ---" -ForegroundColor Cyan
try {
    $evolutionApi = Invoke-WebRequest -Uri "http://localhost:$EV_FRONTEND_PORT/api/health" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ Evolution API: $($evolutionApi.StatusCode) - OK" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Evolution API não está respondendo: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "4. Verificando logs dos containers..." -ForegroundColor Yellow
Write-Host ""

# Verificar logs do Evolution Frontend (onde estava o erro)
Write-Host "   --- Últimas linhas do Evolution Frontend ---" -ForegroundColor Cyan
try {
    $evolutionLogs = docker logs evolution_frontend --tail 20 2>&1
    if ($evolutionLogs -match "error|emerg|invalid") {
        Write-Host "   ⚠ AVISOS/ERROS encontrados:" -ForegroundColor Yellow
        $evolutionLogs | Select-String -Pattern "error|emerg|invalid" | ForEach-Object {
            Write-Host "   $_" -ForegroundColor Red
        }
    } else {
        Write-Host "   ✓ Sem erros críticos nos últimos logs" -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ Não foi possível acessar logs: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Resumo dos Testes" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$results = @{
    "CAPTAR Frontend (Direto)" = $captarDirect
    "CAPTAR via Nginx" = $captarNginx
    "Evolution Frontend" = $evolutionDirect
}

$allPassed = $true
foreach ($test in $results.Keys) {
    $status = if ($results[$test]) { "✓ PASSOU" -ForegroundColor Green } else { "✗ FALHOU" -ForegroundColor Red }
    Write-Host "   $test : " -NoNewline
    Write-Host $status
    if (-not $results[$test]) { $allPassed = $false }
}

Write-Host ""

if ($allPassed) {
    Write-Host "✓ Todos os testes passaram!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Alguns testes falharam. Verifique os logs acima." -ForegroundColor Red
    exit 1
}

