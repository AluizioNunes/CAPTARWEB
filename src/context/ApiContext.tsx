import { createContext, useContext, PropsWithChildren } from 'react'
import apiService from '../services/api'

const ApiContext = createContext(apiService)

export function ApiProvider({ children }: PropsWithChildren<{}>) {
  return (
    <ApiContext.Provider value={apiService}>
      {children}
    </ApiContext.Provider>
  )
}

export function useApi() {
  return useContext(ApiContext)
}