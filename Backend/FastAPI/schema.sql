-- ============================================================
-- CAPTAR v2.0 - Schema SQL Completo
-- Recriação do esquema do banco de dados
-- ============================================================

-- Criação do esquema se não existir
CREATE SCHEMA IF NOT EXISTS captar;

-- Configuração do search_path para o esquema captar
SET search_path TO captar, public;

-- 1. Tabela de Permissões
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

-- 2. Tabela de Usuários
CREATE TABLE IF NOT EXISTS captar.usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    telefone VARCHAR(20),
    perfil_id INTEGER REFERENCES captar.permissoes(id),
    ativo BOOLEAN DEFAULT TRUE,
    ultimo_acesso TIMESTAMP,
    token_recuperacao VARCHAR(255),
    token_expiracao TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabela de Auditoria
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

-- 4. Tabela de Notificações
CREATE TABLE IF NOT EXISTS captar.notificacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    titulo VARCHAR(255),
    mensagem TEXT,
    tipo VARCHAR(50),  -- SUCESSO, ERRO, ALERTA, INFO
    lida BOOLEAN DEFAULT FALSE,
    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lida_em TIMESTAMP,
    CONSTRAINT fk_notificacao_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE
);

-- 5. Tabela de Tarefas
CREATE TABLE IF NOT EXISTS captar.tarefas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    atribuido_para INTEGER,
    titulo VARCHAR(255),
    descricao TEXT,
    prioridade VARCHAR(20),  -- BAIXA, MEDIA, ALTA, URGENTE
    status VARCHAR(20) DEFAULT 'PENDENTE',  -- PENDENTE, EM_ANDAMENTO, CONCLUIDA, CANCELADA
    data_limite DATE,
    concluida_em TIMESTAMP,
    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tarefa_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_tarefa_atribuido_para FOREIGN KEY (atribuido_para) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 6. Tabela de Eleitores
CREATE TABLE IF NOT EXISTS captar.eleitores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE,
    email VARCHAR(255),
    telefone VARCHAR(20),
    cep VARCHAR(10),
    endereco VARCHAR(255),
    numero VARCHAR(10),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    uf CHAR(2),
    zona_eleitoral VARCHAR(10),
    secao_eleitoral VARCHAR(10),
    titulo_eleitor VARCHAR(20),
    zona VARCHAR(10),
    secao VARCHAR(10),
    local_votacao TEXT,
    endereco_local_votacao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    criado_por INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_eleitor_criado_por FOREIGN KEY (criado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 7. Tabela de Ativistas
CREATE TABLE IF NOT EXISTS captar.ativistas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE,
    email VARCHAR(255),
    telefone VARCHAR(20),
    cep VARCHAR(10),
    endereco VARCHAR(255),
    numero VARCHAR(10),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    uf CHAR(2),
    tipo_apoio VARCHAR(50),  -- VOLUNTARIO, APOIADOR, LIDERANCA, COORDENADOR
    area_atuacao VARCHAR(100),
    habilidades TEXT,
    disponibilidade TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    criado_por INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ativista_criado_por FOREIGN KEY (criado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 8. Tabela de Interações
CREATE TABLE IF NOT EXISTS captar.interacoes (
    id SERIAL PRIMARY KEY,
    eleitor_id INTEGER,
    ativista_id INTEGER,
    tipo_interacao VARCHAR(50),  -- VISITA, LIGACAO, WHATSAPP, EMAIL, REUNIAO, EVENTO
    data_interacao TIMESTAMP NOT NULL,
    descricao TEXT,
    proximo_contato DATE,
    status VARCHAR(50),  -- NOVO_CONTATO, CONTATO_EFETUADO, AGUARDANDO_RETORNO, CONTATO_INVALIDO
    anotacoes TEXT,
    criado_por INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_interacao_eleitor FOREIGN KEY (eleitor_id) REFERENCES captar.eleitores(id) ON DELETE CASCADE,
    CONSTRAINT fk_interacao_ativista FOREIGN KEY (ativista_id) REFERENCES captar.ativistas(id) ON DELETE SET NULL,
    CONSTRAINT fk_interacao_criado_por FOREIGN KEY (criado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 9. Tabela de Campanhas
CREATE TABLE IF NOT EXISTS captar.campanhas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    data_inicio DATE NOT NULL,
    data_fim DATE,
    orcamento DECIMAL(15, 2),
    status VARCHAR(50) DEFAULT 'PLANEJAMENTO',  -- PLANEJAMENTO, EM_ANDAMENTO, CONCLUIDA, CANCELADA
    criado_por INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_campanha_criado_por FOREIGN KEY (criado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 10. Tabela de Ações de Campanha
CREATE TABLE IF NOT EXISTS captar.acoes_campanha (
    id SERIAL PRIMARY KEY,
    campanha_id INTEGER NOT NULL,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    tipo_acao VARCHAR(50),  -- EVENTO, PANFLETAGEM, VISITA_DOMICILIAR, REDES_SOCIAIS, ETC
    data_hora_inicio TIMESTAMP NOT NULL,
    data_hora_fim TIMESTAMP,
    localizacao TEXT,
    responsavel_id INTEGER,
    status VARCHAR(50) DEFAULT 'PLANEJADA',  -- PLANEJADA, EM_ANDAMENTO, CONCLUIDA, CANCELADA
    resultado TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_acao_campanha FOREIGN KEY (campanha_id) REFERENCES captar.campanhas(id) ON DELETE CASCADE,
    CONSTRAINT fk_acao_responsavel FOREIGN KEY (responsavel_id) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 11. Tabela de Participação em Ações
CREATE TABLE IF NOT EXISTS captar.participacoes_acao (
    id SERIAL PRIMARY KEY,
    acao_id INTEGER NOT NULL,
    ativista_id INTEGER NOT NULL,
    confirmado BOOLEAN DEFAULT FALSE,
    compareceu BOOLEAN DEFAULT FALSE,
    avaliacao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_participacao_acao FOREIGN KEY (acao_id) REFERENCES captar.acoes_campanha(id) ON DELETE CASCADE,
    CONSTRAINT fk_participacao_ativista FOREIGN KEY (ativista_id) REFERENCES captar.ativistas(id) ON DELETE CASCADE,
    CONSTRAINT uq_participacao_acao_ativista UNIQUE (acao_id, ativista_id)
);

-- 12. Tabela de Mensagens
CREATE TABLE IF NOT EXISTS captar.mensagens (
    id SERIAL PRIMARY KEY,
    remetente_id INTEGER,
    destinatario_id INTEGER,
    assunto VARCHAR(255),
    conteudo TEXT,
    lida BOOLEAN DEFAULT FALSE,
    lida_em TIMESTAMP,
    enviada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensagem_remetente FOREIGN KEY (remetente_id) REFERENCES captar.usuarios(id) ON DELETE SET NULL,
    CONSTRAINT fk_mensagem_destinatario FOREIGN KEY (destinatario_id) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 13. Tabela de Disparos
CREATE TABLE IF NOT EXISTS captar.disparos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    tipo_disparo VARCHAR(50),  -- EMAIL, SMS, WHATSAPP, NOTIFICACAO
    status VARCHAR(50) DEFAULT 'RASCUNHO',  -- RASCUNHO, AGENDADO, ENVIANDO, CONCLUIDO, CANCELADO
    data_agendamento TIMESTAMP,
    total_contatos INTEGER DEFAULT 0,
    total_enviados INTEGER DEFAULT 0,
    total_erros INTEGER DEFAULT 0,
    criado_por INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_disparo_criado_por FOREIGN KEY (criado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 14. Tabela de Contatos para Disparo
CREATE TABLE IF NOT EXISTS captar.contatos_disparo (
    id SERIAL PRIMARY KEY,
    disparo_id INTEGER NOT NULL,
    destinatario VARCHAR(255) NOT NULL,  -- EMAIL, TELEFONE, ETC
    nome_destinatario VARCHAR(255),
    status VARCHAR(50) DEFAULT 'PENDENTE',  -- PENDENTE, ENVIANDO, ENVIADO, ENTREGUE, FALHA
    mensagem_erro TEXT,
    enviado_em TIMESTAMP,
    entregue_em TIMESTAMP,
    CONSTRAINT fk_contato_disparo FOREIGN KEY (disparo_id) REFERENCES captar.disparos(id) ON DELETE CASCADE
);

-- 15. Tabela de Relatórios
CREATE TABLE IF NOT EXISTS captar.relatorios (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    tipo_relatorio VARCHAR(100) NOT NULL,  -- ELEITORES, ATIVISTAS, CAMPANHAS, ETC
    parametros TEXT,  -- JSON COM OS PARÂMETROS DO RELATÓRIO
    formato VARCHAR(20) DEFAULT 'PDF',  -- PDF, XLSX, CSV
    status VARCHAR(50) DEFAULT 'PENDENTE',  -- PENDENTE, PROCESSANDO, CONCLUIDO, FALHA
    caminho_arquivo TEXT,
    criado_por INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    concluido_em TIMESTAMP,
    CONSTRAINT fk_relatorio_criado_por FOREIGN KEY (criado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 16. Tabela de Logs do Sistema
CREATE TABLE IF NOT EXISTS captar.logs_sistema (
    id SERIAL PRIMARY KEY,
    nivel VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    origem VARCHAR(100),  -- MÓDULO/CLASSE QUE GEROU O LOG
    mensagem TEXT NOT NULL,
    detalhes TEXT,
    ip_origem VARCHAR(50),
    usuario_id INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_usuario FOREIGN KEY (usuario_id) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- 17. Tabela de Configurações
CREATE TABLE IF NOT EXISTS captar.configuracoes (
    chave VARCHAR(100) PRIMARY KEY,
    valor TEXT,
    descricao TEXT,
    tipo_dado VARCHAR(50) DEFAULT 'TEXTO',  -- TEXTO, NUMERO, BOOLEANO, JSON
    categoria VARCHAR(50) DEFAULT 'GERAL',
    atualizado_por INTEGER,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_configuracao_atualizado_por FOREIGN KEY (atualizado_por) REFERENCES captar.usuarios(id) ON DELETE SET NULL
);

-- Inserir permissões padrão
INSERT INTO captar.permissoes (
    perfil, 
    descricao,
    pode_criar_eleitor, pode_editar_eleitor, pode_deletar_eleitor,
    pode_criar_ativista, pode_editar_ativista, pode_deletar_ativista,
    pode_criar_usuario, pode_editar_usuario, pode_deletar_usuario,
    pode_enviar_disparos, pode_ver_relatorios, pode_exportar_dados,
    pode_importar_dados, pode_gerenciar_permissoes
) VALUES 
('ADMINISTRADOR', 'Acesso total ao sistema', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE),
('GERENTE', 'Gerente de campanha', TRUE, TRUE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, TRUE, FALSE),
('OPERADOR', 'Operador do sistema', TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE),
('VISITANTE', 'Apenas visualização', FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE)
ON CONFLICT (perfil) DO NOTHING;

-- Inserir usuário administrador padrão (senha: admin123)
-- A senha será atualizada pelo sistema no primeiro login
INSERT INTO captar.usuarios (
    nome, 
    email, 
    senha_hash, 
    perfil_id,
    ativo
) VALUES (
    'Administrador', 
    'admin@captar.com', 
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',  -- senha: admin123
    (SELECT id FROM captar.permissoes WHERE perfil = 'ADMINISTRADOR' LIMIT 1),
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Inserir configurações padrão
INSERT INTO captar.configuracoes (chave, valor, descricao, tipo_dado, categoria) VALUES 
('SISTEMA_NOME', 'CAPTAR', 'Nome do sistema', 'TEXTO', 'GERAL'),
('SISTEMA_VERSAO', '2.0.0', 'Versão do sistema', 'TEXTO', 'GERAL'),
('PAGINACAO_ITENS_POR_PAGINA', '20', 'Número de itens por página nas listagens', 'NUMERO', 'INTERFACE'),
('EMAIL_SERVIDOR', '', 'Servidor SMTP para envio de e-mails', 'TEXTO', 'EMAIL'),
('EMAIL_PORTA', '587', 'Porta do servidor SMTP', 'NUMERO', 'EMAIL'),
('EMAIL_USUARIO', '', 'Usuário para autenticação no servidor SMTP', 'TEXTO', 'EMAIL'),
('EMAIL_SENHA', '', 'Senha para autenticação no servidor SMTP', 'TEXTO', 'EMAIL'),
('WHATSAPP_API_KEY', '', 'Chave da API do WhatsApp', 'TEXTO', 'INTEGRACAO'),
('SMS_API_KEY', '', 'Chave da API de SMS', 'TEXTO', 'INTEGRACAO')
ON CONFLICT (chave) DO NOTHING;

-- Criar índices para melhorar desempenho
CREATE INDEX IF NOT EXISTS idx_eleitores_nome ON captar.eleitores(nome);
CREATE INDEX IF NOT EXISTS idx_eleitores_cpf ON captar.eleitores(cpf);
CREATE INDEX IF NOT EXISTS idx_eleitores_cidade ON captar.eleitores(cidade);
CREATE INDEX IF NOT EXISTS idx_eleitores_bairro ON captar.eleitores(bairro);

CREATE INDEX IF NOT EXISTS idx_ativistas_nome ON captar.ativistas(nome);
CREATE INDEX IF NOT EXISTS idx_ativistas_cpf ON captar.ativistas(cpf);
CREATE INDEX IF NOT EXISTS idx_ativistas_cidade ON captar.ativistas(cidade);

CREATE INDEX IF NOT EXISTS idx_interacoes_eleitor ON captar.interacoes(eleitor_id);
CREATE INDEX IF NOT EXISTS idx_interacoes_ativista ON captar.interacoes(ativista_id);
CREATE INDEX IF NOT EXISTS idx_interacoes_data ON captar.interacoes(data_interacao);

CREATE INDEX IF NOT EXISTS idx_audit_logs_usuario ON captar.audit_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON captar.audit_logs(timestamp);

-- Função para atualizar o campo atualizado_em
CREATE OR REPLACE FUNCTION atualizar_data_atualizacao()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para atualização automática do campo atualizado_em
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'captar' 
        AND table_type = 'BASE TABLE'
        AND table_name IN (
            'usuarios', 'eleitores', 'ativistas', 'interacoes', 
            'campanhas', 'acoes_campanha', 'permissoes', 'tarefas'
        )
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS tr_atualiza_%s ON captar.%I', 
                      t.table_name, t.table_name);
                      
        EXECUTE format('CREATE TRIGGER tr_atualiza_%s
                      BEFORE UPDATE ON captar.%I
                      FOR EACH ROW EXECUTE FUNCTION atualizar_data_atualizacao()',
                      t.table_name, t.table_name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Função para registrar logs de auditoria
CREATE OR REPLACE FUNCTION registrar_auditoria()
RETURNS TRIGGER AS $$
DECLARE
    v_acao TEXT;
    v_dados_antigos TEXT;
    v_dados_novos TEXT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_acao := 'CREATE';
        v_dados_novos := row_to_json(NEW)::TEXT;
        
        INSERT INTO captar.audit_logs (
            usuario_id, usuario_nome, acao, tabela, registro_id, 
            dados_antigos, dados_novos, ip_address, user_agent
        ) VALUES (
            NEW.criado_por, 
            (SELECT nome FROM captar.usuarios WHERE id = NEW.criado_por),
            v_acao, 
            TG_TABLE_NAME, 
            NEW.id, 
            NULL, 
            v_dados_novos,
            NULL,  -- IP e user_agent podem ser preenchidos pela aplicação
            NULL
        );
        
    ELSIF TG_OP = 'UPDATE' THEN
        v_acao := 'UPDATE';
        v_dados_antigos := row_to_json(OLD)::TEXT;
        v_dados_novos := row_to_json(NEW)::TEXT;
        
        INSERT INTO captar.audit_logs (
            usuario_id, usuario_nome, acao, tabela, registro_id, 
            dados_antigos, dados_novos, ip_address, user_agent
        ) VALUES (
            NEW.atualizado_por, 
            (SELECT nome FROM captar.usuarios WHERE id = NEW.atualizado_por),
            v_acao, 
            TG_TABLE_NAME, 
            NEW.id, 
            v_dados_antigos, 
            v_dados_novos,
            NULL,
            NULL
        );
        
    ELSIF TG_OP = 'DELETE' THEN
        v_acao := 'DELETE';
        v_dados_antigos := row_to_json(OLD)::TEXT;
        
        INSERT INTO captar.audit_logs (
            usuario_id, usuario_nome, acao, tabela, registro_id, 
            dados_antigos, dados_novos, ip_address, user_agent
        ) VALUES (
            OLD.atualizado_por, 
            (SELECT nome FROM captar.usuarios WHERE id = OLD.atualizado_por),
            v_acao, 
            TG_TABLE_NAME, 
            OLD.id, 
            v_dados_antigos, 
            NULL,
            NULL,
            NULL
        );
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers de auditoria nas tabelas principais
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'captar' 
        AND table_type = 'BASE TABLE'
        AND table_name IN (
            'usuarios', 'eleitores', 'ativistas', 'interacoes', 
            'campanhas', 'acoes_campanha', 'permissoes', 'tarefas'
        )
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS tr_auditoria_%s ON captar.%I', 
                      t.table_name, t.table_name);
                      
        EXECUTE format('CREATE TRIGGER tr_auditoria_%s
                      AFTER INSERT OR UPDATE OR DELETE ON captar.%I
                      FOR EACH ROW EXECUTE FUNCTION registrar_auditoria()',
                      t.table_name, t.table_name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Função para gerar relatório de atividades
CREATE OR REPLACE FUNCTION captar.gerar_relatorio_atividades(
    p_data_inicio DATE,
    p_data_fim DATE,
    p_usuario_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    data DATE,
    total_contatos INTEGER,
    total_eleitores_novos INTEGER,
    total_ativistas_novos INTEGER,
    total_interacoes INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH datas AS (
        SELECT generate_series(
            p_data_inicio::timestamp,
            p_data_fim::timestamp,
            '1 day'::interval
        )::DATE AS data
    )
    SELECT 
        d.data,
        COALESCE(e.total_eleitores, 0) + COALESCE(a.total_ativistas, 0) + COALESCE(i.total_interacoes, 0) AS total_contatos,
        COALESCE(e.total_eleitores, 0) AS total_eleitores_novos,
        COALESCE(a.total_ativistas, 0) AS total_ativistas_novos,
        COALESCE(i.total_interacoes, 0) AS total_interacoes
    FROM datas d
    LEFT JOIN (
        SELECT 
            DATE(criado_em) AS data,
            COUNT(*) AS total_eleitores
        FROM captar.eleitores
        WHERE 
            (p_usuario_id IS NULL OR criado_por = p_usuario_id)
            AND DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim
        GROUP BY DATE(criado_em)
    ) e ON e.data = d.data
    LEFT JOIN (
        SELECT 
            DATE(criado_em) AS data,
            COUNT(*) AS total_ativistas
        FROM captar.ativistas
        WHERE 
            (p_usuario_id IS NULL OR criado_por = p_usuario_id)
            AND DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim
        GROUP BY DATE(criado_em)
    ) a ON a.data = d.data
    LEFT JOIN (
        SELECT 
            DATE(criado_em) AS data,
            COUNT(*) AS total_interacoes
        FROM captar.interacoes
        WHERE 
            (p_usuario_id IS NULL OR criado_por = p_usuario_id)
            AND DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim
        GROUP BY DATE(criado_em)
    ) i ON i.data = d.data
    ORDER BY d.data;
END;
$$ LANGUAGE plpgsql;

-- Função para buscar estatísticas gerais
CREATE OR REPLACE FUNCTION captar.obter_estatisticas_gerais()
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT json_build_object(
        'total_eleitores', (SELECT COUNT(*) FROM captar.eleitores WHERE ativo = TRUE),
        'total_ativistas', (SELECT COUNT(*) FROM captar.ativistas WHERE ativo = TRUE),
        'total_usuarios', (SELECT COUNT(*) FROM captar.usuarios WHERE ativo = TRUE),
        'total_campanhas_ativas', (SELECT COUNT(*) FROM captar.campanhas WHERE status = 'EM_ANDAMENTO'),
        'total_interacoes_hoje', (
            SELECT COUNT(*) 
            FROM captar.interacoes 
            WHERE DATE(criado_em) = CURRENT_DATE
        ),
        'ultimas_interacoes', (
            SELECT json_agg(
                json_build_object(
                    'id', i.id,
                    'tipo', i.tipo_interacao,
                    'data', i.data_interacao,
                    'descricao', i.descricao,
                    'eleitor', e.nome,
                    'eleitor_id', e.id,
                    'usuario', u.nome,
                    'usuario_id', u.id
                )
            )
            FROM captar.interacoes i
            LEFT JOIN captar.eleitores e ON i.eleitor_id = e.id
            LEFT JOIN captar.usuarios u ON i.criado_por = u.id
            ORDER BY i.criado_em DESC
            LIMIT 5
        )
    ) INTO v_result;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Mensagem de conclusão
DO $$
BEGIN
    RAISE NOTICE 'Esquema do banco de dados CAPTAR criado com sucesso!';
    RAISE NOTICE 'Usuário administrador padrão: admin@captar.com / admin123';
    RAISE NOTICE 'Certifique-se de alterar a senha no primeiro acesso!';
END;
$$;

-- Ajuste de comprimento da coluna Celular na tabela "Usuarios" (legado)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'captar'
          AND table_name = 'Usuarios'
          AND column_name = 'Celular'
          AND character_maximum_length IS NOT NULL
          AND character_maximum_length < 15
    ) THEN
        EXECUTE 'ALTER TABLE "captar"."Usuarios" ALTER COLUMN "Celular" TYPE VARCHAR(15)';
    END IF;
END;
$$;
