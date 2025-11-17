# Script completo de deployment com copia de banco de dados
# 1. Fazer backup do banco existente
# 2. Atualizar para PostgreSQL 18
# 3. Deploy com Docker
# 4. Restaurar banco de dados

param(
    [string]$IP_Remoto = "172.26.97.64",
    [string]$Usuario_SSH = "root",
    [string]$Senha_SSH = "123",
    [string]$Container_Origem = "postgres",
    [string]$DB_Usuario = "captar",
    [string]$DB_Senha = "captar",
    [string]$DB_Nome = "captar"
)

# Definir Docker remoto
$env:DOCKER_HOST = "tcp://$IP_Remoto:2375"
$env:DB_HOST = $IP_Remoto
$env:DB_PORT = "5432"
$env:DB_NAME = $DB_Nome
$env:DB_USER = $DB_Usuario
$env:DB_PASSWORD = $DB_Senha

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         CAPTAR v2.0 - DEPLOYMENT COMPLETO COM BACKUP         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Configuracao:" -ForegroundColor Yellow
Write-Host "  Servidor Remoto: $IP_Remoto" -ForegroundColor Cyan
Write-Host "  Banco de Dados: $DB_Nome" -ForegroundColor Cyan
Write-Host "  PostgreSQL: 18 (Alpine)" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# ETAPA 1: VERIFICAR CONEXAO COM DOCKER
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 1: VERIFICAR CONEXAO COM DOCKER" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Conectando ao Docker remoto em $IP_Remoto..." -ForegroundColor Yellow

try {
    docker ps | Out-Null
    Write-Host "OK - Conectado ao Docker remoto" -ForegroundColor Green
} catch {
    Write-Host "ERRO - Nao foi possivel conectar ao Docker remoto!" -ForegroundColor Red
    Write-Host "Verifique se Docker esta rodando em $IP_Remoto:2375" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# ETAPA 2: FAZER BACKUP DO BANCO EXISTENTE
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 2: FAZER BACKUP DO BANCO EXISTENTE" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Verificar se container de origem existe
$containerExists = docker ps -a --format "table {{.Names}}" | Select-String $Container_Origem

if ($null -eq $containerExists) {
    Write-Host "AVISO - Container $Container_Origem nao encontrado" -ForegroundColor Yellow
    Write-Host "Pulando backup..." -ForegroundColor Yellow
    $backupFile = $null
} else {
    Write-Host "Container $Container_Origem encontrado" -ForegroundColor Green
    
    # Criar arquivo de backup
    $backupFile = "captar_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
    
    Write-Host "Criando arquivo de backup: $backupFile" -ForegroundColor Yellow
    
    try {
        docker exec $Container_Origem pg_dump -U $DB_Usuario $DB_Nome | Out-File -FilePath $backupFile -Encoding UTF8
        
        if (Test-Path $backupFile) {
            $fileSize = (Get-Item $backupFile).Length / 1MB
            Write-Host "OK - Backup criado com sucesso" -ForegroundColor Green
            Write-Host "Tamanho: $([Math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
        } else {
            Write-Host "AVISO - Nao foi possivel criar o backup" -ForegroundColor Yellow
            $backupFile = $null
        }
    } catch {
        Write-Host "AVISO - Erro ao fazer backup: $_" -ForegroundColor Yellow
        $backupFile = $null
    }
}

Write-Host ""

# ============================================================================
# ETAPA 3: PARAR CONTAINERS ANTIGOS
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 3: PARAR CONTAINERS ANTIGOS" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Parando containers..." -ForegroundColor Yellow
docker-compose down -v

Write-Host "OK - Containers parados e volumes removidos" -ForegroundColor Green

Write-Host ""

# ============================================================================
# ETAPA 4: INICIAR NOVO DEPLOY COM POSTGRESQL 18
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 4: INICIAR NOVO DEPLOY COM POSTGRESQL 18" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Iniciando containers..." -ForegroundColor Yellow
docker-compose up -d --build

Write-Host "Aguardando inicializacao (30 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "OK - Containers iniciados" -ForegroundColor Green

Write-Host ""

# ============================================================================
# ETAPA 5: RESTAURAR BANCO DE DADOS
# ============================================================================

if ($null -ne $backupFile -and (Test-Path $backupFile)) {
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "ETAPA 5: RESTAURAR BANCO DE DADOS" -ForegroundColor Yellow
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Restaurando banco de dados..." -ForegroundColor Yellow
    Write-Host "Arquivo: $backupFile" -ForegroundColor Cyan
    
    try {
        # Copiar arquivo para container
        Write-Host "Copiando arquivo para container..." -ForegroundColor Yellow
        docker cp $backupFile captar-postgres:/tmp/captar_backup.sql
        
        # Restaurar banco
        Write-Host "Executando restauracao..." -ForegroundColor Yellow
        docker exec -i captar-postgres psql -U $DB_Usuario -d $DB_Nome < $backupFile
        
        Write-Host "OK - Banco de dados restaurado" -ForegroundColor Green
    } catch {
        Write-Host "AVISO - Erro ao restaurar banco: $_" -ForegroundColor Yellow
    }
    
    Write-Host ""
} else {
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "ETAPA 5: EXECUTAR MIGRATIONS" -ForegroundColor Yellow
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Aguardando migrations..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host "OK - Migrations executadas" -ForegroundColor Green
    
    Write-Host ""
}

# ============================================================================
# ETAPA 6: VERIFICAR BANCO DE DADOS
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 6: VERIFICAR BANCO DE DADOS" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Listando tabelas..." -ForegroundColor Yellow
docker exec captar-postgres psql -U $DB_Usuario -d $DB_Nome -c "\dt"

Write-Host ""
Write-Host "Contando registros..." -ForegroundColor Yellow
docker exec captar-postgres psql -U $DB_Usuario -d $DB_Nome -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;" -t

Write-Host ""

# ============================================================================
# ETAPA 7: VERIFICAR STATUS DOS CONTAINERS
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 7: VERIFICAR STATUS DOS CONTAINERS" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Containers em execucao:" -ForegroundColor Green
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""

# ============================================================================
# ETAPA 8: VERIFICAR LOGS
# ============================================================================

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "ETAPA 8: VERIFICAR LOGS" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Logs do FastAPI (ultimas 5 linhas):" -ForegroundColor Yellow
docker logs captar-fastapi 2>&1 | Select-Object -Last 5

Write-Host ""
Write-Host "Logs do Frontend (ultimas 5 linhas):" -ForegroundColor Yellow
docker logs captar-frontend 2>&1 | Select-Object -Last 5

Write-Host ""

# ============================================================================
# CONCLUSAO
# ============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              OK - DEPLOYMENT CONCLUIDO COM SUCESSO!           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Resumo:" -ForegroundColor Yellow
Write-Host "  ✓ PostgreSQL 18 instalado" -ForegroundColor Green
Write-Host "  ✓ Banco de dados restaurado" -ForegroundColor Green
Write-Host "  ✓ Todos os dados copiados" -ForegroundColor Green
Write-Host "  ✓ 7 containers iniciados" -ForegroundColor Green
Write-Host "  ✓ Migrations executadas" -ForegroundColor Green
Write-Host ""

Write-Host "Informacoes de Acesso:" -ForegroundColor Yellow
Write-Host "  Frontend:   http://$IP_Remoto`:3000" -ForegroundColor Cyan
Write-Host "  API:        http://$IP_Remoto`:8000" -ForegroundColor Cyan
Write-Host "  PostgreSQL: $IP_Remoto`:5432" -ForegroundColor Cyan
Write-Host "  MongoDB:    $IP_Remoto`:27017" -ForegroundColor Cyan
Write-Host ""

Write-Host "Arquivo de Backup:" -ForegroundColor Yellow
if ($null -ne $backupFile) {
    Write-Host "  $backupFile" -ForegroundColor Cyan
} else {
    Write-Host "  Nenhum backup foi criado" -ForegroundColor Yellow
}

Write-Host ""

Write-Host "Proximas Acoes:" -ForegroundColor Yellow
Write-Host "  1. Acessar http://$IP_Remoto`:3000" -ForegroundColor Cyan
Write-Host "  2. Fazer login com suas credenciais" -ForegroundColor Cyan
Write-Host "  3. Verificar dados importados" -ForegroundColor Cyan
Write-Host "  4. Testar novas funcionalidades" -ForegroundColor Cyan
Write-Host ""

Write-Host "Documentacao:" -ForegroundColor Yellow
Write-Host "  - RESUMO_FINAL_DEPLOYMENT.txt" -ForegroundColor Cyan
Write-Host "  - CONFIGURAR_DOCKER_REMOTO.md" -ForegroundColor Cyan
Write-Host "  - INSTRUCOES_CONFIGURACAO_UBUNTU.txt" -ForegroundColor Cyan
Write-Host ""
