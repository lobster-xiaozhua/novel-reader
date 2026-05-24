import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { TagView } from '@/types'

interface TagsState {
  visitedViews: TagView[]
  cachedViews: string[]
  
  addView: (view: TagView) => void
  removeView: (view: TagView) => void
  removeOthers: (view: TagView) => void
  removeAll: () => void
  addCachedView: (name: string) => void
  removeCachedView: (name: string) => void
}

export const useTagsStore = create<TagsState>()(
  persist(
    (set) => ({
      visitedViews: [],
      cachedViews: [],

      addView: (view) =>
        set((state) => {
          if (state.visitedViews.some((v) => v.path === view.path)) {
            return state
          }
          return { visitedViews: [...state.visitedViews, view] }
        }),

      removeView: (view) =>
        set((state) => ({
          visitedViews: state.visitedViews.filter((v) => v.path !== view.path),
        })),

      removeOthers: (view) =>
        set((state) => ({
          visitedViews: state.visitedViews.filter(
            (v) => v.path === view.path || v.path === '/admin-dashboard'
          ),
        })),

      removeAll: () =>
        set((state) => ({
          visitedViews: state.visitedViews.filter((v) => v.path === '/admin-dashboard'),
        })),

      addCachedView: (name) =>
        set((state) => {
          if (state.cachedViews.includes(name)) return state
          return { cachedViews: [...state.cachedViews, name] }
        }),

      removeCachedView: (name) =>
        set((state) => ({
          cachedViews: state.cachedViews.filter((v) => v !== name),
        })),
    }),
    {
      name: 'tags-store',
      partialize: (state) => ({ visitedViews: state.visitedViews }),
    }
  )
)
