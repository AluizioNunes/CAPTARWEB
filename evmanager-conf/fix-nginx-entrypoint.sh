#!/bin/sh
# Script para corrigir configuração do nginx no Evolution Frontend

# Criar diretório se não existir
mkdir -p /etc/nginx/conf.d

# Função para corrigir arquivo
fix_nginx_file() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return 0
    fi
    
    # Criar arquivo temporário
    local tmp_file="${file}.tmp"
    
    # Tentar sed com arquivo temporário
    if sed \
        -e 's/expires[[:space:]]*must-revalidate[[:space:]]*;/expires off;/g' \
        -e 's/expires[[:space:]]*must-revalidate$/expires off;/g' \
        -e 's/expires[[:space:]]*must-revalidate/expires off/g' \
        "$file" > "$tmp_file" 2>/dev/null; then
        mv "$tmp_file" "$file" 2>/dev/null || cp "$tmp_file" "$file" 2>/dev/null || true
        rm -f "$tmp_file" 2>/dev/null || true
    fi
    
    # Verificar se ainda tem o problema
    if grep -q "expires.*must-revalidate" "$file" 2>/dev/null; then
        # Se ainda tiver, remover a linha completamente
        sed '/expires.*must-revalidate/d' "$file" > "$tmp_file" 2>/dev/null && mv "$tmp_file" "$file" 2>/dev/null || true
        rm -f "$tmp_file" 2>/dev/null || true
        
        # Adicionar expires off se não existir
        if ! grep -q "expires off" "$file" 2>/dev/null; then
            sed '/server_name/a\        expires off;' "$file" > "$tmp_file" 2>/dev/null && mv "$tmp_file" "$file" 2>/dev/null || true
            rm -f "$tmp_file" 2>/dev/null || true
        fi
    fi
}

# Corrigir arquivo problemático
if [ -f /etc/nginx/conf.d/nginx.conf ]; then
    fix_nginx_file /etc/nginx/conf.d/nginx.conf
    
    # Se ainda houver problema após todas as tentativas, substituir completamente
    if grep -q "expires.*must-revalidate" /etc/nginx/conf.d/nginx.conf 2>/dev/null; then
        # Usar nosso arquivo customizado se disponível
        if [ -f /opt/conf/default.conf ]; then
            cp /opt/conf/default.conf /etc/nginx/conf.d/nginx.conf 2>/dev/null || true
        else
            # Criar um arquivo mínimo válido
            cat > /etc/nginx/conf.d/nginx.conf << 'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    expires off;
    location / {
        try_files $uri $uri/ /index.html;
    }
    location ^~ /api/ {
        proxy_pass http://evolution_api:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
        fi
    fi
fi

# Também verificar nginx.conf principal
if [ -f /etc/nginx/nginx.conf ]; then
    fix_nginx_file /etc/nginx/nginx.conf
fi

# Verificar configuração antes de iniciar
if ! nginx -t 2>/dev/null; then
    echo "Aviso: Configuração do nginx pode ter problemas, mas tentando iniciar mesmo assim..."
fi

# Iniciar nginx
exec nginx -g 'daemon off;'

