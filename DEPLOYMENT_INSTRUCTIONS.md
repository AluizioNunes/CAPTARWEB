# 🚀 INSTRUÇÕES DE DEPLOYMENT - CAPTAR v2.0

## 📋 PRÉ-REQUISITOS

- Docker 20.10+
- Docker Compose 2.0+
- Git
- 4GB RAM mínimo
- 10GB espaço em disco

## 🔧 INSTALAÇÃO PASSO A PASSO

### PASSO 1: Preparar Arquivos

```bash
cd c:/www/Streamlit/Captar/CAPTAR

# Copiar arquivos estendidos
cp Backend/FastAPI/main_extended.py Backend/FastAPI/main.py
cp Frontend/src/services/api_extended.ts Frontend/src/services/api.ts
```

### PASSO 2: Atualizar Dependências

```bash
# Backend
pip install python-multipart openpyxl reportlab pandas

# Frontend
cd Frontend
npm install
cd ..
```

### PASSO 3: Verificar Arquivo .env

```bash
# Verificar se .env existe e tem as variáveis corretas
cat .env

# Deve conter:
# DB_HOST=postgres
# DB_PORT=5432
# DB_NAME=captar
# DB_USER=captar
# DB_PASSWORD=captar
# DB_SCHEMA=captar
```

### PASSO 4: Limpar Containers Antigos

```bash
# Parar e remover containers antigos
docker-compose down -v

# Remover volumes (CUIDADO: isso deleta dados!)
docker volume prune -f
```

### PASSO 5: Build e Deploy

```bash
# Build das imagens
docker-compose build

# Iniciar containers
docker-compose up -d

# Verificar status
docker-compose ps
```

### PASSO 6: Verificar Migrations

```bash
# Ver logs das migrations
docker-compose logs migrations

# Deve exibir: "Migrations completed"

# Ver logs do FastAPI
docker-compose logs fastapi

# Deve exibir: "Application startup complete"
```

## ✅ VALIDAÇÃO

### Health Checks

```bash
# FastAPI Health
curl http://localhost:8000/health
# Resposta esperada: {"status":"ok","version":"2.0.0"}

# Frontend
curl http://localhost:3000
# Deve retornar HTML da aplicação

# Nginx
curl http://localhost:80
# Deve redirecionar para frontend
```

### Testes de Endpoints

```bash
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","senha":"123456"}'

# Resposta esperada: token e dados do usuário

# 2. Permissões
curl http://localhost:8000/api/permissoes

# Resposta esperada: array com 4 permissões

# 3. Funções
curl http://localhost:8000/api/funcoes

# Resposta esperada: array com funções

# 4. Filtros
curl -X POST http://localhost:8000/api/filtros/aplicar \
  -H "Content-Type: application/json" \
  -d '{"tipo":"bairro","valor":"CENTRO"}'

# Resposta esperada: array com eleitores

# 5. Auditoria
curl http://localhost:8000/api/audit-logs

# Resposta esperada: array com logs
```

### Testes do Frontend

1. Abrir http://localhost:3000
2. Fazer login com admin/123456
3. Verificar se dashboard carrega
4. Clicar em "Permissões" (nova página)
5. Clicar em "Estatísticas" (nova página)
6. Clicar em "Consultas" (nova página)

## 🐛 TROUBLESHOOTING

### Problema: Migrations não rodaram

```bash
# Ver logs detalhados
docker-compose logs migrations

# Reexecutar migrations manualmente
docker-compose exec postgres psql -U captar -d captar -f /migrations.sql
```

### Problema: FastAPI não conecta ao banco

```bash
# Verificar conexão PostgreSQL
docker-compose exec postgres psql -U captar -d captar -c "SELECT 1"

# Ver logs do FastAPI
docker-compose logs fastapi

# Reiniciar FastAPI
docker-compose restart fastapi
```

### Problema: Frontend não carrega

```bash
# Verificar logs do frontend
docker-compose logs frontend

# Limpar cache
docker-compose exec frontend rm -rf node_modules/.cache

# Reconstruir
docker-compose up -d --build frontend
```

### Problema: Porta já em uso

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :3000
kill -9 <PID>
```

## 📊 MONITORAMENTO

### Ver Logs em Tempo Real

```bash
# Todos os containers
docker-compose logs -f

# Container específico
docker-compose logs -f fastapi
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Verificar Uso de Recursos

```bash
# CPU e memória
docker stats

# Espaço em disco
docker system df
```

### Acessar Banco de Dados

```bash
# PostgreSQL
docker-compose exec postgres psql -U captar -d captar

# Listar tabelas
\dt captar.*

# Sair
\q

# MongoDB
docker-compose exec mongodb mongosh -u captar -p captar --authenticationDatabase admin
```

## 🔄 ATUALIZAÇÕES

### Atualizar Código

```bash
# Parar containers
docker-compose down

# Atualizar código
git pull

# Reconstruir
docker-compose up -d --build

# Verificar migrations
docker-compose logs migrations
```

### Backup do Banco de Dados

```bash
# PostgreSQL
docker-compose exec postgres pg_dump -U captar captar > backup.sql

# MongoDB
docker-compose exec mongodb mongodump --username captar --password captar --authenticationDatabase admin --out /backup
```

### Restaurar Banco de Dados

```bash
# PostgreSQL
docker-compose exec -T postgres psql -U captar captar < backup.sql

# MongoDB
docker-compose exec mongodb mongorestore --username captar --password captar --authenticationDatabase admin /backup
```

## 🛑 PARAR E REMOVER

### Parar Containers

```bash
# Parar (mantém dados)
docker-compose stop

# Parar e remover (remove dados)
docker-compose down

# Parar e remover tudo (remove volumes também)
docker-compose down -v
```

## 📝 CHECKLIST DE DEPLOYMENT

- [ ] Pré-requisitos instalados
- [ ] Arquivos copiados (main_extended.py, api_extended.ts)
- [ ] Dependências instaladas
- [ ] .env verificado
- [ ] Containers antigos removidos
- [ ] Build executado com sucesso
- [ ] Containers iniciados
- [ ] Migrations completadas
- [ ] Health checks passaram
- [ ] Endpoints testados
- [ ] Frontend carrega
- [ ] Login funciona
- [ ] Novas páginas acessíveis
- [ ] Banco de dados conectado
- [ ] Logs monitorados

## 🎯 PRÓXIMOS PASSOS

1. **Testes Completos** (1-2 dias)
   - Testar todos os endpoints
   - Testar todas as páginas
   - Testar fluxos de usuário

2. **Otimizações** (1 semana)
   - Cache com Redis
   - Índices de banco de dados
   - Compressão de imagens

3. **Segurança** (1 semana)
   - 2FA
   - Criptografia de dados
   - Rate limiting

4. **Prioridade 3** (2-3 semanas)
   - Resultados Eleitorais
   - Mapa Interativo
   - Relatórios Agendados
   - WhatsApp Integration
   - Dashboard Executivo

## 📞 SUPORTE

Para problemas:
1. Verificar logs: `docker-compose logs`
2. Consultar TROUBLESHOOTING acima
3. Verificar documentação em IMPLEMENTACAO_FASE_POR_FASE.md
4. Consultar RESUMO_IMPLEMENTACAO_FINAL.txt

## 📄 DOCUMENTAÇÃO

- README.md - Documentação geral
- SETUP.md - Guia de setup
- IMPLEMENTACAO_FASE_POR_FASE.md - Detalhes técnicos
- RESUMO_IMPLEMENTACAO_FINAL.txt - Resumo executivo
- DEPLOYMENT_INSTRUCTIONS.md - Este arquivo

---

**Data**: 16/11/2025
**Versão**: 2.0
**Status**: ✅ Pronto para Deploy
