import axios, { AxiosInstance } from 'axios'
import { LoginRequest, LoginResponse, User, IntegracaoConfig } from '../types'

const API_BASE_URL = '/api'

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
        const tenant = localStorage.getItem('tenantSlug') || 'captar'
        ;(config.headers as any)['X-Tenant'] = tenant
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
          const fb = axios.create({ baseURL: 'http://localhost:8000', headers: { 'Content-Type': 'application/json' } })
          const resp3 = await fb.get('/api/health/db')
          return resp3.data
        } catch (e3: any) {
          const fb2 = axios.create({ baseURL: 'http://localhost:8000', headers: { 'Content-Type': 'application/json' } })
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
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/perfil/schema')
      return response.data
    }
  }

  async listPerfil(): Promise<{ rows: any[]; columns: string[] }> {
    const currentSlug = (localStorage.getItem('tenantSlug') || 'captar').toLowerCase()
    // fetch current tenant
    const cur = await this.api.get('/perfil').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      return (await fb.get('/perfil')).data
    })
    if (currentSlug === 'captar') return cur
    // additionally fetch CAPTAR
    const hdr: Record<string, string> = { 'Content-Type': 'application/json', 'X-Tenant': 'captar' }
    const token = localStorage.getItem('token')
    if (token) hdr['Authorization'] = `Bearer ${token}`
    const alt = axios.create({ baseURL: API_BASE_URL, headers: hdr })
    const cap = await alt.get('/perfil').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: hdr })
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
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      return (await fb.get('/funcoes')).data
    })
    if (currentSlug === 'captar') return cur
    const hdr: Record<string, string> = { 'Content-Type': 'application/json', 'X-Tenant': 'captar' }
    const token = localStorage.getItem('token')
    if (token) hdr['Authorization'] = `Bearer ${token}`
    const alt = axios.create({ baseURL: API_BASE_URL, headers: hdr })
    const cap = await alt.get('/funcoes').then(r => r.data).catch(async () => {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: hdr })
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

  async getEleitores(): Promise<any[]> {
    const response = await this.api.get('/eleitores')
    return response.data
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

  async getAtivistas(): Promise<any[]> {
    const response = await this.api.get('/ativistas')
    return response.data
  }

  // ==================== USUÁRIOS ====================
  async getUsuariosSchema(): Promise<{ columns: { name: string; type: string; nullable: boolean; maxLength?: number }[] }> {
    try {
      const response = await this.api.get('/usuarios/schema')
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
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
      const tenant = await getTenantInfo()
      if ((tenant.slug || '').toLowerCase() !== 'captar') {
        const rows = (data.rows || []).filter((r: any) => Number(r.IdTenant ?? r.idTenant) === Number(tenant.id))
        return { rows, columns: data.columns || [] }
      }
      return data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.get('/usuarios')
      const data = response.data
      const tenant = await getTenantInfo()
      if ((tenant.slug || '').toLowerCase() !== 'captar') {
        const rows = (data.rows || []).filter((r: any) => Number(r.IdTenant ?? r.idTenant) === Number(tenant.id))
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
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.post('/usuarios', payload)
      return response.data
    }
  }

  async updateUsuario(id: number, data: any): Promise<{ id: number }> {
    try {
      const response = await this.api.put(`/usuarios/${id}`, data)
      return response.data
    } catch (e: any) {
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
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
      const fb = axios.create({ baseURL: 'http://localhost:8000/api', headers: { 'Content-Type': 'application/json' } })
      const response = await fb.delete(`/usuarios/${id}`)
      return response.data
    }
  }

  // ==================== DASHBOARD ====================

  async getDashboardStats(): Promise<any> {
    const response = await this.api.get('/dashboard/stats')
    const data = response.data || {}
    try {
      const slug = localStorage.getItem('tenantSlug') || 'captar'
      if (slug.toLowerCase() !== 'captar') {
        const users = await this.listUsuarios()
        data.total_usuarios = (users.rows || []).length
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
    const response = await this.api.get('/tenants/schema')
    return response.data
  }

  async listTenants(): Promise<{ rows: any[]; columns: string[] }> {
    const response = await this.api.get('/tenants')
    return response.data
  }

  async createTenant(payload: any): Promise<{ id: number }> {
    const response = await this.api.post('/tenants', payload)
    return response.data
  }

  async updateTenant(id: number, payload: any): Promise<{ id: number }> {
    const response = await this.api.put(`/tenants/${id}`, payload)
    return response.data
  }

  async deleteTenant(id: number): Promise<{ deleted: boolean }> {
    const response = await this.api.delete(`/tenants/${id}`)
    return response.data
  }

  async listTenantParametros(tenantId: number): Promise<{ rows: any[]; columns: string[] }> {
    const response = await this.api.get(`/tenant-parametros/${tenantId}`)
    return response.data
  }

  async createTenantParametro(tenantId: number, payload: any): Promise<{ id: number }> {
    const response = await this.api.post(`/tenant-parametros/${tenantId}`, payload)
    return response.data
  }

  async updateTenantParametro(tenantId: number, id: number, payload: any): Promise<{ id: number }> {
    const response = await this.api.put(`/tenant-parametros/${tenantId}/${id}`, payload)
    return response.data
  }

  async deleteTenantParametro(tenantId: number, id: number): Promise<{ deleted: boolean }> {
    const response = await this.api.delete(`/tenant-parametros/${tenantId}/${id}`)
    return response.data
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
}

export default new ApiService()
