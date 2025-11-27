export interface User {
  id: number
  nome: string
  funcao: string
  usuario: string
  email: string
  cpf: string
  perfil: string
  login_time?: string
}

export interface LoginRequest {
  usuario: string
  senha: string
}

export interface LoginResponse {
  token: string
  user: User
}

export interface Eleitor {
  id: number
  nome: string
  celular: string
  cpf: string
  rg: string
  titulo: string
  secao_eleitoral: string
  zona_eleitoral: string
  local_eleitoral: string
  bairro: string
  zona_cidade: string
  cidade: string
  uf: string
  cadastrante: string
  funcao: string
  perfil: string
  indicacao: string
  datahora: string
  supervisor: string
  coordenador: string
}

export interface Ativista {
  id: number
  datacadastro: string
  nome: string
  funcao: string
  zona: string
  descricao: string
  imagem_perfil_path: string
  supervisor: string
}

export interface Funcao {
  id: number
  funcao: string
  descricao: string
}

export interface Bairro {
  id: number
  zona_eleitoral: string
  bairro: string
  cidade: string
  uf: string
  zona_cidade: string
}

export interface Zona {
  id_zona: number
  zona: string
  created_at: string
}

export interface DashboardStats {
  total_eleitores: number
  total_ativistas: number
  total_usuarios: number
  eleitores_por_zona: Record<string, number>
  ativistas_por_funcao: Record<string, number>
}

export interface IntegracaoConfig {
  base_url: string
  uf: string
  dataset?: string
  municipio?: string
  webhook_url?: string
  webhook_secret?: string
  tse_token?: string
  external_api_token?: string
  active_webhook?: boolean
}
