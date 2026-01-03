# Script de teste para os frontends CAPTAR e Evolution

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Teste de Acesso aos Frontends" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor [System.Net.SecurityProtocolType]::Tls12
} catch {
}
try {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
} catch {
}
try {
    Add-Type -AssemblyName System.Net.Http
} catch {
}

$FRONTEND_PORT = $env:FRONTEND_HOST_PORT
if (-not $FRONTEND_PORT) { $FRONTEND_PORT = "5501" }

$EV_API_PORT = $env:EV_API_HOST_PORT
if (-not $EV_API_PORT) { $EV_API_PORT = "4400" }

$EV_FRONTEND_PORT = $env:EV_FRONTEND_HOST_PORT
if (-not $EV_FRONTEND_PORT) { $EV_FRONTEND_PORT = "4401" }

$NGINX_PORT = $env:NGINX_HOST_PORT
if (-not $NGINX_PORT) { $NGINX_PORT = $env:NGINX_HTTP_PORT }
if (-not $NGINX_PORT) { $NGINX_PORT = "80" }

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
    $handler = $null
    $client = $null
    $resp = $null
    try {
        $handler = New-Object System.Net.Http.HttpClientHandler
        try {
            $handler.AllowAutoRedirect = $false
        } catch {}
        try {
            $handler.ServerCertificateCustomValidationCallback = { param($sender, $cert, $chain, $errors) return $true }
        } catch {}

        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.Timeout = [TimeSpan]::FromSeconds(8)

        $resp = $client.GetAsync($Url).GetAwaiter().GetResult()
        $code = [int]$resp.StatusCode
        $finalUrl = $null
        try { $finalUrl = $resp.RequestMessage.RequestUri.AbsoluteUri } catch {}

        if ($finalUrl -and $finalUrl -ne $Url) { Write-Host "   Final: $finalUrl" -ForegroundColor DarkGray }
        if ($code -ge 300 -and $code -lt 400) {
            $loc = $null
            try { $loc = $resp.Headers.Location.AbsoluteUri } catch {}
            if ($loc) { Write-Host "   Redirect: $loc" -ForegroundColor DarkGray }
        }

        if ($code -ge 200 -and $code -lt 400) {
            Write-Host "   OK: HTTP $code" -ForegroundColor Green
            return $true
        }
        Write-Host "   ERRO: HTTP $code" -ForegroundColor Red
        return $false
    } catch {
        Write-Host "   ERRO: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    } finally {
        try { if ($resp) { $resp.Dispose() } } catch {}
        try { if ($client) { $client.Dispose() } } catch {}
        try { if ($handler) { $handler.Dispose() } } catch {}
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

Test-Url -Url "http://localhost:$NGINX_PORT/api/health" -Name "FastAPI /api/health via Nginx"

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

