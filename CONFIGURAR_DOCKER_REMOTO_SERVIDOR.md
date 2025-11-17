# 🐳 CONFIGURAR DOCKER REMOTO NO SERVIDOR

## ⚠️ PROBLEMA

Docker remoto em **172.26.97.64** não está respondendo na porta **2375**

---

## ✅ SOLUÇÃO: HABILITAR TCP NO DOCKER REMOTO

### NO SERVIDOR REMOTO (172.26.97.64)

#### PASSO 1: Verificar Docker

```bash
# Verificar se Docker está rodando
sudo systemctl status docker

# Resultado esperado:
# active (running)
```

#### PASSO 2: Configurar Docker para TCP

```bash
# Editar arquivo de configuração do Docker
sudo nano /etc/docker/daemon.json
```

#### PASSO 3: Adicionar Configuração TCP

Adicionar ou modificar para:

```json
{
  "hosts": [
    "unix:///var/run/docker.sock",
    "tcp://0.0.0.0:2375"
  ],
  "debug": true,
  "log-driver": "json-file"
}
```

#### PASSO 4: Salvar e Sair

```bash
# Salvar: Ctrl+O, Enter
# Sair: Ctrl+X
```

#### PASSO 5: Reiniciar Docker

```bash
# Reiniciar o daemon do Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# Verificar se está rodando
sudo systemctl status docker
```

#### PASSO 6: Verificar Porta 2375

```bash
# Verificar se Docker está escutando na porta 2375
sudo netstat -tlnp | grep 2375

# Resultado esperado:
# tcp  0  0  0.0.0.0:2375  0.0.0.0:*  LISTEN  xxxx/dockerd
```

#### PASSO 7: Testar Conexão Local

```bash
# No servidor remoto, testar:
curl http://localhost:2375/version

# Resultado esperado:
# {"Version":"20.10.x", ...}
```

---

## 🔧 ALTERNATIVA: USAR SSH TUNNEL

Se não conseguir habilitar TCP, use SSH tunnel:

### NO CLIENTE (Sua máquina)

```powershell
# Criar SSH tunnel
ssh -L 2375:localhost:2375 user@172.26.97.64

# Depois, em outro terminal:
$env:DOCKER_HOST = "tcp://localhost:2375"
docker ps
```

---

## 🚀 APÓS CONFIGURAR NO SERVIDOR

### NO CLIENTE (Sua máquina)

#### PASSO 1: Testar Conexão

```powershell
# Definir variável de ambiente
$env:DOCKER_HOST = "tcp://172.26.97.64:2375"

# Testar conexão
docker version

# Resultado esperado:
# Client: Docker Engine - Community
# Server: Docker Engine - Community
```

#### PASSO 2: Listar Containers

```powershell
docker ps

# Resultado esperado:
# CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS
```

#### PASSO 3: Executar Deploy

```powershell
cd c:\www\Streamlit\Captar\CAPTAR

# Parar containers antigos
docker-compose down -v

# Build e deploy
docker-compose up -d --build

# Verificar
docker ps
```

---

## 📋 VERIFICAÇÃO NO SERVIDOR

### Verificar Configuração

```bash
# Ver configuração atual do Docker
sudo cat /etc/docker/daemon.json

# Resultado esperado:
# {
#   "hosts": [
#     "unix:///var/run/docker.sock",
#     "tcp://0.0.0.0:2375"
#   ]
# }
```

### Verificar Logs

```bash
# Ver logs do Docker
sudo journalctl -u docker -n 50

# Ou
sudo tail -f /var/log/docker.log
```

### Verificar Firewall

```bash
# Verificar se porta 2375 está aberta
sudo ufw status

# Se necessário, abrir porta:
sudo ufw allow 2375/tcp

# Recarregar firewall:
sudo ufw reload
```

---

## ⚠️ SEGURANÇA

### IMPORTANTE: Porta 2375 sem TLS

A porta 2375 é **sem criptografia**. Para produção, use:

```json
{
  "hosts": [
    "unix:///var/run/docker.sock",
    "tcp://0.0.0.0:2376"
  ],
  "tls": true,
  "tlscert": "/etc/docker/certs.d/server-cert.pem",
  "tlskey": "/etc/docker/certs.d/server-key.pem",
  "tlscacert": "/etc/docker/certs.d/ca.pem"
}
```

Ou use SSH tunnel (mais seguro).

---

## 🔍 TROUBLESHOOTING

### Erro: "Cannot connect to Docker daemon"

```bash
# No servidor remoto:
sudo systemctl restart docker
sudo netstat -tlnp | grep 2375
```

### Erro: "Permission denied"

```bash
# No servidor remoto:
sudo usermod -aG docker $USER
newgrp docker
```

### Erro: "Connection refused"

```bash
# Verificar se Docker está rodando:
sudo systemctl status docker

# Verificar se porta está aberta:
sudo netstat -tlnp | grep 2375

# Verificar firewall:
sudo ufw status
```

---

## ✅ PRÓXIMAS AÇÕES

1. **No servidor remoto (172.26.97.64)**:
   - [ ] Editar `/etc/docker/daemon.json`
   - [ ] Adicionar TCP 2375
   - [ ] Reiniciar Docker
   - [ ] Verificar porta 2375

2. **No cliente (Sua máquina)**:
   - [ ] Testar: `docker -H tcp://172.26.97.64:2375 version`
   - [ ] Executar: `.\start_captar.ps1`
   - [ ] Verificar: `docker ps`
   - [ ] Acessar: http://172.26.97.64:3000

---

**Data**: 16/11/2025
**Status**: ⏳ Aguardando configuração do Docker remoto
**Próxima Ação**: Configurar TCP no servidor remoto
