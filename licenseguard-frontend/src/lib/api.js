/**
 * One axios instance for the whole app.
 *
 * Two interceptors do the boring work so no page has to think about auth:
 *   request  - attach the access token
 *   response - on a 401, silently swap the refresh token for a new access
 *              token and replay the original request exactly once
 */
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const TOKEN_KEY = 'lg_access'
export const REFRESH_KEY = 'lg_refresh'

export const tokens = {
  get access() { return localStorage.getItem(TOKEN_KEY) },
  get refresh() { return localStorage.getItem(REFRESH_KEY) },
  set({ access, refresh }) {
    if (access) localStorage.setItem(TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const api = axios.create({ baseURL: `${BASE_URL}/api`, headers: { 'Content-Type': 'application/json' } })

api.interceptors.request.use((config) => {
  const token = tokens.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const isAuthCall = original?.url?.includes('/auth/')

    if (error.response?.status === 401 && !original._retried && !isAuthCall && tokens.refresh) {
      original._retried = true
      try {
        // Collapse parallel 401s into a single refresh request.
        refreshing = refreshing || axios.post(`${BASE_URL}/api/auth/refresh/`, { refresh: tokens.refresh })
        const { data } = await refreshing
        refreshing = null
        tokens.set({ access: data.access, refresh: data.refresh })
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (refreshError) {
        refreshing = null
        tokens.clear()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  },
)

/** Turns a DRF error body into one readable sentence. */
export function readError(error, fallback = 'Something went wrong.') {
  const data = error?.response?.data
  if (!data) return error?.message || fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  const [field, messages] = Object.entries(data)[0] || []
  if (!field) return fallback
  return `${field}: ${Array.isArray(messages) ? messages[0] : messages}`
}

/** DRF pagination returns {results}; plain lists do not. Normalise both. */
export const rows = (data) => (Array.isArray(data) ? data : data?.results || [])

export default api
