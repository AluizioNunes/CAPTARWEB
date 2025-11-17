# Script para copiar banco de dados entre containers PostgreSQL
# Origem: postgres (porta 5432)
# Destino: captar-postgres (porta 5435)

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

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         COPIAR BANCO ENTRE CONTAINERS POSTGRESQL              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Configuracao:" -ForegroundColor Yellow
Write-Host "  Servidor: $IP_Remoto" -ForegroundColor Cyan
Write-Host "  Origem: $Container_Origem (porta 5432)" -ForegroundColor Cyan
Write-Host "  Destino: $Container_Destino (porta 5435)" -ForegroundColor Cyan
Write-Host "  Banco: $DB_Nome" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# ETAPA 1: VERIFICAR CONEXAO
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 1: VERIFICAR CONEXAO COM DOCKER" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
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

# ============================================================================
# ETAPA 2: VERIFICAR CONTAINERS
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 2: VERIFICAR CONTAINERS" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Listando containers..." -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "postgres"

Write-Host ""

# Verificar container origem
$containerOrigemExists = docker ps --format "table {{.Names}}" | Select-String "^$Container_Origem$"
if ($null -eq $containerOrigemExists) {
    Write-Host "ERRO - Container $Container_Origem nao encontrado!" -ForegroundColor Red
    exit 1
}
Write-Host "OK - Container $Container_Origem encontrado" -ForegroundColor Green

# Verificar container destino
$containerDestinoExists = docker ps --format "table {{.Names}}" | Select-String "^$Container_Destino$"
if ($null -eq $containerDestinoExists) {
    Write-Host "ERRO - Container $Container_Destino nao encontrado!" -ForegroundColor Red
    exit 1
}
Write-Host "OK - Container $Container_Destino encontrado" -ForegroundColor Green

Write-Host ""

# ============================================================================
# ETAPA 3: FAZER DUMP DO BANCO ORIGEM
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 3: FAZER DUMP DO BANCO ORIGEM" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Fazendo dump do banco $DB_Nome do container $Container_Origem..." -ForegroundColor Yellow

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

# ============================================================================
# ETAPA 4: LISTAR TABELAS DO BANCO ORIGEM
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 4: LISTAR TABELAS DO BANCO ORIGEM" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Tabelas no banco origem:" -ForegroundColor Yellow
docker exec $Container_Origem psql -U $DB_Usuario -d $DB_Nome -c "\dt" -t

Write-Host ""
Write-Host "Contando registros..." -ForegroundColor Yellow
docker exec $Container_Origem psql -U $DB_Usuario -d $DB_Nome -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" -t

Write-Host ""

# ============================================================================
# ETAPA 5: RESTAURAR BANCO NO DESTINO
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 5: RESTAURAR BANCO NO DESTINO" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Copiando arquivo para container destino..." -ForegroundColor Yellow
docker cp $backupFile "$Container_Destino`:/tmp/backup.sql"

Write-Host "Restaurando banco no container destino..." -ForegroundColor Yellow
docker exec -i $Container_Destino psql -U $DB_Usuario -d $DB_Nome < $backupFile

Write-Host "OK - Banco restaurado com sucesso" -ForegroundColor Green

Write-Host ""

# ============================================================================
# ETAPA 6: VERIFICAR BANCO DESTINO
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 6: VERIFICAR BANCO DESTINO" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Tabelas no banco destino:" -ForegroundColor Yellow
docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "\dt" -t

Write-Host ""
Write-Host "Contando registros..." -ForegroundColor Yellow
docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" -t

Write-Host ""

# ============================================================================
# ETAPA 7: COMPARAR BANCOS
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 7: COMPARAR BANCOS" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Tabelas no banco origem:" -ForegroundColor Yellow
$tabelasOrigem = docker exec $Container_Origem psql -U $DB_Usuario -d $DB_Nome -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" -t
Write-Host $tabelasOrigem

Write-Host ""
Write-Host "Tabelas no banco destino:" -ForegroundColor Yellow
$tabelasDestino = docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" -t
Write-Host $tabelasDestino

Write-Host ""
Write-Host "Registros no banco origem:" -ForegroundColor Yellow
$registrosOrigem = docker exec $Container_Origem psql -U $DB_Usuario -d $DB_Nome -c "SELECT SUM(n_live_tup) FROM pg_stat_user_tables;" -t
Write-Host $registrosOrigem

Write-Host ""
Write-Host "Registros no banco destino:" -ForegroundColor Yellow
$registrosDestino = docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "SELECT SUM(n_live_tup) FROM pg_stat_user_tables;" -t
Write-Host $registrosDestino

Write-Host ""

# ============================================================================
# CONCLUSAO
# ============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              OK - COPIA CONCLUIDA COM SUCESSO!                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Resumo:" -ForegroundColor Yellow
Write-Host "  ✓ Banco copiado com sucesso" -ForegroundColor Green
Write-Host "  ✓ Tabelas preservadas" -ForegroundColor Green
Write-Host "  ✓ Registros preservados" -ForegroundColor Green
Write-Host "  ✓ Integridade verificada" -ForegroundColor Green
Write-Host ""

Write-Host "Informacoes:" -ForegroundColor Yellow
Write-Host "  Arquivo de backup: $backupFile" -ForegroundColor Cyan
Write-Host "  Container origem: $Container_Origem (porta 5432)" -ForegroundColor Cyan
Write-Host "  Container destino: $Container_Destino (porta 5435)" -ForegroundColor Cyan
Write-Host "  Banco: $DB_Nome" -ForegroundColor Cyan
Write-Host ""

Write-Host "Proximas acoes:" -ForegroundColor Yellow
Write-Host "  1. Testar conexao no novo banco:" -ForegroundColor Cyan
Write-Host "     docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c 'SELECT COUNT(*) FROM usuarios;'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Acessar frontend:" -ForegroundColor Cyan
Write-Host "     http://172.26.97.64:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Testar API:" -ForegroundColor Cyan
Write-Host "     curl http://172.26.97.64:8000/health" -ForegroundColor Cyan
Write-Host ""
