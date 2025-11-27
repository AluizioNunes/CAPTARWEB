## Objetivo

* Isolar dados e configurações por cliente (tenant) mantendo um único schema `captar`.

* Controlar acesso, auditoria e operações por `IdTenant` em todas as rotas e camadas.

## Modelo de Dados

* Tabela `"Tenant"`:

  * Colunas: `"IdTenant" (PK, int)`, `"Nome" (varchar)`, `"Slug" (varchar único)`, `"Status" (varchar)`, `"Plano" (varchar)`, `"DataCadastro" (timestamp)`, `"DataUpdate" (timestamp)`, `"Ativo" (boolean)`.

  * Índices: único em `"Slug"`, e índice em `"Ativo"`.

* Tabela `"TenantParametros"`:

  * Colunas: `"IdParametro" (PK)`, `"IdTenant" (FK -> "Tenant"."IdTenant")`, `"Chave" (varchar)`, `"Valor" (text)`, `"Tipo" (varchar)`, `"Descricao" (varchar)`, `"AtualizadoEm" (timestamp)`.

  * Índices: composto `("IdTenant", "Chave")` único.

* Adições de coluna `"IdTenant" (int, not null)` nas tabelas principais: `"Usuarios"`, `"Perfil"`, `"Funcoes"`, `eleitores`, `ativistas`, `interacoes`, `campanhas`, `permissoes`, `tarefas`, etc.

  * Índice por tabela em `"IdTenant"`.

  * Restrições de unicidade compostas por tenant (ex.: `("IdTenant", "Usuario")` em `"Usuarios"`).

## Isolamento e Segurança

* Decisão de escopo: multi-tenant por coluna (single schema) com `"IdTenant"` e filtros obrigatórios.

* Política de acesso:

  * Usuários pertencem a um único tenant (`"Usuarios"."IdTenant"`).

  * Perfis/Permissões são por tenant.

  * Super-admin (tenant especial "root") pode gerenciar tenants.

* Auditoria: incluir `"IdTenant"` em `audit_logs` e em cada operação, para rastreio por tenant.

## Backend (FastAPI)

* Contexto de tenant:

  * Middleware lê `X-Tenant` (header) ou subdomínio e resolve o `IdTenant` (via `"Tenant"."Slug"`).

  * Armazena `request.state.tenant_id` e injeta em handlers.

* Autenticação:

  * `POST /api/auth/login` passa a exigir `X-Tenant` e valida usuário em `"Usuarios"` filtrando por `"IdTenant"`.

  * Token `Bearer` inclui claim `tenant_id`; interceptores usam para preencher `UsuarioUpdate/CadastranteUpdate` e `DataUpdate`.

* Filtro obrigatório por tenant em todas as rotas CRUD:

  * Listar: `WHERE "IdTenant" = request.state.tenant_id`.

  * Inserir: sempre definir `"IdTenant" = request.state.tenant_id`.

  * Atualizar/Deletar: `WHERE "IdTenant" = request.state.tenant_id AND id = ...`.

* Novas rotas de Tenants:

  * `GET/POST/PUT/DELETE /api/tenants` (apenas super-admin).

  * `GET/POST/PUT/DELETE /api/tenants/{id}/params` para parâmetros.

* Migrações:

  * Criar `"Tenant"` e `"TenantParametros"` com índices e FKs.

  * Adicionar `"IdTenant"` às tabelas e preencher dados existentes com um tenant padrão (ex.: `DEFAULT_TENANT`).

  * Ajustar triggers de atualização/auditoria para incluir `"IdTenant"`.

## Frontend (React + Vite)

* Contexto de Tenant:

  * `ApiContext` passa a enviar `X-Tenant` em todos os requests; gerencia o tenant ativo.

  * Tela de seleção de tenant para super-admin; usuários comuns fixos no seu tenant.

* UI/Fluxos:

  * Ocultar campo `"IdTenant"` nos formulários; valor vem do contexto.

  * Filtrar tabelas e dashboards pelo tenant ativo.

  * Nova página “Tenants” com CRUD e “Parâmetros do Tenant” com listagem/edição.

## Auditoria e Logs

* `audit_logs` passa a armazenar `tenant_id` e usuário/ação com escopo do tenant.

* Ajustar funções PL/pgSQL de auditoria para registrar `NEW."IdTenant"`/`OLD."IdTenant"`.

## Provisionamento e Operações

* Provisionar tenant:

  * Criar registro em `"Tenant"` + parâmetros iniciais em `"TenantParametros"`.

  * Criar usuário administrador do tenant (`"Usuarios"` com `"IdTenant"` do novo tenant).

* Backup/Restore por tenant:

  * Estratégia de export por `"IdTenant"` (dump lógico filtrado) para portabilidade.

* Quotas/Planos:

  * Campos `"Plano"`, limites de registros, features habilitadas via `"TenantParametros"`.

## Migração de Dados Existentes

* Criar tenant padrão (“CAPTAR”) e atribuir `"IdTenant"` a todos os registros atuais.

* Ajustar dados divergentes de schema minúsculo/maiúsculo e normalizar tipos.

## Testes

* Testes de integração cobrindo:

  * Login multi-tenant e emissão de token com `tenant_id`.

  * CRUD por tenant (isolamento garantido).

  * Auditoria por tenant.

  * Troca de tenant por super-admin visível no frontend.

## Segurança

* Validar `X-Tenant` contra `"Tenant"."Slug"`; rejeitar tenants inativos.

* Garantir que `tenant_id` do token e do header coincidam; caso contrário, negar acesso.

* Rate limits e quotas por tenant (opcional).

## Entregáveis

* Tabelas `"Tenant"` e `"TenantParametros"` com migrações.

* Middleware, rotas e filtros obrigatórios em backend.

* Contexto de tenant e telas de Tenants/Parâmetros no frontend.

* Scripts de migração e documentação operacional de provisionamento.

## Confirmação

* Confirma a abordagem de single schema com coluna `"IdTenant"` e header `X-Tenant`? Se sim, inicio a implementação com migração do banco, middleware no FastAPI e ajustes de frontend para seleção/aplicação de tenant.

