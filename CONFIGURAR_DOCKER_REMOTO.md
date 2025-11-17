# 🐳 CONFIGURAR DOCKER REMOTO

## 📍 INFORMAÇÃO

Docker está instalado em servidor remoto: **172.26.97.64**

---

## ✅ SOLUÇÃO: CONECTAR AO DOCKER REMOTO

### PASSO 1: Verificar Docker Remoto

```powershell
# Testar conexão com Docker remoto
docker -H tcp://172.26.97.64:2375 version

# Resultado esperado:
# Client: Docker Engine - Community
# Server: Docker Engine - Community
```

### PASSO 2: Configurar Variável de Ambiente

```powershell
# Opção 1: Temporária (apenas sessão atual)
$env:DOCKER_HOST = "tcp://172.26.97.64:2375"

# Opção 2: Permanente (adicionar ao perfil PowerShell)
# Editar: $PROFILE
# Adicionar: $env:DOCKER_HOST = "tcp://172.26.97.64:2375"
```

### PASSO 3: Verificar Conexão

```powershell
# Listar containers
docker ps

# Listar imagens
docker images

# Resultado esperado: Lista de containers/imagens do servidor remoto
```

### PASSO 4: Configurar docker-compose para Remoto

Editar arquivo: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # ... resto do arquivo ...

# Adicionar ao final:
x-docker-host: &docker-host
  DOCKER_HOST: tcp://172.26.97.64:2375
```

Ou usar variável de ambiente:

```powershell
$env:DOCKER_HOST = "tcp://172.26.97.64:2375"
docker-compose up -d --build
```

---

## 🚀 DEPLOYMENT COM DOCKER REMOTO

### PASSO 1: Definir Variáveis de Ambiente

```powershell
# Definir Docker remoto
$env:DOCKER_HOST = "tcp://172.26.97.64:2375"

# Definir banco de dados remoto (se necessário)
$env:DB_HOST = "172.26.97.64"
$env:DB_PORT = "5432"
$env:DB_NAME = "captar"
$env:DB_USER = "captar"
$env:DB_PASSWORD = "captar"
```

### PASSO 2: Navegar para o Projeto

```powershell
cd c:\www\Streamlit\Captar\CAPTAR
```

### PASSO 3: Parar Containers Antigos

```powershell
docker-compose down -v
```

### PASSO 4: Build e Deploy

```powershell
docker-compose up -d --build
```

### PASSO 5: Verificar Containers Remotos

```powershell
# Listar containers no servidor remoto
docker ps

# Ver logs de um container
docker logs captar-fastapi

# Ver logs em tempo real
docker logs -f captar-fastapi
```

### PASSO 6: Verificar Migrations

```powershell
docker logs captar-migrations

# Resultado esperado:
# "Migrations completed"
```

### PASSO 7: Testar Endpoints

```powershell
# Health check
curl http://172.26.97.64:8000/health

# Login
curl -X POST http://172.26.97.64:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"usuario":"admin","senha":"123456"}'

# Frontend
curl http://172.26.97.64:3000
```

---

## 📋 ARQUIVO: start_server.ps1 ATUALIZADO

Editar: `c:\www\Streamlit\Captar\start_server.ps1`

```powershell
# Script para iniciar CAPTAR v2.0 com Docker remoto

# Definir variáveis de ambiente
$env:DOCKER_HOST = "tcp://172.26.97.64:2375"
$env:DB_HOST = "172.26.97.64"
$env:DB_PORT = "5432"
$env:DB_NAME = "captar"
$env:DB_USER = "captar"
$env:DB_PASSWORD = "captar"

# Navegar para o projeto
cd c:\www\Streamlit\Captar\CAPTAR

Write-Host "🐳 Conectando ao Docker remoto em 172.26.97.64..." -ForegroundColor Green

# Verificar conexão
docker version

Write-Host "✅ Conexão com Docker remoto estabelecida!" -ForegroundColor Green

# Parar containers antigos
Write-Host "⏹️  Parando containers antigos..." -ForegroundColor Yellow
docker-compose down -v

# Build e deploy
Write-Host "🚀 Iniciando deployment..." -ForegroundColor Green
docker-compose up -d --build

# Aguardar inicialização
Write-Host "⏳ Aguardando inicialização dos containers..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Verificar migrations
Write-Host "🔍 Verificando migrations..." -ForegroundColor Cyan
docker logs captar-migrations

# Verificar FastAPI
Write-Host "🔍 Verificando FastAPI..." -ForegroundColor Cyan
docker logs captar-fastapi

# Listar containers
Write-Host "📋 Containers em execução:" -ForegroundColor Green
docker ps

# Informações de acesso
Write-Host "`n✅ CAPTAR v2.0 iniciado com sucesso!" -ForegroundColor Green
Write-Host "📍 Servidor: 172.26.97.64" -ForegroundColor Cyan
Write-Host "🌐 Frontend: http://172.26.97.64:3000" -ForegroundColor Cyan
Write-Host "🔌 API: http://172.26.97.64:8000" -ForegroundColor Cyan
Write-Host "🗄️  PostgreSQL: 172.26.97.64:5432" -ForegroundColor Cyan
Write-Host "🍃 MongoDB: 172.26.97.64:27017" -ForegroundColor Cyan
```

---

## 🔧 TROUBLESHOOTING

### Erro: "Cannot connect to Docker daemon"

```powershell
# Verificar se Docker está rodando no servidor remoto
docker -H tcp://172.26.97.64:2375 version

# Se não conectar, verificar:
# 1. IP correto: 172.26.97.64
# 2. Porta correta: 2375
# 3. Docker daemon rodando no servidor remoto
# 4. Firewall permitindo conexão
```

### Erro: "Connection refused"

```powershell
# Docker daemon pode não estar escutando em TCP
# No servidor remoto, verificar:
# sudo systemctl status docker
# sudo netstat -tlnp | grep docker

# Habilitar TCP no Docker (servidor remoto):
# Editar: /etc/docker/daemon.json
# Adicionar: "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
# Reiniciar: sudo systemctl restart docker
```

### Erro: "Permission denied"

```powershell
# Pode ser necessário autenticação
# Usar: docker -H tcp://172.26.97.64:2376 (com TLS)
# Ou configurar credenciais
```

---

## 📊 VERIFICAÇÃO

### Verificar Containers Remotos

```powershell
$env:DOCKER_HOST = "tcp://172.26.97.64:2375"

# Listar containers
docker ps

# Resultado esperado:
# CONTAINER ID   IMAGE                    STATUS
# xxxxx          captar-postgres:latest   Up 2 minutes
# xxxxx          captar-mongodb:latest    Up 2 minutes
# xxxxx          captar-fastapi:latest    Up 2 minutes
# xxxxx          captar-nestjs:latest     Up 2 minutes
# xxxxx          captar-frontend:latest   Up 2 minutes
# xxxxx          captar-nginx:latest      Up 2 minutes
```

### Verificar Volumes Remotos

```powershell
docker volume ls

# Resultado esperado:
# DRIVER    VOLUME NAME
# local     captar_postgres_data
# local     captar_mongodb_data
```

### Verificar Networks Remotas

```powershell
docker network ls

# Resultado esperado:
# NETWORK ID     NAME              DRIVER
# xxxxx          captar-network    bridge
```

---

## 🎯 PRÓXIMAS AÇÕES

1. **Editar start_server.ps1** com configuração remota
2. **Executar**: `.\start_server.ps1`
3. **Aguardar**: Inicialização dos containers
4. **Verificar**: `docker ps`
5. **Acessar**: http://172.26.97.64:3000

---

## 📝 NOTAS IMPORTANTES

1. **IP Remoto**: 172.26.97.64
2. **Porta Docker**: 2375 (padrão)
3. **Porta Frontend**: 3000
4. **Porta API**: 8000
5. **Porta PostgreSQL**: 5432
6. **Porta MongoDB**: 27017

---

**Data**: 16/11/2025
**Status**: ✅ Pronto para Docker Remoto
**Próxima Ação**: Executar start_server.ps1
