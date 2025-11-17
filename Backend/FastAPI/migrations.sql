-- ============================================================
-- CAPTAR v2.0 - Migrations SQL
-- Criação de tabelas para as 15 melhorias prioritárias
-- ============================================================

-- 1. Tabela de Auditoria
CREATE TABLE IF NOT EXISTS captar.audit_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER,
    usuario_nome VARCHAR(255),
    acao VARCHAR(50),  -- CREATE, READ, UPDATE, DELETE
    tabela VARCHAR(100),
    registro_id INTEGER,
    dados_antigos TEXT,
    dados_novos TEXT,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 2. Tabela de Permissões
CREATE TABLE IF NOT EXISTS captar.permissoes (
    id SERIAL PRIMARY KEY,
    perfil VARCHAR(100) UNIQUE NOT NULL,
    descricao VARCHAR(255),
    pode_criar_eleitor BOOLEAN DEFAULT FALSE,
    pode_editar_eleitor BOOLEAN DEFAULT FALSE,
    pode_deletar_eleitor BOOLEAN DEFAULT FALSE,
    pode_criar_ativista BOOLEAN DEFAULT FALSE,
    pode_editar_ativista BOOLEAN DEFAULT FALSE,
    pode_deletar_ativista BOOLEAN DEFAULT FALSE,
    pode_criar_usuario BOOLEAN DEFAULT FALSE,
    pode_editar_usuario BOOLEAN DEFAULT FALSE,
    pode_deletar_usuario BOOLEAN DEFAULT FALSE,
    pode_enviar_disparos BOOLEAN DEFAULT FALSE,
    pode_ver_relatorios BOOLEAN DEFAULT FALSE,
    pode_exportar_dados BOOLEAN DEFAULT FALSE,
    pode_importar_dados BOOLEAN DEFAULT FALSE,
    pode_gerenciar_permissoes BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabela de Notificações
CREATE TABLE IF NOT EXISTS captar.notificacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    titulo VARCHAR(255),
    mensagem TEXT,
    tipo VARCHAR(50),  -- INFO, SUCCESS, WARNING, ERROR
    lida BOOLEAN DEFAULT FALSE,
    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lida_em TIMESTAMP,
    CONSTRAINT fk_notif_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- 4. Tabela de Disparos (SMS/Email)
CREATE TABLE IF NOT EXISTS captar.disparos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    tipo VARCHAR(50),  -- SMS, EMAIL, WHATSAPP
    destinatario VARCHAR(255),
    assunto VARCHAR(255),
    mensagem TEXT,
    status VARCHAR(50),  -- PENDENTE, ENVIADO, FALHA
    tentativas INTEGER DEFAULT 0,
    proxima_tentativa TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enviado_em TIMESTAMP,
    CONSTRAINT fk_disparo_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- 5. Tabela de Importações
CREATE TABLE IF NOT EXISTS captar.importacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    arquivo_nome VARCHAR(255),
    tipo_arquivo VARCHAR(50),  -- CSV, EXCEL
    total_registros INTEGER,
    registros_importados INTEGER,
    registros_erro INTEGER,
    status VARCHAR(50),  -- PROCESSANDO, CONCLUIDO, ERRO
    mensagem_erro TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    concluido_em TIMESTAMP,
    CONSTRAINT fk_import_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- 6. Tabela de Relatórios Agendados
CREATE TABLE IF NOT EXISTS captar.relatorios_agendados (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    nome VARCHAR(255),
    tipo VARCHAR(50),  -- DIARIO, SEMANAL, MENSAL
    dia_semana INTEGER,  -- 0-6 (segunda a domingo)
    dia_mes INTEGER,  -- 1-31
    hora TIME,
    destinatarios TEXT,  -- JSON array de emails
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_relat_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- 7. Tabela de Histórico de Alterações
CREATE TABLE IF NOT EXISTS captar.historico_alteracoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    tabela VARCHAR(100),
    registro_id INTEGER,
    acao VARCHAR(50),  -- CREATE, UPDATE, DELETE
    dados_antigos JSONB,
    dados_novos JSONB,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_hist_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 8. Tabela de Comentários
CREATE TABLE IF NOT EXISTS captar.comentarios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    tabela VARCHAR(100),
    registro_id INTEGER,
    comentario TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_coment_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- 9. Tabela de Tarefas
CREATE TABLE IF NOT EXISTS captar.tarefas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    atribuido_para INTEGER,
    titulo VARCHAR(255),
    descricao TEXT,
    prioridade VARCHAR(50),  -- BAIXA, MEDIA, ALTA
    status VARCHAR(50),  -- ABERTA, EM_PROGRESSO, CONCLUIDA
    data_vencimento DATE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    concluido_em TIMESTAMP,
    CONSTRAINT fk_tarefa_criador FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_tarefa_atribuido FOREIGN KEY (atribuido_para) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 10. Tabela de Aprovações
CREATE TABLE IF NOT EXISTS captar.aprovacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    tabela VARCHAR(100),
    registro_id INTEGER,
    status VARCHAR(50),  -- PENDENTE, APROVADO, REJEITADO
    comentario_aprovador TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aprovado_em TIMESTAMP,
    CONSTRAINT fk_aprov_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- Índices para Performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_usuario ON captar.audit_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON captar.audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON captar.notificacoes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notificacoes_lida ON captar.notificacoes(lida);
CREATE INDEX IF NOT EXISTS idx_disparos_usuario ON captar.disparos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_disparos_status ON captar.disparos(status);
CREATE INDEX IF NOT EXISTS idx_importacoes_usuario ON captar.importacoes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_relatorios_usuario ON captar.relatorios_agendados(usuario_id);
CREATE INDEX IF NOT EXISTS idx_historico_tabela ON captar.historico_alteracoes(tabela, registro_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_registro ON captar.comentarios(tabela, registro_id);
CREATE INDEX IF NOT EXISTS idx_tarefas_usuario ON captar.tarefas(atribuido_para);
CREATE INDEX IF NOT EXISTS idx_tarefas_status ON captar.tarefas(status);
CREATE INDEX IF NOT EXISTS idx_aprovacoes_status ON captar.aprovacoes(status);

-- Inserir Permissões Padrão
INSERT INTO captar.permissoes (perfil, descricao, pode_criar_eleitor, pode_editar_eleitor, pode_deletar_eleitor, pode_criar_ativista, pode_editar_ativista, pode_deletar_ativista, pode_criar_usuario, pode_editar_usuario, pode_deletar_usuario, pode_enviar_disparos, pode_ver_relatorios, pode_exportar_dados, pode_importar_dados, pode_gerenciar_permissoes)
VALUES 
('ADMINISTRADOR', 'Acesso total ao sistema', true, true, true, true, true, true, true, true, true, true, true, true, true, true),
('GERENTE', 'Gerenciamento de dados e relatórios', true, true, true, true, true, true, false, false, false, true, true, true, true, false),
('OPERADOR', 'Operações básicas', true, true, false, true, true, false, false, false, false, false, true, true, false, false),
('VISUALIZADOR', 'Apenas visualização', false, false, false, false, false, false, false, false, false, false, true, true, false, false)
ON CONFLICT (perfil) DO NOTHING;

-- Commit
COMMIT;
