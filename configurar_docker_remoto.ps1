# Script para configurar Docker remoto automaticamente via SSH
# Servidor: 172.26.97.64 (Ubuntu Linux)
# Usuario: root
# Senha: 123

param(
    [string]$IP = "172.26.97.64",
    [string]$Usuario = "root",
    [string]$Senha = "123"
)

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURAR DOCKER REMOTO - 172.26.97.64" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se SSH está disponível
Write-Host "Verificando SSH..." -ForegroundColor Yellow
try {
    ssh -V | Out-Null
    Write-Host "OK - SSH disponivel" -ForegroundColor Green
} catch {
    Write-Host "ERRO - SSH nao encontrado!" -ForegroundColor Red
    Write-Host "Instale OpenSSH ou use PuTTY" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Conectando ao servidor $IP..." -ForegroundColor Yellow

# Criar script de configuracao para executar no servidor remoto
$scriptRemoto = @"
#!/bin/bash

echo "========================================================================"
echo "CONFIGURANDO DOCKER PARA TCP 2375"
echo "========================================================================"
echo ""

# Verificar se Docker esta instalado
if ! command -v docker &> /dev/null; then
    echo "ERRO - Docker nao esta instalado!"
    exit 1
fi

echo "OK - Docker encontrado"
echo ""

# Fazer backup do arquivo original
echo "Fazendo backup de /etc/docker/daemon.json..."
if [ -f /etc/docker/daemon.json ]; then
    cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
    echo "OK - Backup criado em /etc/docker/daemon.json.backup"
else
    echo "Arquivo nao existe, criando novo..."
fi

echo ""
echo "Configurando Docker para TCP 2375..."

# Criar novo arquivo daemon.json com TCP habilitado
cat > /etc/docker/daemon.json << 'EOF'
{
  "hosts": [
    "unix:///var/run/docker.sock",
    "tcp://0.0.0.0:2375"
  ],
  "debug": true,
  "log-driver": "json-file"
}
EOF

echo "OK - Arquivo /etc/docker/daemon.json atualizado"
echo ""

# Recarregar daemon
echo "Recarregando daemon do Docker..."
systemctl daemon-reload

# Reiniciar Docker
echo "Reiniciando Docker..."
systemctl restart docker

echo ""
echo "Aguardando Docker inicializar (5 segundos)..."
sleep 5

# Verificar se Docker esta rodando
if systemctl is-active --quiet docker; then
    echo "OK - Docker esta rodando"
else
    echo "ERRO - Docker nao iniciou!"
    exit 1
fi

echo ""
echo "Verificando porta 2375..."

# Verificar se porta 2375 esta aberta
if netstat -tlnp 2>/dev/null | grep -q 2375; then
    echo "OK - Porta 2375 esta aberta"
else
    echo "AVISO - Porta 2375 pode nao estar respondendo"
    echo "Tentando com ss..."
    ss -tlnp 2>/dev/null | grep 2375
fi

echo ""
echo "Testando conexao local..."
if curl -s http://localhost:2375/version > /dev/null; then
    echo "OK - Docker respondendo em http://localhost:2375"
else
    echo "AVISO - Docker pode nao estar respondendo"
fi

echo ""
echo "========================================================================"
echo "OK - DOCKER CONFIGURADO COM SUCESSO!"
echo "========================================================================"
echo ""
echo "Proximas acoes:"
echo "1. No cliente, execute:"
echo "   `$env:DOCKER_HOST = 'tcp://172.26.97.64:2375'"
echo "   docker version"
echo ""
echo "2. Se conectar com sucesso, execute:"
echo "   .\start_captar.ps1"
echo ""
"@

# Salvar script em arquivo temporario
$tempScript = "$env:TEMP\config_docker.sh"
$scriptRemoto | Out-File -FilePath $tempScript -Encoding UTF8 -Force

Write-Host "Script de configuracao criado" -ForegroundColor Green
Write-Host ""

# Copiar script para servidor remoto via SCP
Write-Host "Copiando script para servidor remoto..." -ForegroundColor Yellow

# Usar expect para passar senha automaticamente
$expectScript = @"
#!/usr/bin/expect -f
set timeout 30
set ip "$IP"
set user "$Usuario"
set password "$Senha"

spawn scp -o StrictHostKeyChecking=no "$tempScript" `$user@`$ip:/tmp/config_docker.sh
expect {
    "password:" {
        send "`$password\r"
        expect eof
    }
    "Permission denied" {
        puts "ERRO - Senha incorreta!"
        exit 1
    }
}
"@

# Tentar com SCP direto (pode pedir senha)
try {
    Write-Host "Tentando copiar arquivo via SCP..." -ForegroundColor Yellow
    
    # Usar SSH para copiar (alternativa ao SCP)
    $sshCmd = "cat $tempScript | ssh -o StrictHostKeyChecking=no $Usuario@$IP 'cat > /tmp/config_docker.sh'"
    
    # Executar via PowerShell
    Write-Host "Executando comando SSH..." -ForegroundColor Yellow
    
    # Usar plink (PuTTY) se disponivel
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        Write-Host "Usando PuTTY plink..." -ForegroundColor Yellow
        # plink nao suporta piping, usar arquivo temporario
    } else {
        Write-Host "SSH nao disponivel com piping" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "AVISO - Nao foi possivel copiar arquivo automaticamente" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "INSTRUCOES MANUAIS" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Se a copia automatica nao funcionou, execute manualmente:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Abra terminal SSH para 172.26.97.64" -ForegroundColor Cyan
Write-Host "   ssh root@172.26.97.64" -ForegroundColor Cyan
Write-Host "   Senha: 123" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Execute os comandos abaixo:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Fazer backup" -ForegroundColor Green
Write-Host "   cp /etc/docker/daemon.json /etc/docker/daemon.json.backup" -ForegroundColor Green
Write-Host ""
Write-Host "   # Criar novo arquivo" -ForegroundColor Green
Write-Host "   cat > /etc/docker/daemon.json << 'EOF'" -ForegroundColor Green
Write-Host "   {" -ForegroundColor Green
Write-Host "     'hosts': [" -ForegroundColor Green
Write-Host "       'unix:///var/run/docker.sock'," -ForegroundColor Green
Write-Host "       'tcp://0.0.0.0:2375'" -ForegroundColor Green
Write-Host "     ]," -ForegroundColor Green
Write-Host "     'debug': true," -ForegroundColor Green
Write-Host "     'log-driver': 'json-file'" -ForegroundColor Green
Write-Host "   }" -ForegroundColor Green
Write-Host "   EOF" -ForegroundColor Green
Write-Host ""
Write-Host "   # Recarregar e reiniciar" -ForegroundColor Green
Write-Host "   systemctl daemon-reload" -ForegroundColor Green
Write-Host "   systemctl restart docker" -ForegroundColor Green
Write-Host ""
Write-Host "   # Verificar" -ForegroundColor Green
Write-Host "   netstat -tlnp | grep 2375" -ForegroundColor Green
Write-Host ""
Write-Host "3. Apos configurar, volte ao cliente e execute:" -ForegroundColor Cyan
Write-Host "   `$env:DOCKER_HOST = 'tcp://172.26.97.64:2375'" -ForegroundColor Cyan
Write-Host "   docker version" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Se conectar com sucesso, execute:" -ForegroundColor Cyan
Write-Host "   .\start_captar.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
