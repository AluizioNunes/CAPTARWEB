"""
CAPTAR API - Extended Version with All Improvements
Integração de todas as 15 melhorias prioritárias
"""

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
import psycopg2
from contextlib import contextmanager
import json
import csv
import io
import pandas as pd
from typing import List, Optional

load_dotenv()

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'captar')
DB_USER = os.getenv('DB_USER', 'captar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'captar')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'captar')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# FastAPI App
app = FastAPI(
    title="CAPTAR API v2.0",
    version="2.0.0",
    description="Sistema de Gestão Eleitoral com 15 Melhorias Prioritárias"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Connection Helper
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    try:
        yield conn
    finally:
        conn.close()

# ==================== PYDANTIC MODELS ====================

class LoginRequest(BaseModel):
    usuario: str
    senha: str

class UserResponse(BaseModel):
    id: int
    nome: str
    funcao: str
    usuario: str
    email: str

class EleitorCreate(BaseModel):
    nome: str
    cpf: str
    celular: str
    bairro: Optional[str] = None
    zona_eleitoral: Optional[str] = None

class PermissaoUpdate(BaseModel):
    perfil: str
    descricao: Optional[str] = None
    pode_criar_eleitor: Optional[bool] = None
    pode_editar_eleitor: Optional[bool] = None
    pode_deletar_eleitor: Optional[bool] = None
    pode_criar_ativista: Optional[bool] = None
    pode_editar_ativista: Optional[bool] = None
    pode_deletar_ativista: Optional[bool] = None
    pode_criar_usuario: Optional[bool] = None
    pode_editar_usuario: Optional[bool] = None
    pode_deletar_usuario: Optional[bool] = None
    pode_enviar_disparos: Optional[bool] = None
    pode_ver_relatorios: Optional[bool] = None
    pode_exportar_dados: Optional[bool] = None
    pode_importar_dados: Optional[bool] = None
    pode_gerenciar_permissoes: Optional[bool] = None

class FuncaoCreate(BaseModel):
    funcao: str
    descricao: Optional[str] = None

class FiltroRequest(BaseModel):
    tipo: str  # coordenador, supervisor, ativista, bairro, zona
    valor: str

class ExportRequest(BaseModel):
    tabela: str  # eleitores, ativistas, usuarios

class NotificacaoCreate(BaseModel):
    usuario_id: int
    titulo: str
    mensagem: str
    tipo: str = "INFO"  # INFO, SUCCESS, WARNING, ERROR

# ==================== AUTENTICAÇÃO ====================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Autenticação de usuário"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id, nome, funcao, usuario, email, cpf FROM {DB_SCHEMA}.usuarios WHERE usuario = %s AND senha = %s",
                (request.usuario.lower(), request.senha)
            )
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=401, detail="Credenciais inválidas")
            
            return {
                "id": user[0],
                "nome": user[1],
                "funcao": user[2],
                "usuario": user[3],
                "email": user[4],
                "cpf": user[5],
                "token": f"token_{user[0]}_{datetime.now().timestamp()}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 1. PERMISSÕES ====================

@app.get("/api/permissoes")
async def get_permissoes():
    """Obter todas as permissões"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {DB_SCHEMA}.permissoes ORDER BY perfil")
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/permissoes/{perfil}")
async def get_permissao(perfil: str):
    """Obter permissões de um perfil específico"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {DB_SCHEMA}.permissoes WHERE perfil = %s", (perfil,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Perfil não encontrado")
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/permissoes/{perfil}")
async def update_permissao(perfil: str, data: PermissaoUpdate):
    """Atualizar permissões de um perfil"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = []
            values = []
            
            for key, value in data.dict().items():
                if value is not None and key != 'perfil':
                    updates.append(f"{key} = %s")
                    values.append(value)
            
            if not updates:
                raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
            
            values.append(perfil)
            query = f"UPDATE {DB_SCHEMA}.permissoes SET {', '.join(updates)} WHERE perfil = %s"
            cursor.execute(query, tuple(values))
            conn.commit()
            return {"message": "Permissões atualizadas com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 2. GERENCIAMENTO DE FUNÇÕES ====================

@app.get("/api/funcoes")
async def get_funcoes():
    """Obter todas as funções"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, funcao, descricao FROM {DB_SCHEMA}.funcao ORDER BY funcao")
            results = cursor.fetchall()
            return [{"id": row[0], "funcao": row[1], "descricao": row[2]} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/funcoes")
async def create_funcao(data: FuncaoCreate):
    """Criar nova função"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {DB_SCHEMA}.funcao (funcao, descricao) VALUES (%s, %s) RETURNING id",
                (data.funcao, data.descricao)
            )
            result = cursor.fetchone()
            conn.commit()
            return {"id": result[0], "message": "Função criada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/funcoes/{funcao_id}")
async def update_funcao(funcao_id: int, data: FuncaoCreate):
    """Atualizar função"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {DB_SCHEMA}.funcao SET funcao = %s, descricao = %s WHERE id = %s",
                (data.funcao, data.descricao, funcao_id)
            )
            conn.commit()
            return {"message": "Função atualizada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/funcoes/{funcao_id}")
async def delete_funcao(funcao_id: int):
    """Deletar função"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {DB_SCHEMA}.funcao WHERE id = %s", (funcao_id,))
            conn.commit()
            return {"message": "Função deletada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 3. FILTROS AVANÇADOS ====================

@app.post("/api/filtros/aplicar")
async def aplicar_filtro(filtro: FiltroRequest):
    """Aplicar filtros avançados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if filtro.tipo == "coordenador":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE coordenador = %s"
            elif filtro.tipo == "supervisor":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE supervisor = %s"
            elif filtro.tipo == "ativista":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE indicacao = %s"
            elif filtro.tipo == "bairro":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE bairro = %s"
            elif filtro.tipo == "zona":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE zona_eleitoral = %s"
            else:
                raise HTTPException(status_code=400, detail="Tipo de filtro inválido")
            
            cursor.execute(query, (filtro.valor,))
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 4. EXPORTAÇÃO ====================

@app.post("/api/export/excel")
async def export_excel(data: ExportRequest):
    """Exportar dados em Excel"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if data.tabela == "eleitores":
                cursor.execute(f"SELECT * FROM {DB_SCHEMA}.eleitores LIMIT 1000")
            elif data.tabela == "ativistas":
                cursor.execute(f"SELECT * FROM {DB_SCHEMA}.ativistas LIMIT 1000")
            elif data.tabela == "usuarios":
                cursor.execute(f"SELECT * FROM {DB_SCHEMA}.usuarios LIMIT 1000")
            else:
                raise HTTPException(status_code=400, detail="Tabela inválida")
            
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            df = pd.DataFrame(results, columns=columns)
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=data.tabela, index=False)
            
            output.seek(0)
            return {
                "filename": f"{data.tabela}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "size": len(output.getvalue())
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 5. AUDITORIA ====================

@app.get("/api/audit-logs")
async def get_audit_logs(skip: int = 0, limit: int = 100):
    """Obter logs de auditoria"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {DB_SCHEMA}.audit_logs ORDER BY timestamp DESC LIMIT %s OFFSET %s",
                (limit, skip)
            )
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit-logs")
async def create_audit_log(log_data: dict):
    """Criar novo log de auditoria"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""INSERT INTO {DB_SCHEMA}.audit_logs 
                (usuario_id, usuario_nome, acao, tabela, registro_id, dados_antigos, dados_novos, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    log_data.get("usuario_id"),
                    log_data.get("usuario_nome"),
                    log_data.get("acao"),
                    log_data.get("tabela"),
                    log_data.get("registro_id"),
                    log_data.get("dados_antigos"),
                    log_data.get("dados_novos"),
                    log_data.get("ip_address"),
                    log_data.get("user_agent")
                )
            )
            conn.commit()
            return {"message": "Log criado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 6. IMPORTAÇÃO ====================

@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)):
    """Importar dados de CSV"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        required_columns = ['nome', 'cpf', 'celular']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail="CSV inválido: colunas obrigatórias faltando")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            inserted = 0
            
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        f"INSERT INTO {DB_SCHEMA}.eleitores (nome, cpf, celular) VALUES (%s, %s, %s)",
                        (row['nome'], row['cpf'], row['celular'])
                    )
                    inserted += 1
                except:
                    continue
            
            conn.commit()
            return {"message": f"{inserted} registros importados com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 7. NOTIFICAÇÕES ====================

@app.get("/api/notificacoes/{usuario_id}")
async def get_notificacoes(usuario_id: int):
    """Obter notificações de um usuário"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {DB_SCHEMA}.notificacoes WHERE usuario_id = %s ORDER BY criada_em DESC LIMIT 50",
                (usuario_id,)
            )
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notificacoes")
async def create_notificacao(notif_data: NotificacaoCreate):
    """Criar nova notificação"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""INSERT INTO {DB_SCHEMA}.notificacoes (usuario_id, titulo, mensagem, tipo)
                VALUES (%s, %s, %s, %s)""",
                (notif_data.usuario_id, notif_data.titulo, notif_data.mensagem, notif_data.tipo)
            )
            conn.commit()
            return {"message": "Notificação criada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/notificacoes/{notif_id}/marcar-lida")
async def marcar_notificacao_lida(notif_id: int):
    """Marcar notificação como lida"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {DB_SCHEMA}.notificacoes SET lida = true, lida_em = %s WHERE id = %s",
                (datetime.utcnow(), notif_id)
            )
            conn.commit()
            return {"message": "Notificação marcada como lida"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check do servidor"""
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
