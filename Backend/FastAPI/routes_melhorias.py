from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import json
import csv
import io
from typing import List
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

router = APIRouter(prefix="/api", tags=["melhorias"])

# ==================== 1. PERMISSÕES ====================

@router.get("/permissoes")
async def get_permissoes(db: Session = Depends(get_db)):
    """Obter todas as permissões"""
    try:
        query = "SELECT * FROM captar.permissoes ORDER BY perfil"
        db.execute(query)
        results = db.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/permissoes/{perfil}")
async def get_permissao(perfil: str, db: Session = Depends(get_db)):
    """Obter permissões de um perfil específico"""
    try:
        query = "SELECT * FROM captar.permissoes WHERE perfil = %s"
        db.execute(query, (perfil,))
        result = db.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Perfil não encontrado")
        return dict(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/permissoes/{perfil}")
async def update_permissao(perfil: str, data: dict, db: Session = Depends(get_db)):
    """Atualizar permissões de um perfil"""
    try:
        # Construir query dinamicamente
        updates = []
        values = []
        for key, value in data.items():
            if key != 'perfil':
                updates.append(f"{key} = %s")
                values.append(value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        values.append(perfil)
        query = f"UPDATE captar.permissoes SET {', '.join(updates)} WHERE perfil = %s"
        db.execute(query, tuple(values))
        db.commit()
        return {"message": "Permissões atualizadas com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 2. GERENCIAMENTO DE FUNÇÕES ====================

@router.get("/funcoes")
async def get_funcoes(db: Session = Depends(get_db)):
    """Obter todas as funções"""
    try:
        query = "SELECT * FROM captar.funcao ORDER BY funcao"
        db.execute(query)
        results = db.fetchall()
        return [{"id": row[0], "funcao": row[1], "descricao": row[2]} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/funcoes")
async def create_funcao(data: dict, db: Session = Depends(get_db)):
    """Criar nova função"""
    try:
        query = "INSERT INTO captar.funcao (funcao, descricao) VALUES (%s, %s) RETURNING id"
        db.execute(query, (data.get("funcao"), data.get("descricao")))
        result = db.fetchone()
        return {"id": result[0], "message": "Função criada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/funcoes/{funcao_id}")
async def update_funcao(funcao_id: int, data: dict, db: Session = Depends(get_db)):
    """Atualizar função"""
    try:
        query = "UPDATE captar.funcao SET funcao = %s, descricao = %s WHERE id = %s"
        db.execute(query, (data.get("funcao"), data.get("descricao"), funcao_id))
        db.commit()
        return {"message": "Função atualizada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/funcoes/{funcao_id}")
async def delete_funcao(funcao_id: int, db: Session = Depends(get_db)):
    """Deletar função"""
    try:
        query = "DELETE FROM captar.funcao WHERE id = %s"
        db.execute(query, (funcao_id,))
        db.commit()
        return {"message": "Função deletada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 3. FILTROS AVANÇADOS ====================

@router.post("/filtros/aplicar")
async def aplicar_filtro(filtro: dict, db: Session = Depends(get_db)):
    """Aplicar filtros avançados"""
    try:
        filtro_tipo = filtro.get("tipo")  # coordenador, supervisor, ativista, bairro, zona
        filtro_valor = filtro.get("valor")
        
        if filtro_tipo == "coordenador":
            query = "SELECT * FROM captar.eleitores WHERE coordenador = %s"
        elif filtro_tipo == "supervisor":
            query = "SELECT * FROM captar.eleitores WHERE supervisor = %s"
        elif filtro_tipo == "ativista":
            query = "SELECT * FROM captar.eleitores WHERE indicacao = %s"
        elif filtro_tipo == "bairro":
            query = "SELECT * FROM captar.eleitores WHERE bairro = %s"
        elif filtro_tipo == "zona":
            query = "SELECT * FROM captar.eleitores WHERE zona_eleitoral = %s"
        else:
            raise HTTPException(status_code=400, detail="Tipo de filtro inválido")
        
        db.execute(query, (filtro_valor,))
        results = db.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 4. EXPORTAÇÃO PDF/EXCEL ====================

@router.post("/export/excel")
async def export_excel(data: dict, db: Session = Depends(get_db)):
    """Exportar dados em Excel"""
    try:
        tabela = data.get("tabela")  # eleitores, ativistas, usuarios
        
        if tabela == "eleitores":
            query = "SELECT * FROM captar.eleitores"
        elif tabela == "ativistas":
            query = "SELECT * FROM captar.ativistas"
        elif tabela == "usuarios":
            query = "SELECT * FROM captar.usuarios"
        else:
            raise HTTPException(status_code=400, detail="Tabela inválida")
        
        db.execute(query)
        results = db.fetchall()
        
        # Converter para DataFrame
        df = pd.DataFrame(results)
        
        # Criar arquivo Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=tabela, index=False)
        
        output.seek(0)
        return {
            "filename": f"{tabela}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "data": output.getvalue().hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/pdf")
async def export_pdf(data: dict, db: Session = Depends(get_db)):
    """Exportar dados em PDF"""
    try:
        tabela = data.get("tabela")
        
        if tabela == "eleitores":
            query = "SELECT id, nome, cpf, celular, bairro FROM captar.eleitores LIMIT 100"
        elif tabela == "ativistas":
            query = "SELECT id, nome, funcao, zona FROM captar.ativistas LIMIT 100"
        elif tabela == "usuarios":
            query = "SELECT id, nome, funcao, usuario FROM captar.usuarios LIMIT 100"
        else:
            raise HTTPException(status_code=400, detail="Tabela inválida")
        
        db.execute(query)
        results = db.fetchall()
        
        # Criar PDF em memória
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        
        # Título
        styles = getSampleStyleSheet()
        title = Paragraph(f"Relatório de {tabela.capitalize()}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Tabela
        table_data = [list(results[0].keys())] + [list(row) for row in results]
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        output.seek(0)
        
        return {
            "filename": f"{tabela}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "data": output.getvalue().hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 5. AUDITORIA/LOG ====================

@router.get("/audit-logs")
async def get_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Obter logs de auditoria"""
    try:
        query = "SELECT * FROM captar.audit_logs ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        db.execute(query, (limit, skip))
        results = db.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audit-logs")
async def create_audit_log(log_data: dict, db: Session = Depends(get_db)):
    """Criar novo log de auditoria"""
    try:
        query = """
            INSERT INTO captar.audit_logs 
            (usuario_id, usuario_nome, acao, tabela, registro_id, dados_antigos, dados_novos, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute(query, (
            log_data.get("usuario_id"),
            log_data.get("usuario_nome"),
            log_data.get("acao"),
            log_data.get("tabela"),
            log_data.get("registro_id"),
            log_data.get("dados_antigos"),
            log_data.get("dados_novos"),
            log_data.get("ip_address"),
            log_data.get("user_agent")
        ))
        db.commit()
        return {"message": "Log criado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit-logs/usuario/{usuario_id}")
async def get_audit_logs_by_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obter logs de auditoria de um usuário específico"""
    try:
        query = "SELECT * FROM captar.audit_logs WHERE usuario_id = %s ORDER BY timestamp DESC LIMIT 100"
        db.execute(query, (usuario_id,))
        results = db.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== IMPORTAÇÃO EM LOTE ====================

@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Importar dados de CSV"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Validar colunas
        required_columns = ['nome', 'cpf', 'celular']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail="CSV inválido: colunas obrigatórias faltando")
        
        # Inserir dados
        inserted = 0
        for _, row in df.iterrows():
            try:
                query = "INSERT INTO captar.eleitores (nome, cpf, celular) VALUES (%s, %s, %s)"
                db.execute(query, (row['nome'], row['cpf'], row['celular']))
                inserted += 1
            except:
                continue
        
        db.commit()
        return {"message": f"{inserted} registros importados com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== NOTIFICAÇÕES ====================

@router.get("/notificacoes/{usuario_id}")
async def get_notificacoes(usuario_id: int, db: Session = Depends(get_db)):
    """Obter notificações de um usuário"""
    try:
        query = "SELECT * FROM captar.notificacoes WHERE usuario_id = %s ORDER BY criada_em DESC LIMIT 50"
        db.execute(query, (usuario_id,))
        results = db.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notificacoes")
async def create_notificacao(notif_data: dict, db: Session = Depends(get_db)):
    """Criar nova notificação"""
    try:
        query = """
            INSERT INTO captar.notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, %s, %s, %s)
        """
        db.execute(query, (
            notif_data.get("usuario_id"),
            notif_data.get("titulo"),
            notif_data.get("mensagem"),
            notif_data.get("tipo", "INFO")
        ))
        db.commit()
        return {"message": "Notificação criada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/notificacoes/{notif_id}/marcar-lida")
async def marcar_notificacao_lida(notif_id: int, db: Session = Depends(get_db)):
    """Marcar notificação como lida"""
    try:
        query = "UPDATE captar.notificacoes SET lida = true, lida_em = %s WHERE id = %s"
        db.execute(query, (datetime.utcnow(), notif_id))
        db.commit()
        return {"message": "Notificação marcada como lida"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
