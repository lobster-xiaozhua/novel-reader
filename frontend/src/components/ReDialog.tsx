import { useState, useCallback, createContext, useContext, useRef } from 'react'
import { X, Loader2 } from 'lucide-react'
import { createPortal } from 'react-dom'

interface DialogOptions {
  title: string
  content: React.ReactNode
  width?: number | string
  confirmText?: string
  cancelText?: string
  showCancel?: boolean
  onConfirm?: () => void | Promise<void>
  onCancel?: () => void
  closeOnClickOverlay?: boolean
}

interface DialogItem extends DialogOptions {
  id: string
  visible: boolean
  loading: boolean
}

interface DialogContextType {
  open: (options: DialogOptions) => void
  close: (id: string) => void
  confirm: (options: Omit<DialogOptions, 'onConfirm' | 'onCancel'>) => Promise<boolean>
}

const DialogContext = createContext<DialogContextType | null>(null)

export function useDialog() {
  const ctx = useContext(DialogContext)
  if (!ctx) throw new Error('useDialog must be used within DialogProvider')
  return ctx
}

export function DialogProvider({ children }: { children: React.ReactNode }) {
  const [dialogs, setDialogs] = useState<DialogItem[]>([])
  const confirmResolveRef = useRef<((value: boolean) => void) | null>(null)

  const open = useCallback((options: DialogOptions) => {
    const id = Math.random().toString(36).slice(2)
    setDialogs(prev => [...prev, { ...options, id, visible: true, loading: false }])
  }, [])

  const close = useCallback((id: string) => {
    setDialogs(prev => prev.map(d => d.id === id ? { ...d, visible: false } : d))
    setTimeout(() => {
      setDialogs(prev => prev.filter(d => d.id !== id))
    }, 300)
  }, [])

  const confirm = useCallback((options: Omit<DialogOptions, 'onConfirm' | 'onCancel'>): Promise<boolean> => {
    return new Promise((resolve) => {
      confirmResolveRef.current = resolve
      open({
        ...options,
        showCancel: true,
        onConfirm: () => resolve(true),
        onCancel: () => resolve(false),
      })
    })
  }, [open])

  const handleConfirm = async (dialog: DialogItem) => {
    if (!dialog.onConfirm) {
      close(dialog.id)
      return
    }
    setDialogs(prev => prev.map(d => d.id === dialog.id ? { ...d, loading: true } : d))
    try {
      await dialog.onConfirm()
      close(dialog.id)
    } finally {
      setDialogs(prev => prev.map(d => d.id === dialog.id ? { ...d, loading: false } : d))
    }
  }

  return (
    <DialogContext.Provider value={{ open, close, confirm }}>
      {children}
      {createPortal(
        <>
          {dialogs.map(dialog => (
            <div
              key={dialog.id}
              className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-300 ${dialog.visible ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
            >
              <div
                className="absolute inset-0 bg-black/50"
                onClick={() => dialog.closeOnClickOverlay !== false && close(dialog.id)}
              />
              <div
                className={`relative bg-card-bg border border-card-border rounded-xl shadow-2xl w-full transform transition-all duration-300 ${dialog.visible ? 'scale-100 translate-y-0' : 'scale-95 translate-y-4'}`}
                style={{ maxWidth: dialog.width || 480 }}
              >
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
                  <h3 className="text-lg font-semibold text-text-primary">{dialog.title}</h3>
                  <button
                    onClick={() => close(dialog.id)}
                    className="p-1 rounded-lg hover:bg-white/5 text-text-muted hover:text-text-primary transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="px-6 py-5">
                  {dialog.content}
                </div>

                <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06]">
                  {dialog.showCancel !== false && (
                    <button
                      onClick={() => { dialog.onCancel?.(); close(dialog.id) }}
                      className="px-4 h-10 rounded-lg bg-white/5 text-text-secondary hover:bg-white/10 transition-colors"
                    >
                      {dialog.cancelText || '取消'}
                    </button>
                  )}
                  <button
                    onClick={() => handleConfirm(dialog)}
                    disabled={dialog.loading}
                    className="flex items-center gap-2 px-4 h-10 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-50"
                  >
                    {dialog.loading && <Loader2 className="w-4 h-4 animate-spin" />}
                    {dialog.confirmText || '确认'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </>,
        document.body
      )}
    </DialogContext.Provider>
  )
}
