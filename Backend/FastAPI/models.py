from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class AuditLog(Base):
    """Modelo para auditoria de ações dos usuários"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer)
    usuario_nome = Column(String)
    acao = Column(String)  # CREATE, READ, UPDATE, DELETE
    tabela = Column(String)  # eleitores, ativistas, usuarios, etc
    registro_id = Column(Integer)
    dados_antigos = Column(Text)  # JSON
    dados_novos = Column(Text)  # JSON
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AuditLog {self.id}: {self.usuario_nome} - {self.acao} em {self.tabela}>"

class Permissao(Base):
    """Modelo para permissões por perfil"""
    __tablename__ = "permissoes"
    
    id = Column(Integer, primary_key=True)
    perfil = Column(String, unique=True)  # ADMINISTRADOR, GERENTE, OPERADOR
    descricao = Column(String)
    pode_criar_eleitor = Column(Boolean, default=False)
    pode_editar_eleitor = Column(Boolean, default=False)
    pode_deletar_eleitor = Column(Boolean, default=False)
    pode_criar_ativista = Column(Boolean, default=False)
    pode_editar_ativista = Column(Boolean, default=False)
    pode_deletar_ativista = Column(Boolean, default=False)
    pode_criar_usuario = Column(Boolean, default=False)
    pode_editar_usuario = Column(Boolean, default=False)
    pode_deletar_usuario = Column(Boolean, default=False)
    pode_enviar_disparos = Column(Boolean, default=False)
    pode_ver_relatorios = Column(Boolean, default=False)
    pode_exportar_dados = Column(Boolean, default=False)
    pode_importar_dados = Column(Boolean, default=False)
    pode_gerenciar_permissoes = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Permissao {self.perfil}>"

class Notificacao(Base):
    """Modelo para notificações em tempo real"""
    __tablename__ = "notificacoes"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer)
    titulo = Column(String)
    mensagem = Column(Text)
    tipo = Column(String)  # INFO, SUCCESS, WARNING, ERROR
    lida = Column(Boolean, default=False)
    criada_em = Column(DateTime, default=datetime.utcnow)
    lida_em = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Notificacao {self.id}: {self.titulo}>"
