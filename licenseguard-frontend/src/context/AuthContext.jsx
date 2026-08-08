import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { tokens } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // On boot, if we still hold a token, ask the API who we are.
  useEffect(() => {
    if (!tokens.access) { setLoading(false); return }
    api.get('/auth/me/')
      .then(({ data }) => setUser(data))
      .catch(() => tokens.clear())
      .finally(() => setLoading(false))
  }, [])

  const finish = (data) => {
    tokens.set({ access: data.access, refresh: data.refresh })
    if (data.user) setUser(data.user)
    else api.get('/auth/me/').then(({ data: me }) => setUser(me))
    return data
  }

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/auth/login/', { email, password })
    return finish(data)
  }, [])

  const signup = useCallback(async (payload) => {
    const { data } = await api.post('/auth/signup/', payload)
    return finish(data)
  }, [])

  const loginWithGoogle = useCallback(async (credential) => {
    const { data } = await api.post('/auth/google/', { credential })
    return finish(data)
  }, [])

  const logout = useCallback(() => {
    tokens.clear()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
