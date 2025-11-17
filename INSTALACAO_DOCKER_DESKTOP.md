# 🐳 INSTALAÇÃO DO DOCKER DESKTOP

## ⚠️ PROBLEMA DETECTADO

Docker Desktop não está instalado ou não está no PATH do sistema.

---

## ✅ SOLUÇÃO: INSTALAR DOCKER DESKTOP

### PASSO 1: Download

1. Acesse: https://www.docker.com/products/docker-desktop
2. Clique em "Download for Windows"
3. Escolha a versão apropriada:
   - **Intel/AMD**: Docker Desktop for Windows
   - **ARM64**: Docker Desktop for Windows (ARM64)

### PASSO 2: Instalação

1. Execute o instalador `Docker Desktop Installer.exe`
2. Siga as instruções do assistente
3. Marque as opções:
   - ✅ Install required Windows components for WSL 2
   - ✅ Add Docker Compose
   - ✅ Add Docker to PATH

### PASSO 3: Configuração do WSL 2

Se solicitado:

```powershell
# Abrir PowerShell como Administrador

# Habilitar WSL 2
wsl --install

# Reiniciar o computador
```

### PASSO 4: Iniciar Docker Desktop

1. Procure por "Docker Desktop" no menu Iniciar
2. Clique para iniciar
3. Aguarde a inicialização (pode levar alguns minutos)
4. Verifique o ícone na bandeja do sistema

### PASSO 5: Verificar Instalação

```powershell
# Abrir PowerShell (novo terminal)

# Verificar Docker
docker --version

# Verificar Docker Compose
docker-compose --version

# Resultado esperado:
# Docker version 20.10.x, build xxxxx
# Docker Compose version 2.x.x, build xxxxx
```

---

## 🚀 APÓS INSTALAR DOCKER DESKTOP

Volte e execute os comandos de deploy:

```powershell
cd c:\www\Streamlit\Captar\CAPTAR

# 1. Parar containers antigos
docker-compose down -v

# 2. Build e iniciar
docker-compose up -d --build

# 3. Verificar migrations
docker-compose logs migrations

# 4. Verificar FastAPI
docker-compose logs fastapi

# 5. Testar health
curl http://localhost:8000/health

# 6. Acessar frontend
# Abra no navegador: http://localhost:3000
```

---

## 📋 REQUISITOS DO SISTEMA

- **Windows 10/11** (Pro, Enterprise ou Home com WSL 2)
- **Processador**: Compatível com virtualização
- **RAM**: Mínimo 4GB (recomendado 8GB+)
- **Disco**: Mínimo 5GB de espaço livre
- **WSL 2**: Habilitado no Windows

---

## ⚙️ CONFIGURAÇÃO RECOMENDADA

Após instalar, configure Docker Desktop:

1. Abra Docker Desktop
2. Clique em **Settings** (engrenagem)
3. Vá para **Resources**
4. Configure:
   - **CPUs**: 4 (ou mais)
   - **Memory**: 4GB (ou mais)
   - **Disk image size**: 50GB (ou mais)
5. Clique em **Apply & Restart**

---

## 🔍 TROUBLESHOOTING

### Erro: "Docker daemon is not running"

```powershell
# Iniciar Docker Desktop
# Ou reiniciar o computador
```

### Erro: "WSL 2 installation is incomplete"

```powershell
# Abrir PowerShell como Administrador
wsl --install
# Reiniciar computador
```

### Erro: "Cannot connect to Docker daemon"

```powershell
# Verificar se Docker Desktop está rodando
# Procure pelo ícone na bandeja do sistema
# Se não estiver, clique para iniciar
```

---

## 📞 SUPORTE

Se tiver problemas:

1. Consulte: https://docs.docker.com/desktop/install/windows-install/
2. Verifique requisitos do sistema
3. Tente reinstalar Docker Desktop
4. Reinicie o computador

---

## ✅ PRÓXIMOS PASSOS

Após instalar Docker Desktop:

1. ✅ Abra novo terminal PowerShell
2. ✅ Navegue para: `cd c:\www\Streamlit\Captar\CAPTAR`
3. ✅ Execute: `docker-compose down -v`
4. ✅ Execute: `docker-compose up -d --build`
5. ✅ Verifique: `docker-compose logs migrations`

---

**Data**: 16/11/2025
**Status**: ⏳ Aguardando instalação do Docker Desktop
**Próxima Ação**: Instalar Docker Desktop e executar deploy
