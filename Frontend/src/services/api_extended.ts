import axios, { AxiosInstance } from 'axios'
import { LoginRequest, LoginResponse, User } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

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
  }

  // ==================== AUTENTICAÇÃO ====================

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.api.post('/auth/login', credentials)
    return response.data
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

  // ==================== FUNÇÕES ====================

  async getFuncoes(): Promise<any[]> {
    const response = await this.api.get('/funcoes')
    return response.data
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

  async getUsuarios(): Promise<any[]> {
    const response = await this.api.get('/usuarios')
    return response.data
  }

  // ==================== DASHBOARD ====================

  async getDashboardStats(): Promise<any> {
    const response = await this.api.get('/dashboard/stats')
    return response.data
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
}

export default new ApiService()
