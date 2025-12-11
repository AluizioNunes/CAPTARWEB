# Guia de Testes dos Frontends

Este documento descreve como testar o acesso aos frontends CAPTAR e Evolution após o deploy no Portainer.

## 📋 Pré-requisitos

- Containers rodando no Portainer
- Acesso ao servidor onde os containers estão rodando (ou acesso via Portainer)

## 🧪 Opções de Teste

### Opção 1: Teste Local (do seu computador)

Se você tem acesso de rede ao servidor onde os containers estão rodando:

#### Windows (PowerShell)
```powershell
# Executar o script de teste
npm run test:frontends

# Ou diretamente:
.\scripts\test-frontends.ps1
```

#### Linux/Mac (Bash)
```bash
# Dar permissão de execução
chmod +x scripts/test-frontends.sh

# Executar o script
./scripts/test-frontends.sh
```

### Opção 2: Teste via Portainer Console

1. Acesse o Portainer
2. Vá em **Containers** → Selecione qualquer container da stack (ex: `captar-nginx`)
3. Clique em **Console** ou **Exec**
4. Execute:

```bash
# Instalar ferramentas se necessário (Alpine Linux)
apk add --no-cache curl wget

# Executar teste interno
wget -q --spider --timeout=3 http://frontend:80 && echo "CAPTAR Frontend: OK" || echo "CAPTAR Frontend: FALHOU"
wget -q --spider --timeout=3 http://evolution_frontend:80 && echo "Evolution Frontend: OK" || echo "Evolution Frontend: FALHOU"
wget -q --spider --timeout=3 http://fastapi:8000/health && echo "FastAPI: OK" || echo "FastAPI: FALHOU"
```

### Opção 3: Teste Manual via Browser

Acesse as URLs abaixo no seu navegador:

- **CAPTAR Frontend (direto)**: `http://SEU_SERVIDOR:5501`
- **CAPTAR via Nginx**: `http://SEU_SERVIDOR:5500`
- **Evolution Frontend**: `http://SEU_SERVIDOR:4380`

### Opção 4: Teste via curl/wget no servidor

Se você tem acesso SSH ao servidor:

```bash
# Testar CAPTAR Frontend
curl -I http://localhost:5501
curl -I http://localhost:5500

# Testar Evolution Frontend
curl -I http://localhost:4380

# Testar APIs
curl http://localhost:5500/api/health
curl http://localhost:4380/api/health
```

## 🔍 Verificação de Logs

### Ver logs do Evolution Frontend (onde estava o erro)

No Portainer:
1. Vá em **Containers** → `evolution_frontend`
2. Clique em **Logs**
3. Verifique se ainda há erros de `must-revalidate`

Ou via terminal:
```bash
docker logs evolution_frontend --tail 50
```

### Ver logs de todos os containers

```bash
docker-compose logs --tail=50
```

## ✅ Checklist de Testes

- [ ] CAPTAR Frontend responde na porta 5501
- [ ] CAPTAR via Nginx responde na porta 5500
- [ ] Evolution Frontend responde na porta 4380
- [ ] FastAPI Health Check retorna status OK
- [ ] Evolution API responde
- [ ] Não há erros de `must-revalidate` nos logs do Evolution Frontend
- [ ] Todos os containers estão com status "Running"

## 🐛 Troubleshooting

### Container não inicia

1. Verifique os logs: `docker logs evolution_frontend`
2. Verifique se o script `fix-nginx-entrypoint.sh` está montado corretamente
3. Verifique se o arquivo tem permissões de leitura

### Frontend não responde

1. Verifique se o container está rodando: `docker ps`
2. Verifique se a porta está mapeada corretamente
3. Verifique se há firewall bloqueando a porta
4. Verifique os logs do container

### Erro de `must-revalidate` ainda aparece

1. Pare o container: `docker stop evolution_frontend`
2. Remova o container: `docker rm evolution_frontend`
3. Recrie a stack no Portainer
4. Verifique se o script `fix-nginx-entrypoint.sh` está sendo executado

## 📝 Notas

- Os testes verificam tanto conectividade HTTP quanto status dos containers
- Os scripts podem ser executados localmente ou no servidor
- Para testes internos (dentro da rede Docker), use os nomes dos serviços como hostnames

