# CAPTAR - Sistema de Gestão Eleitoral

Uma plataforma moderna de gestão eleitoral construída com tecnologias de ponta.

## 🏗️ Arquitetura

### Frontend
- **Vite** - Build tool rápido e moderno
- **React 18** - UI library
- **TypeScript** - Type safety
- **Ant Design** - Component library
- **Framer Motion** - Animações
- **ECharts** - Gráficos avançados
- **Zustand** - State management

### Backend - FastAPI (PostgreSQL)
- **FastAPI** - Framework web rápido
- **PostgreSQL** - Banco de dados relacional
- **SQLAlchemy** - ORM
- **Pydantic** - Validação de dados

### Backend - NestJS (MongoDB)
- **NestJS** - Framework Node.js
- **MongoDB** - Banco de dados NoSQL
- **Mongoose** - ODM
- **JWT** - Autenticação

### Infraestrutura
- **Docker** - Containerização
- **Docker Compose** - Orquestração
- **Nginx** - Reverse proxy e load balancer

## 📋 Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (para desenvolvimento local)
- Python 3.11+ (para desenvolvimento local)

## 🚀 Início Rápido

### 1. Clone o repositório

```bash
cd c:/www/Streamlit/Captar/CAPTAR
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

### 3. Inicie os containers

```bash
docker-compose up -d
```

### 4. Acesse a aplicação

- **Frontend**: http://localhost:3000
- **FastAPI**: http://localhost:8000
- **NestJS**: http://localhost:3001
- **Nginx**: http://localhost:80

## 📁 Estrutura do Projeto

```
CAPTAR/
├── Frontend/                 # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/      # Componentes reutilizáveis
│   │   ├── pages/           # Páginas da aplicação
│   │   ├── services/        # Serviços de API
│   │   ├── store/           # Zustand stores
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utilitários
│   ├── Dockerfile
│   └── package.json
│
├── Backend/
│   ├── FastAPI/             # FastAPI + PostgreSQL
│   │   ├── main.py          # Aplicação principal
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── NestJS/              # NestJS + MongoDB
│       ├── src/
│       ├── package.json
│       └── Dockerfile
│
├── docker-compose.yml       # Orquestração de containers
├── nginx.conf              # Configuração do Nginx
└── .env.example            # Variáveis de ambiente
```

## 🔐 Autenticação

### Credenciais Padrão

- **Usuário**: admin
- **Senha**: 123456

## 📊 Endpoints da API

### FastAPI (PostgreSQL)

```
POST   /api/auth/login              - Login
GET    /api/auth/me                 - Usuário atual
POST   /api/auth/logout             - Logout

GET    /api/eleitores               - Listar eleitores
POST   /api/eleitores               - Criar eleitor
GET    /api/eleitores/{id}          - Obter eleitor
PUT    /api/eleitores/{id}          - Atualizar eleitor
DELETE /api/eleitores/{id}          - Deletar eleitor

GET    /api/ativistas               - Listar ativistas
GET    /api/usuarios                - Listar usuários
GET    /api/funcoes                 - Listar funções
GET    /api/bairros                 - Listar bairros
GET    /api/zonas                   - Listar zonas

GET    /api/dashboard/stats         - Estatísticas
GET    /api/dashboard/top-ativistas - Top ativistas
GET    /api/dashboard/top-usuarios  - Top usuários
GET    /api/dashboard/top-supervisores - Top supervisores
GET    /api/dashboard/top-coordenadores - Top coordenadores
GET    /api/dashboard/top-bairros   - Top bairros
GET    /api/dashboard/top-zonas     - Top zonas
```

## 🐳 Comandos Docker

### Iniciar containers

```bash
docker-compose up -d
```

### Parar containers

```bash
docker-compose down
```

### Ver logs

```bash
docker-compose logs -f [service]
```

### Reconstruir containers

```bash
docker-compose up -d --build
```

### Remover volumes

```bash
docker-compose down -v
```

## 🛠️ Desenvolvimento Local

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

### FastAPI

```bash
cd Backend/FastAPI
pip install -r requirements.txt
python main.py
```

### NestJS

```bash
cd Backend/NestJS
npm install
npm run start:dev
```

## 📦 Nomes das Imagens Docker

- `captar-frontend:latest` - Frontend React
- `captar-fastapi:latest` - Backend FastAPI
- `captar-nestjs:latest` - Backend NestJS
- `captar-nginx:latest` - Nginx Reverse Proxy
- `captar-postgres:latest` - PostgreSQL
- `captar-mongodb:latest` - MongoDB

## 🔄 Fluxo de Dados

```
Frontend (React)
    ↓
Nginx (Reverse Proxy)
    ├→ FastAPI (PostgreSQL) - Dados relacionais
    └→ NestJS (MongoDB) - Dados não-relacionais
```

## 📝 Variáveis de Ambiente

Veja `.env.example` para todas as variáveis disponíveis.

## 🚨 Troubleshooting

### Porta já em uso

```bash
# Encontrar processo usando a porta
lsof -i :3000

# Matar processo
kill -9 <PID>
```

### Containers não iniciam

```bash
# Verificar logs
docker-compose logs

# Reconstruir
docker-compose up -d --build
```

### Erro de conexão com banco de dados

```bash
# Verificar se containers estão rodando
docker-compose ps

# Reiniciar containers
docker-compose restart
```

## 📚 Documentação

- [Vite](https://vitejs.dev/)
- [React](https://react.dev/)
- [Ant Design](https://ant.design/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [NestJS](https://docs.nestjs.com/)
- [Docker](https://docs.docker.com/)

## 📄 Licença

MIT

## 👥 Autores

CAPTAR Team

## 📞 Suporte

Para suporte, abra uma issue no repositório.
