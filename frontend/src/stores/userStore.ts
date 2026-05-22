import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '@/types'
import { post } from '@/utils/http'

interface UserState {
  user: User | null
  isLoggedIn: boolean

  setUser: (user: User | null) => void
  login: (user: User) => void
  logout: () => void
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      isLoggedIn: false,

      setUser: (user) => set({ user }),

      login: (user) => {
        set({ user, isLoggedIn: true })
      },

      logout: () => {
        post('/auth/logout/').catch(() => {})
        set({ user: null, isLoggedIn: false })
      },
    }),
    {
      name: 'user-store',
      partialize: (state) => ({ user: state.user, isLoggedIn: state.isLoggedIn }),
    }
  )
)
