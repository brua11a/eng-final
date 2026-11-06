import { defineStore } from 'pinia'
import { login as apiLogin, setAuthToken } from '../api/client'

const STORAGE_KEY = 'eng_final_auth'

function loadPersisted() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function persist(state) {
  sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      token: state.token,
      idx: state.idx,
      email: state.email,
      roles: state.roles,
    }),
  )
}

export const useAuthStore = defineStore('auth', {
  state: () => {
    const saved = loadPersisted()
    if (saved?.token) setAuthToken(saved.token)
    return {
      token: saved?.token ?? null,
      idx: saved?.idx ?? null,
      email: saved?.email ?? null,
      roles: saved?.roles ?? [],
    }
  },
  getters: {
    isLoggedIn: (s) => !!s.token,
    hasStudent: (s) => s.roles.includes('Student'),
    hasTeacher: (s) => s.roles.includes('Teacher') || s.roles.includes('Admin'),
    hasAdmin: (s) => s.roles.includes('Admin'),
    visibleTabs(state) {
      const tabs = []
      if (state.token) tabs.push({ name: 'catalogue', label: 'Catalogue', path: '/catalogue' })
      if (state.roles.includes('Student'))
        tabs.push({ name: 'student', label: 'Student', path: '/student' })
      if (state.roles.includes('Teacher') || state.roles.includes('Admin'))
        tabs.push({ name: 'teacher', label: 'Teacher', path: '/teacher' })
      if (state.roles.includes('Admin'))
        tabs.push({ name: 'admin', label: 'Admin', path: '/admin' })
      return tabs
    },
    defaultRoute() {
      if (this.hasStudent && !this.roles.includes('Teacher') && !this.hasAdmin) {
        return '/student/schedule'
      }
      if (this.roles.includes('Teacher') && !this.hasStudent) {
        return '/teacher/schedule'
      }
      return this.visibleTabs[0]?.path ?? '/login'
    },
  },
  actions: {
    async login(email, password) {
      const data = await apiLogin(email, password)
      if (!data.ok) {
        return { ok: false, err: data.err || 'Login failed' }
      }
      this.token = data.token
      this.idx = data.idx
      this.email = data.email ?? email
      this.roles = data.roles ?? []
      setAuthToken(data.token)
      persist(this)
      return { ok: true }
    },
    logout() {
      this.token = null
      this.idx = null
      this.email = null
      this.roles = []
      setAuthToken(null)
      sessionStorage.removeItem(STORAGE_KEY)
    },
  },
})
