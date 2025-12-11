#!/bin/bash
# Script de teste para os frontends CAPTAR e Evolution
# Pode ser executado localmente ou no servidor onde os containers estão rodando

echo "========================================"
echo "Teste de Acesso aos Frontends"
echo "========================================"
echo ""

# Configurações das portas (padrões do docker-compose.yml)
FRONTEND_PORT=${FRONTEND_HOST_PORT:-5501}
EV_FRONTEND_PORT=${EV_FRONTEND_HOST_PORT:-4380}
NGINX_PORT=5500

# Verificar se os containers estão rodando
echo "1. Verificando status dos containers..."
echo ""

if ! command -v docker &> /dev/null; then
    echo "   ERRO: Docker não está instalado ou não está no PATH"
    exit 1
fi

containers=$(docker ps --format "{{.Names}}" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "   ERRO: Docker não está acessível ou não está rodando"
    echo "   Verifique se o Docker está instalado e rodando"
    exit 1
fi

captar_frontend=$(echo "$containers" | grep -q "captar-frontend" && echo "yes" || echo "no")
evolution_frontend=$(echo "$containers" | grep -q "evolution_frontend" && echo "yes" || echo "no")
nginx=$(echo "$containers" | grep -q "captar-nginx" && echo "yes" || echo "no")

echo -n "   CAPTAR Frontend: "
if [ "$captar_frontend" = "yes" ]; then
    echo "✓ Rodando"
else
    echo "✗ Não encontrado"
fi

echo -n "   Evolution Frontend: "
if [ "$evolution_frontend" = "yes" ]; then
    echo "✓ Rodando"
else
    echo "✗ Não encontrado"
fi

echo -n "   Nginx: "
if [ "$nginx" = "yes" ]; then
    echo "✓ Rodando"
else
    echo "✗ Não encontrado"
fi

echo ""
echo "2. Testando acesso HTTP aos frontends..."
echo ""

# Função para testar URL
test_url() {
    local url=$1
    local name=$2
    
    echo -n "   Testando $name... "
    echo "($url)"
    
    if command -v curl &> /dev/null; then
        response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
        if [ $? -eq 0 ] && [ "$response" != "000" ]; then
            echo "   ✓ Status: $response - OK"
            return 0
        else
            echo "   ✗ Erro ao conectar"
            return 1
        fi
    elif command -v wget &> /dev/null; then
        if wget -q --spider --timeout=5 "$url" 2>/dev/null; then
            echo "   ✓ Acessível"
            return 0
        else
            echo "   ✗ Erro ao conectar"
            return 1
        fi
    else
        echo "   ⚠ curl ou wget não encontrado, pulando teste HTTP"
        return 2
    fi
}

# Testar CAPTAR Frontend direto
echo "   --- CAPTAR Frontend (Porta $FRONTEND_PORT) ---"
test_url "http://localhost:$FRONTEND_PORT" "CAPTAR Frontend Direto"
captar_direct=$?

echo ""

# Testar CAPTAR via Nginx
echo "   --- CAPTAR via Nginx (Porta $NGINX_PORT) ---"
test_url "http://localhost:$NGINX_PORT" "CAPTAR via Nginx"
captar_nginx=$?

echo ""

# Testar Evolution Frontend
echo "   --- Evolution Frontend (Porta $EV_FRONTEND_PORT) ---"
test_url "http://localhost:$EV_FRONTEND_PORT" "Evolution Frontend"
evolution_direct=$?

echo ""
echo "3. Verificando endpoints de API..."
echo ""

# Testar API do FastAPI
echo "   --- FastAPI Health Check ---"
if command -v curl &> /dev/null; then
    fastapi_response=$(curl -s --max-time 5 "http://localhost:$NGINX_PORT/api/health" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$fastapi_response" ]; then
        echo "   ✓ FastAPI Health: OK"
        echo "   ✓ Resposta: $fastapi_response"
    else
        echo "   ✗ FastAPI não está respondendo"
    fi
else
    echo "   ⚠ curl não encontrado, pulando teste de API"
fi

echo ""

# Testar Evolution API
echo "   --- Evolution API ---"
if command -v curl &> /dev/null; then
    evolution_api_response=$(curl -s --max-time 5 "http://localhost:$EV_FRONTEND_PORT/api/health" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "   ✓ Evolution API: OK"
    else
        echo "   ✗ Evolution API não está respondendo"
    fi
else
    echo "   ⚠ curl não encontrado, pulando teste de API"
fi

echo ""
echo "4. Verificando logs dos containers..."
echo ""

# Verificar logs do Evolution Frontend (onde estava o erro)
echo "   --- Últimas linhas do Evolution Frontend ---"
evolution_logs=$(docker logs evolution_frontend --tail 20 2>&1)
if echo "$evolution_logs" | grep -qiE "error|emerg|invalid"; then
    echo "   ⚠ AVISOS/ERROS encontrados:"
    echo "$evolution_logs" | grep -iE "error|emerg|invalid" | while read -r line; do
        echo "   $line"
    done
else
    echo "   ✓ Sem erros críticos nos últimos logs"
fi

echo ""
echo "========================================"
echo "Resumo dos Testes"
echo "========================================"
echo ""

echo -n "   CAPTAR Frontend (Direto): "
if [ $captar_direct -eq 0 ]; then
    echo "✓ PASSOU"
else
    echo "✗ FALHOU"
fi

echo -n "   CAPTAR via Nginx: "
if [ $captar_nginx -eq 0 ]; then
    echo "✓ PASSOU"
else
    echo "✗ FALHOU"
fi

echo -n "   Evolution Frontend: "
if [ $evolution_direct -eq 0 ]; then
    echo "✓ PASSOU"
else
    echo "✗ FALHOU"
fi

echo ""

if [ $captar_direct -eq 0 ] && [ $captar_nginx -eq 0 ] && [ $evolution_direct -eq 0 ]; then
    echo "✓ Todos os testes passaram!"
    exit 0
else
    echo "✗ Alguns testes falharam. Verifique os logs acima."
    exit 1
fi

