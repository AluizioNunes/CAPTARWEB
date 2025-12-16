import axios, { AxiosInstance } from 'axios'
import { LoginRequest, LoginResponse, User, IntegracaoConfig } from '../types'

export interface ApiResponse<T> {
  rows: T[]
  columns: string[]
}

export interface Eleitor {
  id: number
  nome: string
  cpf?: string
  celular?: string
  bairro?: string
  zona_eleitoral?: string
  criado_por?: number
  IdTenant?: number
  TenantLayer?: string
  DataCadastro?: string
  DataUpdate?: string
  TipoUpdate?: string
  UsuarioUpdate?: string
}

export interface Ativista {
  id: number
  nome: string
  tipo_apoio?: string
  criado_por?: number
  IdTenant?: number
  TenantLayer?: string
  DataCadastro?: string
  DataUpdate?: string
  TipoUpdate?: string
  UsuarioUpdate?: string
}

const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env && (import.meta as any).env.VITE_API_URL) || '/api'

class ApiService {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Interceptor para adicionar token
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      const isLogin = String(config.url || '').includes('/auth/login')
      const hasExplicitTenant = !!(config.headers && (config.headers as any)['X-Tenant'])
      if (!isLogin) {
        const root = localStorage.getItem('rootTenantSlug') || 'captar'
        const adminCtx = localStorage.getItem('adminContext') === '1'
        const cur = localStorage.getItem('tenantSlug') || 'captar'
        const effective = (adminCtx && String(root).toLowerCase() === 'captar') ? 'captar' : cur
        ;(config.headers as any)['X-Tenant'] = effective
        const view = localStorage.getItem('viewTenantSlug') || ''
        if (adminCtx && view) {
          ;(config.headers as any)['X-View-Tenant'] = view
        } else {
          if ((config.headers as any)['X-View-Tenant']) delete (config.headers as any)['X-View-Tenant']
        }
      } else if (!hasExplicitTenant && config.headers) {
        delete (config.headers as any)['X-Tenant']
      }
      return config
    })

    // Interceptor para tratar erros
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )

    // removido disparo automático de migração para evitar 404 em ambientes sem o endpoint
  }

  // ==================== AUTENTICAÇÃO ====================

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const tryLogin = async (slug?: string) => {
      const chosenSlug = slug ?? 'captar'
      const cfg = chosenSlug ? { headers: { 'X-Tenant': chosenSlug } } : {}
      const resp = await this.api.post('/auth/login', credentials, cfg)
      const data = resp.data
      const rawTenant = (data?.tenantSlug ?? data?.tenant ?? data?.slug ?? data?.TenantSlug ?? data?.Tenant)
      const tenantSlug = String(rawTenant || chosenSlug)
      localStorage.setItem('tenantSlug', tenantSlug)
      try {
        const root = localStorage.getItem('rootTenantSlug')
        if (!root) localStorage.setItem('rootTenantSlug', tenantSlug)
        if (tenantSlug.toLowerCase() === 'captar') {
          localStorage.setItem('rootTenantSlug', 'captar')
          localStorage.setItem('adminContext', '1')
        }
      } catch {}
      try {
        const resTen = await this.listTenants()
        const rowsTen = resTen.rows || []
        const t = rowsTen.find((r: any) => String(r.Slug ?? r.slug).toUpperCase() === tenantSlug.toUpperCase())
        const tenantName = t ? String(t.Nome ?? t.nome) : tenantSlug
        localStorage.setItem('tenantName', tenantName)
      } catch {}
      if (data && data.token && !data.user) {
        const user: User = {
          id: data.id,
          nome: data.nome,
          funcao: data.funcao,
          usuario: data.usuario,
          email: data.email,
          cpf: data.cpf,
          perfil: data.funcao
        }
        return { token: data.token, user }
      }
      return data
    }

    try {
      return await tryLogin()
    } catch (e1: any) {
      try {
        // fallback: tentar com 'captar'
        return await tryLogin('captar')
      } catch (e2: any) {
        try {
          // fallback: testar todos tenants conhecidos
          const list = await this.listTenants().catch(() => ({ rows: [] }))
          const rows = (list.rows || [])
          const slugs: string[] = rows.map((t: any) => String(t.Slug ?? t.slug ?? '')).filter(Boolean)
          for (const slug of slugs) {
            try {
              const r = await tryLogin(slug)
              return r
            } catch {}
          }
        } catch {}
        throw e1
      }
    }
  }

  async healthDb(): Promise<{ ok: boolean }> {
    try {
      const response = await this.api.get('/health/db')
      return response.data
    } catch (e1: any) {
      try {
        const resp2 = await this.api.get('/health')
        return { ok: !!resp2.data }
      } catch (e2: any) {
        try {
          const fb = axios.create({ baseURL: 'http://localhost:8001', headers: { 'Content-Type': 'application/json' } })
          const resp3 = await fb.get('/api/health/db')
          return resp3.data
        } catch (e3: any) {
          const fb2 = axios.create({ baseURL: 'http://localhost:8001', headers: { 'Content-Type': 'application/json' } })
          const resp4 = await fb2.get('/health')
          return { ok: !!resp4.data }
        }
      }
    }
  }

  async logout(): Promise<void> {
    await this.api.post('/auth/logout')
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get('/auth/me')
    return response.data
  }

  // ==================== PERMISSÕES ====================

  async getPermissoes(): Promise<any[]> {
    const response = await this.api.get('/permissoes')
    return response.data
  }

  async getPermissao(perfil: string): Promise<any> {
    const response = await this.api.get(`/permissoes/${perfil}`)
    return response.data
  }

  async updatePermissao(perfil: string, data: any): Promise<any> {
    const response = await this.api.put(`/permissoes/${perfil}`, data)
    return response.data
  }

  async createPermissao(data: any): Promise<any> {
    const response = await this.api.post('/permissoes', data)
    return response.data
  }

  async deletePermissao(perfil: string): Promise<any> {
    const response = await this.api.delete(`/permissoes/${perfil}`)
    return response.data
  }

  async getPerfilSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean }[] }> {
    try {
      const response = await this.api.get('/perfil/schema')
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/perfil/schema')
      return response.data
    }
  }

  async listPerfil(): Promise<{ rows: any[]; columns: string[] }> {
    const currentSlug = (localStorage.getItem('tenantSlug') || 'captar').toLowerCase()
    // fetch current tenant
    const cur = await this.api.get('/perfil').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      return (await fb.get('/perfil')).data
    })
    if (currentSlug === 'captar') return cur
    // additionally fetch CAPTAR
    const hdr: Record<string, string> = { 'Content-Type': 'application/json', 'X-Tenant': 'captar' }
    const token = localStorage.getItem('token')
    if (token) hdr['Authorization'] = `Bearer ${token}`
    const alt = axios.create({ baseURL: API_BASE_URL, headers: hdr })
    const cap = await alt.get('/perfil').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: hdr })
      return (await fb.get('/perfil')).data
    })
    const rowsCur = cur.rows || []
    const rowsCap = cap.rows || []
    const mergedMap: Record<string, any> = {}
    for (const r of [...rowsCap, ...rowsCur]) {
      const key = String(r.Perfil ?? r.perfil ?? r.Descricao ?? r.descricao ?? '').toUpperCase()
      if (!mergedMap[key]) mergedMap[key] = r
    }
    return { rows: Object.values(mergedMap), columns: cur.columns || cap.columns || [] }
  }

  async createPerfil(payload: any): Promise<{ id: number }> {
    try {
      const response = await this.api.post('/perfil', payload)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post('/perfil', payload)
      return response.data
    }
  }

  async updatePerfil(id: number, payload: any): Promise<{ id: number }> {
    try {
      const response = await this.api.put(`/perfil/${id}`, payload)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.put(`/perfil/${id}`, payload)
      return response.data
    }
  }

  async deletePerfil(id: number): Promise<{ deleted: boolean }> {
    try {
      const response = await this.api.delete(`/perfil/${id}`)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.delete(`/perfil/${id}`)
      return response.data
    }
  }

  // ==================== FUNÇÕES ====================

  async getFuncoesSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean }[] }> {
    const response = await this.api.get('/funcoes/schema')
    return response.data
  }

  async listFuncoes(): Promise<{ rows: any[]; columns: string[] }> {
    const currentSlug = (localStorage.getItem('tenantSlug') || 'captar').toLowerCase()
    const cur = await this.api.get('/funcoes').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      return (await fb.get('/funcoes')).data
    })
    if (currentSlug === 'captar') return cur
    const hdr: Record<string, string> = { 'Content-Type': 'application/json', 'X-Tenant': 'captar' }
    const token = localStorage.getItem('token')
    if (token) hdr['Authorization'] = `Bearer ${token}`
    const alt = axios.create({ baseURL: API_BASE_URL, headers: hdr })
    const cap = await alt.get('/funcoes').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: hdr })
      return (await fb.get('/funcoes')).data
    })
    const rowsCur = cur.rows || []
    const rowsCap = cap.rows || []
    const mergedMap: Record<string, any> = {}
    for (const r of [...rowsCap, ...rowsCur]) {
      const key = String(r.Funcao ?? r.funcao ?? r.Descricao ?? r.descricao ?? '').toUpperCase()
      if (!mergedMap[key]) mergedMap[key] = r
    }
    return { rows: Object.values(mergedMap), columns: cur.columns || cap.columns || [] }
  }

  async createFuncao(data: any): Promise<any> {
    const response = await this.api.post('/funcoes', data)
    return response.data
  }

  async updateFuncao(id: number, data: any): Promise<any> {
    const response = await this.api.put(`/funcoes/${id}`, data)
    return response.data
  }

  async deleteFuncao(id: number): Promise<any> {
    const response = await this.api.delete(`/funcoes/${id}`)
    return response.data
  }

  // ==================== FILTROS AVANÇADOS ====================

  async applyFilter(filtro: { tipo: string; valor: string }): Promise<any[]> {
    const response = await this.api.post('/filtros/aplicar', filtro)
    return response.data
  }

  // ==================== EXPORTAÇÃO ====================

  async exportExcel(tabela: string): Promise<any> {
    const response = await this.api.post('/export/excel', { tabela }, {
      responseType: 'blob',
    })
    return response.data
  }

  async exportPdf(tabela: string): Promise<any> {
    const response = await this.api.post('/export/pdf', { tabela }, {
      responseType: 'blob',
    })
    return response.data
  }

  async exportData(tabela: string, format: 'pdf' | 'excel'): Promise<void> {
    try {
      const data = format === 'excel' ? await this.exportExcel(tabela) : await this.exportPdf(tabela)
      const url = window.URL.createObjectURL(new Blob([data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${tabela}.${format === 'excel' ? 'xlsx' : 'pdf'}`)
      document.body.appendChild(link)
      link.click()
      link.parentNode?.removeChild(link)
    } catch (error) {
      throw error
    }
  }

  // ==================== AUDITORIA ====================

  async getAuditLogs(skip: number = 0, limit: number = 100): Promise<any[]> {
    const response = await this.api.get('/audit-logs', {
      params: { skip, limit },
    })
    return response.data
  }

  async createAuditLog(data: any): Promise<any> {
    const response = await this.api.post('/audit-logs', data)
    return response.data
  }

  async getAuditLogsByUser(usuarioId: number): Promise<any[]> {
    const response = await this.api.get(`/audit-logs/usuario/${usuarioId}`)
    return response.data
  }

  // ==================== IMPORTAÇÃO ====================

  async importCsv(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await this.api.post('/import/csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  // ==================== NOTIFICAÇÕES ====================

  async getNotificacoes(usuarioId: number): Promise<any[]> {
    const response = await this.api.get(`/notificacoes/${usuarioId}`)
    return response.data
  }

  async createNotificacao(data: any): Promise<any> {
    const response = await this.api.post('/notificacoes', data)
    return response.data
  }

  async marcarNotificacaoLida(notificacaoId: number): Promise<any> {
    const response = await this.api.put(`/notificacoes/${notificacaoId}/marcar-lida`)
    return response.data
  }

  // ==================== ELEITORES ====================

  async getEleitoresSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean; maxLength?: number }[] }> {
    try {
      const response = await this.api.get('/eleitores/schema')
      return response.data
    } catch (e: any) {
      // Fallback schema
      return {
        columns: [
          { name: 'id', type: 'integer', nullable: false },
          { name: 'nome', type: 'string', nullable: false },
          { name: 'cpf', type: 'string', nullable: true },
          { name: 'celular', type: 'string', nullable: true },
          { name: 'bairro', type: 'string', nullable: true },
          { name: 'zona_eleitoral', type: 'string', nullable: true },
          { name: 'DataCadastro', type: 'datetime', nullable: true },
          { name: 'TenantLayer', type: 'string', nullable: true },
        ]
      }
    }
  }

  async getEleitores(): Promise<ApiResponse<Eleitor>> {
    try {
      const response = await this.api.get('/eleitores')
      const data = response.data
      const rows: Eleitor[] = Array.isArray(data) ? (data as Eleitor[]) : ((data.rows || []) as Eleitor[])
      const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
      const viewSlug = (localStorage.getItem('viewTenantSlug') || '').toUpperCase()
      const viewName = (localStorage.getItem('viewTenantName') || '').toUpperCase()
      if (adminCtx && viewSlug) {
        const allow = new Set([viewSlug, viewName])
        const filtered = rows.filter((r: Eleitor) => allow.has(String((r as any).TenantLayer || '').toUpperCase()))
        return { rows: filtered, columns: Array.isArray(data) ? [] : (data.columns || []) }
      }
      return { rows, columns: Array.isArray(data) ? [] : (data.columns || []) }
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/eleitores')
      const data = response.data
      const rows: Eleitor[] = Array.isArray(data) ? (data as Eleitor[]) : ((data.rows || []) as Eleitor[])
      const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
      const viewSlug = (localStorage.getItem('viewTenantSlug') || '').toUpperCase()
      const viewName = (localStorage.getItem('viewTenantName') || '').toUpperCase()
      if (adminCtx && viewSlug) {
        const allow = new Set([viewSlug, viewName])
        const filtered = rows.filter((r: Eleitor) => allow.has(String((r as any).TenantLayer || '').toUpperCase()))
        return { rows: filtered, columns: Array.isArray(data) ? [] : (data.columns || []) }
      }
      return { rows, columns: Array.isArray(data) ? [] : (data.columns || []) }
    }
  }

  async createEleitor(data: any): Promise<any> {
    const response = await this.api.post('/eleitores', data)
    return response.data
  }

  async updateEleitor(id: number, data: any): Promise<any> {
    const response = await this.api.put(`/eleitores/${id}`, data)
    return response.data
  }

  async deleteEleitor(id: number): Promise<any> {
    const response = await this.api.delete(`/eleitores/${id}`)
    return response.data
  }

  // ==================== ATIVISTAS ====================

  async getAtivistasSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean; maxLength?: number }[] }> {
    try {
      const response = await this.api.get('/ativistas/schema')
      return response.data
    } catch (e: any) {
      // Fallback schema
      return {
        columns: [
          { name: 'id', type: 'integer', nullable: false },
          { name: 'nome', type: 'string', nullable: false },
          { name: 'tipo_apoio', type: 'string', nullable: true },
          { name: 'area_atuacao', type: 'string', nullable: true },
          { name: 'DataCadastro', type: 'datetime', nullable: true },
          { name: 'TenantLayer', type: 'string', nullable: true },
        ]
      }
    }
  }

  async getAtivistas(): Promise<ApiResponse<Ativista>> {
    try {
      const response = await this.api.get('/ativistas')
      const data = response.data
      const rows: Ativista[] = Array.isArray(data) ? (data as Ativista[]) : ((data.rows || []) as Ativista[])
      const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
      const viewSlug = (localStorage.getItem('viewTenantSlug') || '').toUpperCase()
      const viewName = (localStorage.getItem('viewTenantName') || '').toUpperCase()
      if (adminCtx && viewSlug) {
        const allow = new Set([viewSlug, viewName])
        const filtered = rows.filter((r: Ativista) => allow.has(String((r as any).TenantLayer || '').toUpperCase()))
        return { rows: filtered, columns: Array.isArray(data) ? [] : (data.columns || []) }
      }
      return { rows, columns: Array.isArray(data) ? [] : (data.columns || []) }
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/ativistas')
      const data = response.data
      const rows: Ativista[] = Array.isArray(data) ? (data as Ativista[]) : ((data.rows || []) as Ativista[])
      const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
      const viewSlug = (localStorage.getItem('viewTenantSlug') || '').toUpperCase()
      const viewName = (localStorage.getItem('viewTenantName') || '').toUpperCase()
      if (adminCtx && viewSlug) {
        const allow = new Set([viewSlug, viewName])
        const filtered = rows.filter((r: Ativista) => allow.has(String((r as any).TenantLayer || '').toUpperCase()))
        return { rows: filtered, columns: Array.isArray(data) ? [] : (data.columns || []) }
      }
      return { rows, columns: Array.isArray(data) ? [] : (data.columns || []) }
    }
  }

  async createAtivista(data: any): Promise<any> {
    const response = await this.api.post('/ativistas', data)
    return response.data
  }

  async updateAtivista(id: number, data: any): Promise<any> {
    const response = await this.api.put(`/ativistas/${id}`, data)
    return response.data
  }

  async deleteAtivista(id: number): Promise<any> {
    const response = await this.api.delete(`/ativistas/${id}`)
    return response.data
  }

  async listCandidatos(): Promise<{ rows: any[]; columns: string[] }> {
    const response = await this.api.get('/candidatos')
    return response.data
  }

  async createCandidato(payload: any): Promise<{ id: number }> {
    const response = await this.api.post('/candidatos', payload)
    return response.data
  }

  async updateCandidato(id: number, payload: any): Promise<{ id: number }> {
    const response = await this.api.put(`/candidatos/${id}`, payload)
    return response.data
  }

  async deleteCandidato(id: number): Promise<{ deleted: boolean }> {
    const response = await this.api.delete(`/candidatos/${id}`)
    return response.data
  }

  async listEleicoes(): Promise<{ rows: any[]; columns: string[] }> {
    const response = await this.api.get('/eleicoes')
    return response.data
  }

  async createEleicao(payload: any): Promise<{ id: number }> {
    const response = await this.api.post('/eleicoes', payload)
    return response.data
  }

  async updateEleicao(id: number, payload: any): Promise<{ id: number }> {
    const response = await this.api.put(`/eleicoes/${id}`, payload)
    return response.data
  }

  async deleteEleicao(id: number): Promise<{ deleted: boolean }> {
    const response = await this.api.delete(`/eleicoes/${id}`)
    return response.data
  }

  async listMetas(): Promise<{ rows: any[]; columns: string[] }> {
    const response = await this.api.get('/metas')
    return response.data
  }

  async createMeta(payload: any): Promise<{ id: number }> {
    const response = await this.api.post('/metas', payload)
    return response.data
  }

  async updateMeta(id: number, payload: any): Promise<{ id: number }> {
    const response = await this.api.put(`/metas/${id}`, payload)
    return response.data
  }

  async deleteMeta(id: number): Promise<{ deleted: boolean }> {
    const response = await this.api.delete(`/metas/${id}`)
    return response.data
  }

  // ==================== USUÁRIOS ====================
  async getUsuariosSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean; maxLength?: number }[] }> {
    try {
      const response = await this.api.get('/usuarios/schema')
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/usuarios/schema')
      return response.data
    }
  }

  async listUsuarios(): Promise<{ rows: any[]; columns: string[] }> {
    const getTenantInfo = async (): Promise<{ id?: number; nome?: string; slug?: string }> => {
      try {
        const slug = localStorage.getItem('tenantSlug') || 'captar'
        const nameLS = localStorage.getItem('tenantName') || ''
        const res = await this.listTenants()
        const rows = res.rows || []
        const tByName = rows.find((r: any) => String(r.Nome ?? r.nome).toUpperCase() === String(nameLS).toUpperCase())
        const tBySlug = rows.find((r: any) => String(r.Slug ?? r.slug) === slug)
        const t = tByName || tBySlug
        return { id: t?.IdTenant ?? t?.id, nome: t?.Nome ?? t?.nome, slug }
      } catch {
        return { slug: localStorage.getItem('tenantSlug') || 'captar', nome: localStorage.getItem('tenantName') || '' }
      }
    }
    try {
      const response = await this.api.get('/usuarios')
      const data = response.data
      const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
      const viewSlug = (localStorage.getItem('viewTenantSlug') || '').toUpperCase()
      const viewName = (localStorage.getItem('viewTenantName') || '').toUpperCase()
      const tenant = await getTenantInfo()
      if ((tenant.slug || '').toLowerCase() !== 'captar') {
        const rows = (data.rows || []).filter((r: any) => Number(r.IdTenant ?? r.idTenant) === Number(tenant.id))
        return { rows, columns: data.columns || [] }
      }
      if (adminCtx && viewSlug) {
        const allow = new Set([viewSlug, viewName])
        const rows = (data.rows || []).filter((r: any) => allow.has(String(r.TenantLayer || '').toUpperCase()))
        return { rows, columns: data.columns || [] }
      }
      return data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/usuarios')
      const data = response.data
      const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
      const viewSlug = (localStorage.getItem('viewTenantSlug') || '').toUpperCase()
      const viewName = (localStorage.getItem('viewTenantName') || '').toUpperCase()
      const tenant = await getTenantInfo()
      if ((tenant.slug || '').toLowerCase() !== 'captar') {
        const rows = (data.rows || []).filter((r: any) => Number(r.IdTenant ?? r.idTenant) === Number(tenant.id))
        return { rows, columns: data.columns || [] }
      }
      if (adminCtx && viewSlug) {
        const allow = new Set([viewSlug, viewName])
        const rows = (data.rows || []).filter((r: any) => allow.has(String(r.TenantLayer || '').toUpperCase()))
        return { rows, columns: data.columns || [] }
      }
      return data
    }
  }

  async createUsuario(payload: any): Promise<{ id: number }> {
    try {
      const response = await this.api.post('/usuarios', payload)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post('/usuarios', payload)
      return response.data
    }
  }

  async updateUsuario(id: number, data: any): Promise<{ id: number }> {
    try {
      const response = await this.api.put(`/usuarios/${id}`, data)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.put(`/usuarios/${id}`, data)
      return response.data
    }
  }

  async uploadUsuarioFoto(id: number, payload: { file?: File; data_url?: string }): Promise<{ saved: boolean; path: string }> {
    const form = new FormData()
    if (payload.file) form.append('file', payload.file)
    if (payload.data_url) form.append('data_url', payload.data_url)
    const response = await this.api.post(`/usuarios/${id}/foto`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  }

  async deleteUsuario(id: number): Promise<{ deleted: boolean }> {
    try {
      const response = await this.api.delete(`/usuarios/${id}`)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.delete(`/usuarios/${id}`)
      return response.data
    }
  }

  // ==================== DASHBOARD ====================

  async getDashboardStats(): Promise<any> {
    const adminCtx = (localStorage.getItem('adminContext') || '') === '1'
    const viewSlug = (localStorage.getItem('viewTenantSlug') || '').trim()
    const hdrs: Record<string, string> = {}
    if (adminCtx && viewSlug) hdrs['X-View-Tenant'] = viewSlug
    const response = await this.api.get('/dashboard/stats', { headers: hdrs })
    const data = response.data || {}
    try {
      const slug = (localStorage.getItem('tenantSlug') || 'captar').toLowerCase()
      if (slug !== 'captar') {
        const users = await this.listUsuarios()
        data.total_usuarios = (users.rows || []).length
      } else if (adminCtx && viewSlug) {
        const users = await this.listUsuarios()
        data.total_usuarios = (users.rows || []).length
        try {
          const eleitores = await this.getEleitores()
          data.total_eleitores = (eleitores.rows || eleitores || []).length
          const ativistas = await this.getAtivistas()
          data.total_ativistas = (ativistas.rows || ativistas || []).length
        } catch {}
      }
    } catch {}
    return data
  }

  async getTopAtivistas(): Promise<any[]> {
    const response = await this.api.get('/dashboard/top-ativistas')
    return response.data
  }

  async getTopUsuarios(): Promise<any[]> {
    const response = await this.api.get('/dashboard/top-usuarios')
    return response.data
  }

  async getTopSupervisores(): Promise<any[]> {
    const response = await this.api.get('/dashboard/top-supervisores')
    return response.data
  }

  async getTopCoordenadores(): Promise<any[]> {
    const response = await this.api.get('/dashboard/top-coordenadores')
    return response.data
  }

  async getTopBairros(): Promise<any[]> {
    const response = await this.api.get('/dashboard/top-bairros')
    return response.data
  }

  async getTopZonas(): Promise<any[]> {
    const response = await this.api.get('/dashboard/top-zonas')
    return response.data
  }
  async listCoordenadores(): Promise<{ rows: any[] }> {
    const res = await this.listUsuarios()
    const rows = (res.rows || []).filter((u: any) => String(u.Funcao || u.funcao).toUpperCase().trim() === 'COORDENADOR' || String(u.Funcao || u.funcao).toUpperCase().trim() === 'ADMINISTRADOR')
    return { rows }
  }
  async listSupervisores(coordenador: string): Promise<{ rows: any[] }> {
    const res = await this.listUsuarios()
    const rows = (res.rows || []).filter((u: any) => String(u.Funcao || u.funcao).toUpperCase().trim() === 'SUPERVISOR' && String(u.Coordenador || u.coordenador).trim() === String(coordenador).trim())
    return { rows }
  }
  
  // ==================== TENANTS ====================
  async getTenantsSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean }[] }> {
    try {
      const response = await this.api.get('/tenants/schema')
      return response.data
    } catch (e1: any) {
      try {
        const response = await this.api.get('/tenants/schema', { baseURL: 'http://localhost:8001/api' })
        return response.data
      } catch (e3: any) {
        const origin = typeof window !== 'undefined' ? window.location.origin : ''
        const base = origin ? `${origin}/api` : 'http://localhost:8001/api'
        const response = await this.api.get('/tenants/schema', { baseURL: base })
        return response.data
      }
    }
  }

  async listTenants(): Promise<{ rows: any[]; columns: string[] }> {
    try {
      const response = await this.api.get('/tenants')
      return response.data
    } catch (e1: any) {
      try {
        const response = await this.api.get('/tenants', { baseURL: 'http://localhost:8001/api' })
        return response.data
      } catch (e3: any) {
        const origin = typeof window !== 'undefined' ? window.location.origin : ''
        const base = origin ? `${origin}/api` : 'http://localhost:8001/api'
        const response = await this.api.get('/tenants', { baseURL: base })
        return response.data
      }
    }
  }

  async createTenant(payload: any): Promise<{ id: number }> {
    try {
      const response = await this.api.post('/tenants', payload)
      return response.data
    } catch (e1: any) {
      try {
        const response = await this.api.post('/tenants', payload, { baseURL: 'http://localhost:8001/api' })
        return response.data
      } catch (e2: any) {
        const origin = typeof window !== 'undefined' ? window.location.origin : ''
        const base = origin ? `${origin}/api` : 'http://localhost:8001/api'
        const response = await this.api.post('/tenants', payload, { baseURL: base })
        return response.data
      }
    }
  }

  async updateTenant(id: number, payload: any): Promise<{ id: number }> {
    try {
      const response = await this.api.put(`/tenants/${id}`, payload)
      return response.data
    } catch (e1: any) {
      try {
        const response = await this.api.put(`/tenants/${id}`, payload, { baseURL: 'http://localhost:8001/api' })
        return response.data
      } catch (e2: any) {
        const origin = typeof window !== 'undefined' ? window.location.origin : ''
        const base = origin ? `${origin}/api` : 'http://localhost:8001/api'
        const response = await this.api.put(`/tenants/${id}`, payload, { baseURL: base })
        return response.data
      }
    }
  }

  async deleteTenant(id: number): Promise<{ deleted: boolean }> {
    try {
      const response = await this.api.delete(`/tenants/${id}`)
      return response.data
    } catch (e1: any) {
      try {
        const response = await this.api.delete(`/tenants/${id}`, { baseURL: 'http://localhost:8001/api' })
        return response.data
      } catch (e2: any) {
        const origin = typeof window !== 'undefined' ? window.location.origin : ''
        const base = origin ? `${origin}/api` : 'http://localhost:8001/api'
        const response = await this.api.delete(`/tenants/${id}`, { baseURL: base })
        return response.data
      }
    }
  }

  async deleteTenantAndDb(slug: string): Promise<{ ok: boolean; deleted: number; dropped: string }> {
    try {
      const response = await this.api.delete('/tenants/delete_all', { data: { slug } })
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.delete('/tenants/delete_all', { data: { slug } })
      return response.data
    }
  }


  async provisionTenant(body: { nome: string; slug: string; db_name: string; db_host: string; db_port: string; db_user: string; db_password: string }): Promise<{ ok: boolean; idTenant: number; dsn: string; actions: string[] }> {
    try {
      const response = await this.api.post('/tenants/provision', body)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post('/tenants/provision', body)
      return response.data
    }
  }

  async recreateTenantDb(slug: string): Promise<{ ok: boolean; idTenant: number; dsn: string; actions: string[] }> {
    try {
      const response = await this.api.post(`/tenants/${slug}/recreate_db`)
      return response.data
    } catch (e1: any) {
      try {
        const response = await this.api.post(`/tenants/${slug}/recreate_db`, undefined, { baseURL: 'http://localhost:8001/api' })
        return response.data
      } catch (e2: any) {
        const origin = typeof window !== 'undefined' ? window.location.origin : ''
        const base = origin ? `${origin}/api` : 'http://localhost:8001/api'
        const response = await this.api.post(`/tenants/${slug}/recreate_db`, undefined, { baseURL: base })
        return response.data
      }
    }
  }

  async setTenantDsn(slug: string, dsn: string): Promise<{ ok: boolean; idTenant: number; actions: string[] }> {
    try {
      const response = await this.api.post(`/tenants/${slug}/set_dsn`, { dsn })
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post(`/tenants/${slug}/set_dsn`, { dsn })
      return response.data
    }
  }

  async migrateAllTenants(): Promise<{ ok: boolean; results: any[] }> {
    try {
      const response = await this.api.post('/admin/migrate_all_tenants')
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post('/admin/migrate_all_tenants')
      return response.data
    }
  }

  async migrateTenantData(slug: string): Promise<{ ok: boolean; migrated: number }> {
    try {
      const response = await this.api.post('/tenants/migrate_data', { slug })
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8001/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post('/tenants/migrate_data', { slug })
      return response.data
    }
  }
  // ==================== INTEGRAÇÕES ====================

  async testarIntegracao(payload: { base_url: string; uf?: string; dataset?: string; municipio?: string }): Promise<{ connected: boolean; status_code: number }> {
    const response = await this.api.post('/integracoes/testar', payload)
    return response.data
  }

  async salvarIntegracaoConfig(cfg: IntegracaoConfig): Promise<{ id: number; saved: boolean }> {
    const response = await this.api.post('/integracoes/config', cfg)
    return response.data
  }

  async obterIntegracaoConfig(): Promise<any> {
    const response = await this.api.get('/integracoes/config')
    return response.data
  }

  async listarMunicipios(uf: string): Promise<{ uf: string; municipios: { id: number; nome: string }[] }> {
    const response = await this.api.get(`/integracoes/municipios/${uf}`)
    return response.data
  }

  async listarRecursosCkan(dataset: string, uf?: string): Promise<{ resources: { id: string; name: string; format: string; url: string }[] }> {
    const response = await this.api.post('/integracoes/ckan/resources', { dataset, uf })
    return response.data
  }

  async previewRecursoCkan(resource_url: string, limit: number = 15): Promise<{ columns: string[]; rows: any[] }> {
    const response = await this.api.post('/integracoes/ckan/preview', { resource_url, limit })
    return response.data
  }
  
  async getEvolutionApiKeyMasked(): Promise<{ hasKey: boolean; keyMasked: string }> {
    const response = await this.api.get('/integracoes/evolution/key')
    return response.data
  }
  
  async testEvolutionApi(): Promise<{ ok: boolean; status_code: number; message?: string; version?: string }> {
    const response = await this.api.get('/integracoes/evolution/test')
    return response.data
  }
}

export default new ApiService()
