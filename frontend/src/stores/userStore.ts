import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '@/types'

interface UserState {
  user: User | null
  token: string | null
  isLoggedIn: boolean
  
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  login: (user: User, token: string) => void
  logout: () => void
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoggedIn: false,

      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),

      login: (user, token) => {
        localStorage.setItem('token', token)
        set({ user, token, isLoggedIn: true })
      },

      logout: () => {
        localStorage.removeItem('token')
        set({ user: null, token: null, isLoggedIn: false })
      },
    }),
    {
      name: 'user-store',
      partialize: (state) => ({ user: state.user, isLoggedIn: state.isLoggedIn }),
    }
  )
)
