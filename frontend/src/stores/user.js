import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('access_token') || '')

  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')

  async function login(credentials) {
    const { data } = await api.post('/api/login', credentials)
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    return data
  }

  async function register(userData) {
    const { data } = await api.post('/api/register', userData)
    return data
  }

  async function logout() {
    try {
      await api.post('/api/logout')
    } catch (e) {
      // ignore
    }
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  }

  async function fetchUser() {
    try {
      const { data } = await api.get('/api/me')
      user.value = data
      localStorage.setItem('user', JSON.stringify(data))
    } catch (e) {
      token.value = ''
      user.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    }
  }

  return { user, token, isLoggedIn, username, login, register, logout, fetchUser }
})
