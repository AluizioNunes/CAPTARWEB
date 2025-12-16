# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar apenas os arquivos necessários para instalar as dependências
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
ENV CI=true
ENV NODE_OPTIONS=--max-old-space-size=1024

# Instalar dependências
RUN npm config set fund false && npm config set audit false && npm ci --no-audit --no-fund

# Copiar o restante dos arquivos
COPY . .

# Construir a aplicação
RUN npm run build

# Production stage
FROM nginx:alpine

# Copiar os arquivos de build para o nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar a configuração personalizada do nginx
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf

# Expor a porta 80
EXPOSE 80

# Comando para iniciar o nginx
CMD ["nginx", "-g", "daemon off;"]
