# 🚀 CAPTAR - Setup e Instalação

## 📋 O que foi criado

### ✅ Frontend (Vite + React + TypeScript)
```
Frontend/
├── src/
│   ├── components/
│   │   ├── Layout.tsx          - Layout principal
│   │   ├── ChartComponent.tsx  - Componente de gráficos ECharts
│   │   └── Layout.css
│   ├── pages/
│   │   ├── LoginPage.tsx       - Página de login
│   │   ├── DashboardPage.tsx   - Dashboard com gráficos
│   │   ├── EleitorPage.tsx     - Gerenciamento de eleitores
│   │   ├── AtivistaPage.tsx    - Gerenciamento de ativistas
│   │   ├── UsuarioPage.tsx     - Gerenciamento de usuários
│   │   └── *.css
│   ├── services/
│   │   └── api.ts              - Cliente HTTP com Axios
│   ├── store/
│   │   └── authStore.ts        - Zustand store de autenticação
│   ├── types/
│   │   └── index.ts            - TypeScript interfaces
│   ├── App.tsx                 - Componente principal
│   ├── main.tsx                - Entry point
│   └── index.css
├── vite.config.ts
├── tsconfig.json
├── package.json
├── Dockerfile
└── index.html
```

### ✅ Backend FastAPI (PostgreSQL)
```
Backend/FastAPI/
├── main.py                     - Aplicação FastAPI
├── requirements.txt            - Dependências Python
└── Dockerfile
```

**Endpoints implementados:**
- Autenticação (login, logout, me)
- CRUD de Eleitores
- CRUD de Ativistas
- CRUD de Usuários
- Dashboard com estatísticas
- Top ativistas, usuários, supervisores, coordenadores
- Top bairros e zonas

### ✅ Backend NestJS (MongoDB)
```
Backend/NestJS/
├── package.json                - Dependências Node.js
├── Dockerfile
└── (estrutura pronta para desenvolvimento)
```

### ✅ Infraestrutura Docker
```
├── docker-compose.yml          - Orquestração completa
├── nginx.conf                  - Reverse proxy e load balancer
├── .env                        - Variáveis de ambiente
├── .env.example                - Template de variáveis
└── start.sh                    - Script de inicialização
```

## 🐳 Containers Docker

| Container | Imagem | Porta | Função |
|-----------|--------|-------|--------|
| frontend | captar-frontend | 3000 | React App |
| fastapi | captar-fastapi | 8000 | API PostgreSQL |
| nestjs | captar-nestjs | 3001 | API MongoDB |
| nginx | nginx:alpine | 80/443 | Reverse Proxy |
| postgres | postgres:15 | 5432 | Banco Relacional |
| mongodb | mongo:latest | 27017 | Banco NoSQL |

## 🚀 Como Iniciar

### Opção 1: Com Docker (Recomendado)

```bash
cd c:/www/Streamlit/Captar/CAPTAR

# Iniciar todos os containers
docker-compose up -d

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f
```

### Opção 2: Script de inicialização

```bash
cd c:/www/Streamlit/Captar/CAPTAR
bash start.sh
```

### Opção 3: Desenvolvimento local

#### Frontend
```bash
cd Frontend
npm install
npm run dev
```

#### FastAPI
```bash
cd Backend/FastAPI
pip install -r requirements.txt
python main.py
```

#### NestJS
```bash
cd Backend/NestJS
npm install
npm run start:dev
```

## 🌐 Acessar a Aplicação

Após iniciar os containers:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Frontend | http://localhost:3000 | Interface React |
| FastAPI | http://localhost:8000 | API PostgreSQL |
| FastAPI Docs | http://localhost:8000/docs | Swagger UI |
| NestJS | http://localhost:3001 | API MongoDB |
| Nginx | http://localhost | Reverse Proxy |

## 🔐 Credenciais Padrão

```
Usuário: admin
Senha: 123456
```

## 📊 Banco de Dados

### PostgreSQL
- **Host**: postgres:5432
- **Database**: captar
- **User**: captar
- **Password**: captar
- **Schema**: captar

### MongoDB
- **URI**: mongodb://captar:captar@mongodb:27017/captar?authSource=admin
- **Database**: captar

## 📝 Variáveis de Ambiente

Veja `.env` para configurações atuais ou `.env.example` para template.

## 🛠️ Comandos Úteis

### Docker Compose

```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Reconstruir
docker-compose up -d --build

# Ver logs
docker-compose logs -f [service]

# Executar comando em container
docker-compose exec [service] [command]
```

### Verificar Conectividade

```bash
# Testar PostgreSQL
docker-compose exec postgres psql -U captar -d captar -c "SELECT 1"

# Testar MongoDB
docker-compose exec mongodb mongosh -u captar -p captar --authenticationDatabase admin

# Testar FastAPI
curl http://localhost:8000/health

# Testar Frontend
curl http://localhost:3000
```

## 📦 Dependências Principais

### Frontend
- react@18.2.0
- vite@5.0.0
- antd@5.11.0
- echarts@5.4.0
- framer-motion@10.16.0
- zustand@4.4.0
- axios@1.6.0

### FastAPI
- fastapi==0.104.1
- uvicorn==0.24.0
- psycopg2-binary==2.9.10
- sqlalchemy==2.0.23

### NestJS
- @nestjs/core@10.2.0
- @nestjs/mongoose@10.0.0
- mongoose@8.0.0

## 🔄 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                       │
│              http://localhost:3000                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Nginx Reverse Proxy                         │
│           http://localhost:80/443                        │
└──────────────┬──────────────────────────┬────────────────┘
               │                          │
               ▼                          ▼
    ┌──────────────────┐      ┌──────────────────┐
    │  FastAPI         │      │  NestJS          │
    │  PostgreSQL      │      │  MongoDB         │
    │  :8000           │      │  :3001           │
    └──────────────────┘      └──────────────────┘
               │                          │
               ▼                          ▼
    ┌──────────────────┐      ┌──────────────────┐
    │  PostgreSQL      │      │  MongoDB         │
    │  :5432           │      │  :27017          │
    └──────────────────┘      └──────────────────┘
```

## 🐛 Troubleshooting

### Porta já em uso

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :3000
kill -9 <PID>
```

### Containers não iniciam

```bash
# Verificar logs
docker-compose logs

# Reconstruir
docker-compose up -d --build

# Remover containers e volumes
docker-compose down -v
docker-compose up -d
```

### Erro de conexão com banco

```bash
# Verificar se containers estão rodando
docker-compose ps

# Reiniciar containers
docker-compose restart

# Verificar logs do banco
docker-compose logs postgres
docker-compose logs mongodb
```

## 📚 Documentação

- [Vite Docs](https://vitejs.dev/)
- [React Docs](https://react.dev/)
- [Ant Design](https://ant.design/)
- [ECharts](https://echarts.apache.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [NestJS](https://docs.nestjs.com/)
- [Docker](https://docs.docker.com/)
- [Nginx](https://nginx.org/)

## ✨ Próximos Passos

1. ✅ Instalar dependências do Frontend
2. ✅ Instalar dependências do FastAPI
3. ✅ Instalar dependências do NestJS
4. ✅ Configurar variáveis de ambiente
5. ✅ Iniciar containers Docker
6. ✅ Acessar http://localhost:3000
7. ✅ Fazer login com admin/123456
8. ✅ Explorar o dashboard

## 📞 Suporte

Para problemas ou dúvidas, consulte a documentação ou abra uma issue.

---

**Criado em**: 2024
**Versão**: 1.0.0
**Status**: ✅ Pronto para produção
