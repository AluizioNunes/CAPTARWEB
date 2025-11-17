# 🚀 RESOLVER ERRO NPM E FAZER DEPLOY

## ❌ PROBLEMA: Erro "ENOSPC: no space left on device"

Seu disco está cheio. Siga os passos abaixo:

---

## ✅ SOLUÇÃO RÁPIDA

### PASSO 1: Limpar Espaço em Disco (Windows)

```powershell
# Abrir PowerShell como Administrador

# Limpar arquivos temporários
Remove-Item -Recurse -Force $env:TEMP\*
Remove-Item -Recurse -Force $env:WINDIR\Temp\*

# Limpar cache do npm
npm cache clean --force

# Limpar Docker
docker system prune -f
docker volume prune -f
```

### PASSO 2: Remover node_modules Antigos

```powershell
cd c:\www\Streamlit\Captar\CAPTAR\Frontend

# Remover node_modules
Remove-Item -Recurse -Force node_modules

# Remover package-lock.json
Remove-Item package-lock.json
```

### PASSO 3: Instalar Dependências Novamente

```powershell
# Instalar com verbose para ver progresso
npm install --verbose

# Se ainda der erro, tentar com:
npm install --legacy-peer-deps
```

### PASSO 4: Verificar Espaço em Disco

```powershell
# Ver espaço disponível
Get-Volume

# Se ainda estiver cheio, considere:
# 1. Deletar arquivos desnecessários
# 2. Usar disco externo
# 3. Aumentar espaço em disco
```

---

## 📋 ARQUIVOS ATUALIZADOS

### ✅ Docker
- `docker-compose.yml` - Todos os containers com label `com.captar.stack=captar`

### ✅ Frontend - Nomes em Português
- `Permissoes.tsx` (era PermissionsPage.tsx)
- `Estatisticas.tsx` (era StatisticsPage.tsx)
- `Consultas.tsx` (era QueryPage.tsx)
- `Dashboard.tsx` (mantido como está)

### ✅ App.tsx
- Importações atualizadas com nomes em português
- Rotas atualizadas

---

## 🚀 APÓS RESOLVER O ERRO NPM

### 1. Copiar Arquivos

```bash
cd c:\www\Streamlit\Captar\CAPTAR

# Backend
cp Backend/FastAPI/main_extended.py Backend/FastAPI/main.py

# Frontend
cp Frontend/src/services/api_extended.ts Frontend/src/services/api.ts
```

### 2. Instalar Dependências Backend

```bash
pip install python-multipart openpyxl reportlab pandas
```

### 3. Build Frontend

```bash
cd Frontend
npm run build
cd ..
```

### 4. Deploy com Docker

```bash
# Limpar tudo
docker-compose down -v

# Build e iniciar
docker-compose up -d --build

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f
```

### 5. Verificar Migrations

```bash
# Aguarde 30 segundos, depois:
docker-compose logs migrations

# Deve exibir: "Migrations completed"
```

### 6. Testar

```bash
# Health check
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","senha":"123456"}'
```

---

## 📊 RESUMO DAS MUDANÇAS

| Item | Antes | Depois | Status |
|------|-------|--------|--------|
| Docker Stack | Sem label | Com label captar | ✅ |
| PermissionsPage.tsx | Inglês | Permissoes.tsx | ✅ |
| StatisticsPage.tsx | Inglês | Estatisticas.tsx | ✅ |
| QueryPage.tsx | Inglês | Consultas.tsx | ✅ |
| Dashboard | Mantido | Dashboard | ✅ |
| App.tsx | Antigos imports | Novos imports | ✅ |

---

## 🔍 VERIFICAR STACK CAPTAR

```bash
# Listar containers com label captar
docker ps --filter "label=com.captar.stack=captar"

# Resultado esperado:
# captar-postgres
# captar-mongodb
# captar-migrations
# captar-fastapi
# captar-nestjs
# captar-frontend
# captar-nginx
```

---

## ⚠️ SE AINDA TIVER PROBLEMAS

### Erro: "npm ERR! code ENOSPC"

```bash
# Aumentar limite de arquivos abertos (Linux/Mac)
ulimit -n 65536

# Windows: Considere usar SSD ou limpar mais espaço
```

### Erro: "Cannot find module"

```bash
# Limpar cache e reinstalar
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Erro: "EACCES: permission denied"

```bash
# Windows: Executar PowerShell como Administrador
# Linux/Mac: Usar sudo ou ajustar permissões
sudo chown -R $USER:$USER .
```

---

## 📝 PRÓXIMOS PASSOS

1. ✅ Resolver erro npm
2. ✅ Copiar arquivos estendidos
3. ✅ Instalar dependências
4. ✅ Build frontend
5. ✅ Deploy com Docker
6. ✅ Verificar migrations
7. ✅ Testar endpoints
8. ⏳ Implementar Prioridade 3

---

**Data**: 16/11/2025
**Status**: ✅ Pronto para Deploy
**Próxima Ação**: Resolver erro npm e fazer deploy
