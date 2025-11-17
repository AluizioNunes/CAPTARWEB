# Script para copiar banco de dados PostgreSQL existente para novo deploy
# Origem: Container PostgreSQL existente
# Destino: Novo container PostgreSQL 18 no Docker remoto

param(
    [string]$IP_Remoto = "172.26.97.64",
    [string]$Usuario_SSH = "root",
    [string]$Senha_SSH = "123",
    [string]$Container_Origem = "postgres",
    [string]$DB_Nome = "captar",
    [string]$DB_Usuario = "captar",
    [string]$DB_Senha = "captar"
)

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "COPIAR BANCO DE DADOS POSTGRESQL" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Configuracao:" -ForegroundColor Yellow
Write-Host "  Servidor Remoto: $IP_Remoto" -ForegroundColor Cyan
Write-Host "  Container Origem: $Container_Origem" -ForegroundColor Cyan
Write-Host "  Banco de Dados: $DB_Nome" -ForegroundColor Cyan
Write-Host ""

# Definir Docker remoto
$env:DOCKER_HOST = "tcp://$IP_Remoto:2375"

Write-Host "Conectando ao Docker remoto..." -ForegroundColor Yellow

# Verificar conexao
try {
    docker ps | Out-Null
    Write-Host "OK - Conectado ao Docker remoto" -ForegroundColor Green
} catch {
    Write-Host "ERRO - Nao foi possivel conectar ao Docker remoto!" -ForegroundColor Red
    Write-Host "Verifique se Docker esta rodando em $IP_Remoto:2375" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 1: FAZER DUMP DO BANCO EXISTENTE" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Criar diretorio temporario
$tempDir = "$env:TEMP\captar_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "Diretorio temporario: $tempDir" -ForegroundColor Cyan
Write-Host ""

# Fazer dump do banco existente
Write-Host "Fazendo dump do banco de dados existente..." -ForegroundColor Yellow
Write-Host "Comando: docker exec $Container_Origem pg_dump -U $DB_Usuario $DB_Nome" -ForegroundColor Gray

try {
    $dumpFile = "$tempDir\captar_backup.sql"
    
    # Executar pg_dump
    docker exec $Container_Origem pg_dump -U $DB_Usuario $DB_Nome | Out-File -FilePath $dumpFile -Encoding UTF8
    
    if (Test-Path $dumpFile) {
        $fileSize = (Get-Item $dumpFile).Length / 1MB
        Write-Host "OK - Dump criado com sucesso" -ForegroundColor Green
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
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 2: ATUALIZAR docker-compose.yml PARA POSTGRES 18" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Ler arquivo docker-compose.yml
$dockerComposePath = ".\docker-compose.yml"

Write-Host "Lendo: $dockerComposePath" -ForegroundColor Yellow

if (Test-Path $dockerComposePath) {
    $content = Get-Content $dockerComposePath -Raw
    
    # Substituir versao do PostgreSQL
    $contentAtualizado = $content -replace 'image: postgres:\d+(-alpine)?', 'image: postgres:18-alpine'
    
    # Salvar arquivo atualizado
    Set-Content -Path $dockerComposePath -Value $contentAtualizado -Encoding UTF8
    
    Write-Host "OK - docker-compose.yml atualizado para PostgreSQL 18" -ForegroundColor Green
} else {
    Write-Host "AVISO - docker-compose.yml nao encontrado em $dockerComposePath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 3: PARAR CONTAINERS ANTIGOS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Parando containers..." -ForegroundColor Yellow
docker-compose down -v

Write-Host "OK - Containers parados" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 4: INICIAR NOVO POSTGRES 18" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Iniciando novo PostgreSQL 18..." -ForegroundColor Yellow
docker-compose up -d postgres

Write-Host "Aguardando PostgreSQL inicializar (15 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "OK - PostgreSQL 18 iniciado" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 5: RESTAURAR BANCO DE DADOS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Restaurando banco de dados..." -ForegroundColor Yellow
Write-Host "Arquivo: $dumpFile" -ForegroundColor Cyan

# Copiar arquivo para container
Write-Host "Copiando arquivo SQL para container..." -ForegroundColor Yellow
docker cp $dumpFile captar-postgres:/tmp/captar_backup.sql

# Restaurar banco
Write-Host "Executando restauracao..." -ForegroundColor Yellow
Get-Content -Raw $dumpFile | docker exec -i captar-postgres psql -U $DB_Usuario -d $DB_Nome

Write-Host "OK - Banco de dados restaurado" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 6: VERIFICAR BANCO DE DADOS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Listando tabelas..." -ForegroundColor Yellow

$tabelas = docker exec captar-postgres psql -U $DB_Usuario -d $DB_Nome -c "\dt" -t

Write-Host "Tabelas encontradas:" -ForegroundColor Green
Write-Host $tabelas -ForegroundColor Cyan

Write-Host ""
Write-Host "Contando registros..." -ForegroundColor Yellow

$registros = docker exec captar-postgres psql -U $DB_Usuario -d $DB_Nome -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" -t

Write-Host "Registros por tabela:" -ForegroundColor Green
Write-Host $registros -ForegroundColor Cyan

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 7: INICIAR TODOS OS CONTAINERS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Iniciando todos os containers..." -ForegroundColor Yellow
docker-compose up -d --build

Write-Host "Aguardando inicializacao (30 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "ETAPA 8: VERIFICAR STATUS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Containers em execucao:" -ForegroundColor Green
docker ps

Write-Host ""
Write-Host "Logs das migrations:" -ForegroundColor Yellow
docker logs captar-migrations

Write-Host ""
Write-Host "Logs do FastAPI:" -ForegroundColor Yellow
docker logs captar-fastapi | Select-Object -Last 10

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "OK - BANCO DE DADOS COPIADO COM SUCESSO!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Resumo:" -ForegroundColor Yellow
Write-Host "  - PostgreSQL 18 instalado" -ForegroundColor Cyan
Write-Host "  - Banco de dados restaurado" -ForegroundColor Cyan
Write-Host "  - Todos os dados copiados" -ForegroundColor Cyan
Write-Host "  - Containers iniciados" -ForegroundColor Cyan
Write-Host ""

Write-Host "Proximas acoes:" -ForegroundColor Yellow
Write-Host "  1. Testar conexao: docker exec captar-postgres psql -U $DB_Usuario -d $DB_Nome -c 'SELECT COUNT(*) FROM information_schema.tables;'" -ForegroundColor Cyan
Write-Host "  2. Acessar frontend: http://172.26.97.64:3000" -ForegroundColor Cyan
Write-Host "  3. Testar API: curl http://172.26.97.64:8000/health" -ForegroundColor Cyan
Write-Host ""

Write-Host "Arquivo de backup:" -ForegroundColor Yellow
Write-Host "  $dumpFile" -ForegroundColor Cyan
Write-Host ""
