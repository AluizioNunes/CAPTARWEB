# Build stage
FROM node:24.11.0 AS builder

WORKDIR /app

# Copiar apenas os arquivos necessários para instalar as dependências
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Instalar dependências
RUN npm ci

# Copiar o restante dos arquivos
COPY . .

# Construir a aplicação
RUN npm run build

# Production stage
FROM nginx:alpine

# Copiar os arquivos de build para o nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar a configuração personalizada do nginx (se necessário)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expor a porta 80
EXPOSE 80

# Comando para iniciar o nginx
CMD ["nginx", "-g", "daemon off;"]
