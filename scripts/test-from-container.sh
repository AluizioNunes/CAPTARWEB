#!/bin/sh
# Script para testar os frontends a partir de dentro de um container
# Útil para executar no Portainer via exec

echo "========================================"
echo "Teste de Acesso aos Frontends (do Container)"
echo "========================================"
echo ""

# Testar conectividade interna da rede Docker
test_internal_url() {
    local url=$1
    local name=$2
    
    echo -n "   Testando $name... "
    echo "($url)"
    
    if command -v wget >/dev/null 2>&1; then
        if wget -q --spider --timeout=3 "$url" 2>/dev/null; then
            echo "   ✓ Acessível"
            return 0
        else
            echo "   ✗ Não acessível"
            return 1
        fi
    elif command -v curl >/dev/null 2>&1; then
        response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null)
        if [ "$response" != "000" ] && [ -n "$response" ]; then
            echo "   ✓ Status: $response"
            return 0
        else
            echo "   ✗ Não acessível"
            return 1
        fi
    else
        echo "   ⚠ wget/curl não disponível"
        return 2
    fi
}

echo "1. Testando serviços internos (rede Docker)..."
echo ""

# Testar CAPTAR Frontend (interno)
test_internal_url "http://frontend:80" "CAPTAR Frontend (interno)"
captar_internal=$?

# Testar FastAPI (interno)
test_internal_url "http://fastapi:8000/health" "FastAPI Health (interno)"
fastapi_internal=$?

# Testar Nginx (interno)
test_internal_url "http://nginx:80" "Nginx (interno)"
nginx_internal=$?

# Testar Evolution Frontend (interno)
test_internal_url "http://evolution_frontend:80" "Evolution Frontend (interno)"
evolution_internal=$?

# Testar Evolution API (interno)
test_internal_url "http://evolution_api:4000" "Evolution API (interno)"
evolution_api_internal=$?

echo ""
echo "2. Verificando resolução DNS..."
echo ""

for service in frontend fastapi nginx evolution_frontend evolution_api postgres redis; do
    if command -v nslookup >/dev/null 2>&1; then
        if nslookup "$service" >/dev/null 2>&1; then
            echo "   ✓ $service resolvido"
        else
            echo "   ✗ $service não resolvido"
        fi
    elif command -v getent >/dev/null 2>&1; then
        if getent hosts "$service" >/dev/null 2>&1; then
            echo "   ✓ $service resolvido"
        else
            echo "   ✗ $service não resolvido"
        fi
    else
        echo "   ⚠ Ferramentas de DNS não disponíveis"
        break
    fi
done

echo ""
echo "========================================"
echo "Resumo dos Testes Internos"
echo "========================================"
echo ""

services=(
    "CAPTAR Frontend:$captar_internal"
    "FastAPI:$fastapi_internal"
    "Nginx:$nginx_internal"
    "Evolution Frontend:$evolution_internal"
    "Evolution API:$evolution_api_internal"
)

all_ok=true
for service_info in "${services[@]}"; do
    service_name="${service_info%%:*}"
    service_result="${service_info##*:}"
    
    echo -n "   $service_name: "
    if [ "$service_result" -eq 0 ]; then
        echo "✓ OK"
    elif [ "$service_result" -eq 2 ]; then
        echo "⚠ SKIP (sem ferramentas)"
    else
        echo "✗ FALHOU"
        all_ok=false
    fi
done

echo ""

if [ "$all_ok" = true ]; then
    echo "✓ Todos os serviços internos estão acessíveis!"
    exit 0
else
    echo "✗ Alguns serviços não estão acessíveis internamente"
    exit 1
fi

