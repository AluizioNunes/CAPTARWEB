import { createContext, useContext, PropsWithChildren, useMemo } from 'react'
import apiService from '../services/api'

const ApiContext = createContext(apiService)

export function ApiProvider({ children }: PropsWithChildren<{}>) {
  const svc = useMemo(() => {
    const cache = new Map<string, any>()
    const getKey = (name: string, args: any[]) => {
      const slug = (typeof window !== 'undefined' ? localStorage.getItem('tenantSlug') : null) || 'captar'
      const view = (typeof window !== 'undefined' ? localStorage.getItem('viewTenantSlug') : null) || ''
      return `${slug}:${view}:${name}:${JSON.stringify(args)}`
    }
    const asAny = apiService as any
    const orig = {
      listTenants: asAny.listTenants.bind(apiService),
      listUsuarios: asAny.listUsuarios.bind(apiService),
      listPerfil: asAny.listPerfil.bind(apiService),
      listFuncoes: asAny.listFuncoes.bind(apiService),
      createUsuario: asAny.createUsuario.bind(apiService),
      updateUsuario: asAny.updateUsuario.bind(apiService),
      deleteUsuario: asAny.deleteUsuario.bind(apiService),
      uploadUsuarioFoto: asAny.uploadUsuarioFoto.bind(apiService),
    }
    asAny.listTenants = async () => {
      const k = getKey('listTenants', [])
      if (cache.has(k)) return cache.get(k)
      const res = await orig.listTenants()
      cache.set(k, res)
      return res
    }
    asAny.listUsuarios = async () => {
      const k = getKey('listUsuarios', [])
      if (cache.has(k)) return cache.get(k)
      const res = await orig.listUsuarios()
      cache.set(k, res)
      return res
    }
    asAny.listPerfil = async () => {
      const k = getKey('listPerfil', [])
      if (cache.has(k)) return cache.get(k)
      const res = await orig.listPerfil()
      cache.set(k, res)
      return res
    }
    asAny.listFuncoes = async () => {
      const k = getKey('listFuncoes', [])
      if (cache.has(k)) return cache.get(k)
      const res = await orig.listFuncoes()
      cache.set(k, res)
      return res
    }
    asAny.createUsuario = async (payload: any) => {
      const res = await orig.createUsuario(payload)
      cache.clear()
      return res
    }
    asAny.updateUsuario = async (id: number, payload: any) => {
      const res = await orig.updateUsuario(id, payload)
      cache.clear()
      return res
    }
    asAny.deleteUsuario = async (id: number) => {
      const res = await orig.deleteUsuario(id)
      cache.clear()
      return res
    }
    asAny.uploadUsuarioFoto = async (id: number, payload: any) => {
      const res = await orig.uploadUsuarioFoto(id, payload)
      cache.clear()
      return res
    }
    return apiService
  }, [])
  return (
    <ApiContext.Provider value={svc}>
      {children}
    </ApiContext.Provider>
  )
}

export function useApi() {
  return useContext(ApiContext)
}
