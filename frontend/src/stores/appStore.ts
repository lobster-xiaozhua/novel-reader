import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SidebarState {
  opened: boolean
  withoutAnimation: boolean
}

interface AppState {
  sidebar: SidebarState
  device: 'mobile' | 'desktop'
  layout: 'vertical' | 'horizontal' | 'mix'
  
  toggleSidebar: () => void
  closeSidebar: () => void
  openSidebar: () => void
  toggleDevice: (device: 'mobile' | 'desktop') => void
  setLayout: (layout: 'vertical' | 'horizontal' | 'mix') => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      sidebar: {
        opened: true,
        withoutAnimation: false,
      },
      device: 'desktop',
      layout: 'vertical',

      toggleSidebar: () =>
        set((state) => ({
          sidebar: {
            opened: !state.sidebar.opened,
            withoutAnimation: false,
          },
        })),

      closeSidebar: () =>
        set({
          sidebar: { opened: false, withoutAnimation: false },
        }),

      openSidebar: () =>
        set({
          sidebar: { opened: true, withoutAnimation: false },
        }),

      toggleDevice: (device) => set({ device }),

      setLayout: (layout) => set({ layout }),
    }),
    {
      name: 'app-store',
      partialize: (state) => ({ sidebar: state.sidebar, layout: state.layout }),
    }
  )
)
