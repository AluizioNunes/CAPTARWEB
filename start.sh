#!/bin/bash

# CAPTAR - Sistema de Gestão Eleitoral
# Script de inicialização

set -e

echo "🚀 Iniciando CAPTAR..."
echo ""

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Por favor, instale o Docker."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Por favor, instale o Docker Compose."
    exit 1
fi

echo "✅ Docker e Docker Compose encontrados"
echo ""

# Criar diretório SSL se não existir
if [ ! -d "ssl" ]; then
    echo "📁 Criando diretório SSL..."
    mkdir -p ssl
    
    # Gerar certificados auto-assinados
    echo "🔐 Gerando certificados SSL auto-assinados..."
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
        -subj "/C=BR/ST=State/L=City/O=CAPTAR/CN=localhost"
fi

echo "🐳 Iniciando containers..."
docker-compose up -d

echo ""
echo "⏳ Aguardando containers ficarem prontos..."
sleep 10

echo ""
echo "✅ CAPTAR iniciado com sucesso!"
echo ""
echo "📍 Acesse a aplicação em:"
echo "   Frontend:  http://localhost:3000"
echo "   FastAPI:   http://localhost:8000"
echo "   NestJS:    http://localhost:3001"
echo "   Nginx:     http://localhost:80"
echo ""
echo "🔐 Credenciais padrão:"
echo "   Usuário: admin"
echo "   Senha:   123456"
echo ""
echo "📊 Para ver os logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Para parar:"
echo "   docker-compose down"
echo ""
