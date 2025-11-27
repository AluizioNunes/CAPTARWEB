import { create } from 'zustand'
import { User } from '../types'
import { parseISO, isValid } from 'date-fns'

interface AuthStore {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setIsLoading: (isLoading: boolean) => void
  logout: () => void
  login: (user: User, token: string) => void
}

const storedUser = localStorage.getItem('user')
let initialUser: User | null = null
if (storedUser) {
  try {
    const u = JSON.parse(storedUser) as User
    if (u && u.login_time) {
      const iso = parseISO(u.login_time)
      if (isValid(iso)) {
        initialUser = u
      } else {
        const d = new Date(u.login_time)
        if (isValid(d)) {
          u.login_time = d.toISOString()
        } else {
          u.login_time = new Date().toISOString()
        }
        localStorage.setItem('user', JSON.stringify(u))
        initialUser = u
      }
    } else {
      initialUser = u
    }
  } catch {
    initialUser = null
    localStorage.removeItem('user')
  }
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: initialUser,
  token: localStorage.getItem('token'),
  isLoading: false,
  isAuthenticated: !!localStorage.getItem('token'),

  setUser: (user) => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user))
    } else {
      localStorage.removeItem('user')
    }
    set({ user })
  },

  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
    set({ token, isAuthenticated: !!token })
  },

  setIsLoading: (isLoading) => set({ isLoading }),

  logout: () => {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    set({ user: null, token: null, isAuthenticated: false })
  },

  login: (user, token) => {
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('token', token)
    set({ user, token, isAuthenticated: true })
  },
}))
