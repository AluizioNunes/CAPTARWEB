CREATE TABLE IF NOT EXISTS captar.configuracoes (
    chave VARCHAR(100) PRIMARY KEY,
    valor TEXT,
    descricao TEXT,
    tipo_dado VARCHAR(50) DEFAULT 'TEXTO',
    categoria VARCHAR(50) DEFAULT 'GERAL',
    atualizado_por INTEGER,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO captar.configuracoes (chave, valor, descricao, tipo_dado, categoria) VALUES 
('WHATSAPP_INSTANCE_NAME', 'WC', 'Nome da instância do Evolution API', 'TEXTO', 'INTEGRACAO'),
('WHATSAPP_API_KEY', '58D7985786B3-4CA2-9331-0381DFA1A4E1', 'Token de autenticação do Evolution API', 'TEXTO', 'INTEGRACAO'),
('WHATSAPP_API_URL', 'http://localhost:4000', 'URL base interna do Evolution API', 'TEXTO', 'INTEGRACAO')
ON CONFLICT (chave) DO UPDATE 
SET valor = EXCLUDED.valor;
