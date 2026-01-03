import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import pg from "pg";

const { Pool } = pg;

const DB_SCHEMA = String(process.env.DB_SCHEMA || "captar").trim() || "captar";

const DB_HOST = String(process.env.DB_HOST || "").trim() || "localhost";
const DB_PORT = (() => {
  const raw = String(process.env.DB_PORT || "").trim();
  if (raw) {
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) ? n : 5432;
  }
  if (DB_HOST === "localhost" || DB_HOST === "127.0.0.1") return 5440;
  return 5432;
})();

const pool = new Pool({
  host: DB_HOST,
  port: DB_PORT,
  database: process.env.DB_NAME || "captar",
  user: process.env.DB_USER || "captar",
  password: process.env.DB_PASSWORD || "captar",
  ssl:
    String(process.env.DB_SSL || "")
      .trim()
      .toLowerCase() === "true"
      ? { rejectUnauthorized: false }
      : undefined,
  max: Number.parseInt(process.env.DB_POOL_MAX || "1", 10),
  idleTimeoutMillis: Number.parseInt(process.env.DB_POOL_IDLE_MS || "30000", 10),
  connectionTimeoutMillis: Number.parseInt(process.env.DB_POOL_CONN_TIMEOUT_MS || "10000", 10),
});

const server = new Server(
  { name: "postgres-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } },
);

async function withClient(fn) {
  const client = await pool.connect();
  try {
    await client.query("SELECT set_config('search_path', $1, false)", [DB_SCHEMA]);
    return await fn(client);
  } finally {
    client.release();
  }
}

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "query_postgres",
        description: "Executa uma query SQL no PostgreSQL e retorna as linhas",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string", description: "Query SQL para executar" },
            params: { type: "array", description: "Parâmetros posicionais ($1, $2, ...)" },
            row_limit: { type: "integer", description: "Limite de linhas (padrão 500)" },
          },
          required: ["query"],
        },
      },
      {
        name: "list_tables",
        description: "Lista todas as tabelas do schema configurado",
        inputSchema: { type: "object", properties: {} },
      },
      {
        name: "describe_table",
        description: "Descreve a estrutura (colunas) de uma tabela",
        inputSchema: {
          type: "object",
          properties: {
            table_name: { type: "string", description: "Nome da tabela" },
          },
          required: ["table_name"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const toolName = request.params?.name;
  const args = (request.params?.arguments || {}) ?? {};

  if (toolName === "query_postgres") {
    const query = String(args.query || "");
    const params = Array.isArray(args.params) ? args.params : [];
    const rowLimitRaw = Number.isFinite(args.row_limit) ? Number(args.row_limit) : 500;
    const rowLimit = Math.max(1, Math.min(5000, Math.trunc(rowLimitRaw)));

    const res = await withClient(async (client) => {
      const r = await client.query(query, params);
      const rows = Array.isArray(r.rows) ? r.rows.slice(0, rowLimit) : [];
      return { rowCount: r.rowCount ?? rows.length, rows };
    });

    return {
      content: [{ type: "text", text: JSON.stringify(res, null, 2) }],
    };
  }

  if (toolName === "list_tables") {
    const res = await withClient(async (client) => {
      const r = await client.query(
        `
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1
        ORDER BY table_name ASC
        `,
        [DB_SCHEMA],
      );
      return r.rows || [];
    });
    return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
  }

  if (toolName === "describe_table") {
    const tableName = String(args.table_name || "").trim();
    if (!tableName) throw new Error("table_name é obrigatório");

    const res = await withClient(async (client) => {
      const r = await client.query(
        `
        SELECT
          ordinal_position,
          column_name,
          data_type,
          is_nullable,
          column_default
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position ASC
        `,
        [DB_SCHEMA, tableName],
      );
      return r.rows || [];
    });
    return { content: [{ type: "text", text: JSON.stringify(res, null, 2) }] };
  }

  throw new Error(`Ferramenta desconhecida: ${toolName}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  try {
    process.stderr.write(String(err?.stack || err || "Erro ao iniciar MCP") + "\n");
  } catch {}
  process.exit(1);
});
