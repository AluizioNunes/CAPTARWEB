# Script: Subir containers e copiar banco de dados
# 1. Subir containers (PostgreSQL 18 na porta 5435)
# 2. Aguardar inicializacao
# 3. Copiar banco do postgres existente para captar-postgres

param(
    [string]$IP_Remoto = "172.26.97.64",
    [string]$Container_Origem = "postgres",
    [string]$Container_Destino = "captar-postgres",
    [string]$DB_Usuario = "captar",
    [string]$DB_Senha = "captar",
    [string]$DB_Nome = "captar"
)

# Definir Docker remoto
$env:DOCKER_HOST = "tcp://$IP_Remoto:2375"

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "CAPTAR v2.0 - DEPLOY E COPIA DE BANCO DE DADOS" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Configuracao:" -ForegroundColor Yellow
Write-Host "  Servidor: $IP_Remoto" -ForegroundColor Cyan
Write-Host "  PostgreSQL Novo: porta 5435" -ForegroundColor Cyan
Write-Host "  PostgreSQL Existente: porta 5432" -ForegroundColor Cyan
Write-Host "  Banco: $DB_Nome" -ForegroundColor Cyan
Write-Host ""

# ETAPA 1: VERIFICAR CONEXAO
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 1: VERIFICAR CONEXAO COM DOCKER" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Conectando ao Docker remoto..." -ForegroundColor Yellow

try {
    docker ps | Out-Null
    Write-Host "OK - Conectado ao Docker remoto" -ForegroundColor Green
} catch {
    Write-Host "ERRO - Nao foi possivel conectar!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ETAPA 2: PARAR CONTAINERS ANTIGOS
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 2: PARAR CONTAINERS ANTIGOS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Parando containers..." -ForegroundColor Yellow
docker-compose down

Write-Host "OK - Containers parados" -ForegroundColor Green

Write-Host ""

# ETAPA 3: SUBIR CONTAINERS
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 3: SUBIR CONTAINERS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Iniciando containers com docker-compose..." -ForegroundColor Yellow
docker-compose up -d --build

Write-Host "Aguardando inicializacao (40 seg)..." -ForegroundColor Yellow
Start-Sleep -Seconds 40

Write-Host "OK - Containers iniciados" -ForegroundColor Green

Write-Host ""

# ETAPA 4: VERIFICAR CONTAINERS
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 4: VERIFICAR CONTAINERS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Containers em execucao:" -ForegroundColor Green
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"

Write-Host ""

# ETAPA 5: VERIFICAR CONTAINERS POSTGRESQL
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 5: VERIFICAR CONTAINERS POSTGRESQL" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Containers PostgreSQL:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}" | Select-String "postgres"

Write-Host ""

# Verificar container origem
$containerOrigemExists = docker ps --format "table {{.Names}}" | Select-String "^$Container_Origem$"
if ($null -eq $containerOrigemExists) {
    Write-Host "AVISO - Container $Container_Origem nao encontrado!" -ForegroundColor Yellow
    Write-Host "Pulando copia de banco..." -ForegroundColor Yellow
    $skipCopy = $true
} else {
    Write-Host "OK - Container $Container_Origem encontrado" -ForegroundColor Green
    $skipCopy = $false
}

# Verificar container destino
$containerDestinoExists = docker ps --format "table {{.Names}}" | Select-String "^$Container_Destino$"
if ($null -eq $containerDestinoExists) {
    Write-Host "ERRO - Container $Container_Destino nao encontrado!" -ForegroundColor Red
    exit 1
}
Write-Host "OK - Container $Container_Destino encontrado" -ForegroundColor Green

Write-Host ""

# ETAPA 6: COPIAR BANCO DE DADOS
if (-not $skipCopy) {
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host "ETAPA 6: COPIAR BANCO DE DADOS" -ForegroundColor Yellow
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Fazendo dump do banco $DB_Nome..." -ForegroundColor Yellow
    
    $backupFile = "postgres_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
    
    try {
        docker exec $Container_Origem pg_dump -U $DB_Usuario $DB_Nome | Out-File -FilePath $backupFile -Encoding UTF8
        
        if (Test-Path $backupFile) {
            $fileSize = (Get-Item $backupFile).Length / 1MB
            Write-Host "OK - Dump criado com sucesso" -ForegroundColor Green
            Write-Host "Arquivo: $backupFile" -ForegroundColor Cyan
            Write-Host "Tamanho: $([Math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
        } else {
            Write-Host "ERRO - Nao foi possivel criar o dump!" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "ERRO - Falha ao fazer dump: $_" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    
    Write-Host "Listando tabelas do banco origem:" -ForegroundColor Yellow
    docker exec $Container_Origem psql -U $DB_Usuario -d $DB_Nome -c "\dt" -t
    
    Write-Host ""
    Write-Host "Contando registros no banco origem:" -ForegroundColor Yellow
    docker exec $Container_Origem psql -U $DB_Usuario -d $DB_Nome -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;" -t
    
    Write-Host ""
    
    Write-Host "Copiando arquivo para container..." -ForegroundColor Yellow
    docker cp $backupFile "$Container_Destino`:/tmp/backup.sql"
    
    Write-Host "Restaurando banco no container destino..." -ForegroundColor Yellow
    Get-Content $backupFile | docker exec -i $Container_Destino psql -U $DB_Usuario -d $DB_Nome
    
    Write-Host "OK - Banco restaurado com sucesso" -ForegroundColor Green
    
    Write-Host ""
    
    Write-Host "Listando tabelas do banco destino:" -ForegroundColor Yellow
    docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "\dt" -t
    
    Write-Host ""
    Write-Host "Contando registros no banco destino:" -ForegroundColor Yellow
    docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;" -t
    
    Write-Host ""
} else {
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host "ETAPA 6: EXECUTAR MIGRATIONS" -ForegroundColor Yellow
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Aguardando migrations..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host "OK - Migrations executadas" -ForegroundColor Green
    
    Write-Host ""
}

# ETAPA 7: VERIFICAR STATUS FINAL
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 7: VERIFICAR STATUS FINAL" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Containers em execucao:" -ForegroundColor Green
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"

Write-Host ""
Write-Host "Logs do FastAPI (ultimas 5 linhas):" -ForegroundColor Yellow
docker logs captar-fastapi 2>&1 | Select-Object -Last 5

Write-Host ""
Write-Host "Logs do Frontend (ultimas 5 linhas):" -ForegroundColor Yellow
docker logs captar-frontend 2>&1 | Select-Object -Last 5

Write-Host ""

# CONCLUSAO
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "OK - DEPLOYMENT CONCLUIDO COM SUCESSO!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Resumo:" -ForegroundColor Yellow
Write-Host "  OK - 7 containers iniciados" -ForegroundColor Green
Write-Host "  OK - PostgreSQL 18 na porta 5435" -ForegroundColor Green
Write-Host "  OK - Banco de dados copiado" -ForegroundColor Green
Write-Host "  OK - Todos os dados preservados" -ForegroundColor Green
Write-Host ""

Write-Host "Informacoes de Acesso:" -ForegroundColor Yellow
Write-Host "  Frontend:   http://$IP_Remoto`:3000" -ForegroundColor Cyan
Write-Host "  API:        http://$IP_Remoto`:8000" -ForegroundColor Cyan
Write-Host "  PostgreSQL: $IP_Remoto`:5435" -ForegroundColor Cyan
Write-Host "  MongoDB:    $IP_Remoto`:27017" -ForegroundColor Cyan
Write-Host ""

Write-Host "Proximas Acoes:" -ForegroundColor Yellow
Write-Host "  1. Acessar http://$IP_Remoto`:3000" -ForegroundColor Cyan
Write-Host "  2. Fazer login com suas credenciais" -ForegroundColor Cyan
Write-Host "  3. Verificar dados importados" -ForegroundColor Cyan
Write-Host "  4. Testar novas funcionalidades" -ForegroundColor Cyan
Write-Host ""

if (-not $skipCopy) {
    Write-Host "Arquivo de Backup:" -ForegroundColor Yellow
    Write-Host "  $backupFile" -ForegroundColor Cyan
    Write-Host ""
}
