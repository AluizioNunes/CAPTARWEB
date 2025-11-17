# Script simples para fazer backup e restaurar banco de dados PostgreSQL
# Entre containers Docker

param(
    [string]$IP_Remoto = "172.26.97.64",
    [string]$Acao = "backup",  # backup ou restore
    [string]$Container_Origem = "postgres",
    [string]$Container_Destino = "captar-postgres",
    [string]$DB_Usuario = "captar",
    [string]$DB_Nome = "captar"
)

# Definir Docker remoto
$env:DOCKER_HOST = "tcp://$IP_Remoto:2375"

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "BACKUP E RESTAURACAO DE BANCO DE DADOS" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Acao: $Acao" -ForegroundColor Yellow
Write-Host "Container Origem: $Container_Origem" -ForegroundColor Yellow
Write-Host "Container Destino: $Container_Destino" -ForegroundColor Yellow
Write-Host "Banco: $DB_Nome" -ForegroundColor Yellow
Write-Host ""

if ($Acao -eq "backup") {
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host "FAZENDO BACKUP DO BANCO DE DADOS" -ForegroundColor Yellow
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Criar arquivo de backup
    $backupFile = "captar_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
    
    Write-Host "Criando arquivo: $backupFile" -ForegroundColor Yellow
    
    # Fazer dump
    Write-Host "Executando pg_dump..." -ForegroundColor Yellow
    docker exec $Container_Origem pg_dump -U $DB_Usuario $DB_Nome | Out-File -FilePath $backupFile -Encoding UTF8
    
    if (Test-Path $backupFile) {
        $fileSize = (Get-Item $backupFile).Length / 1MB
        Write-Host "OK - Backup criado com sucesso" -ForegroundColor Green
        Write-Host "Arquivo: $backupFile" -ForegroundColor Cyan
        Write-Host "Tamanho: $([Math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
    } else {
        Write-Host "ERRO - Nao foi possivel criar o backup!" -ForegroundColor Red
        exit 1
    }
    
} elseif ($Acao -eq "restore") {
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host "RESTAURANDO BANCO DE DADOS" -ForegroundColor Yellow
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Procurar arquivo de backup mais recente
    $backupFile = Get-ChildItem -Filter "captar_backup_*.sql" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    if ($null -eq $backupFile) {
        Write-Host "ERRO - Nenhum arquivo de backup encontrado!" -ForegroundColor Red
        Write-Host "Procure por: captar_backup_*.sql" -ForegroundColor Yellow
        exit 1
    }
    
    $backupPath = $backupFile.FullName
    
    Write-Host "Arquivo de backup: $backupPath" -ForegroundColor Yellow
    Write-Host "Tamanho: $([Math]::Round($backupFile.Length / 1MB, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    
    # Copiar arquivo para container
    Write-Host "Copiando arquivo para container..." -ForegroundColor Yellow
    docker cp $backupPath "$Container_Destino`:/tmp/captar_backup.sql"
    
    # Restaurar banco
    Write-Host "Restaurando banco de dados..." -ForegroundColor Yellow
    docker exec -i $Container_Destino psql -U $DB_Usuario -d $DB_Nome < $backupPath
    
    Write-Host "OK - Banco de dados restaurado" -ForegroundColor Green
    
    # Verificar
    Write-Host ""
    Write-Host "Verificando tabelas..." -ForegroundColor Yellow
    docker exec $Container_Destino psql -U $DB_Usuario -d $DB_Nome -c "\dt"
    
} else {
    Write-Host "ERRO - Acao invalida: $Acao" -ForegroundColor Red
    Write-Host "Use: backup ou restore" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "OK - OPERACAO CONCLUIDA!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
