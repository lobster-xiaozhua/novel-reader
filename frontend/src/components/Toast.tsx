import { useState, useCallback, createContext, useContext, useRef } from 'react'
import { X, CheckCircle, AlertTriangle, Info, XCircle } from 'lucide-react'
import { createPortal } from 'react-dom'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
}

interface ToastContextType {
  toast: (type: ToastType, message: string) => void
  success: (message: string) => void
  error: (message: string) => void
  warning: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

export function useErrorReporter() {
  const toast = useToast()

  const reportError = useCallback((error: unknown, context?: string) => {
    console.error(`[错误报告] ${context || ''}`, error)

    if (error instanceof Error && 'status' in error) {
      const httpErr = error as { userMessage?: string; message: string }
      toast.error(httpErr.userMessage || httpErr.message)
      return
    }

    if (error instanceof Error) {
      toast.error(`${context || '错误'}: ${error.message}`)
      return
    }

    toast.error(`${context || '发生'}未知错误`)
  }, [toast])

  return { reportError }
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const colorMap = {
  success: 'text-success bg-success/10 border-success/20',
  error: 'text-danger bg-danger/10 border-danger/20',
  warning: 'text-warning bg-warning/10 border-warning/20',
  info: 'text-info bg-info/10 border-info/20',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, type, message }])
    const timer = setTimeout(() => removeToast(id), 4000)
    timers.current.set(id, timer)
  }, [removeToast])

  const value: ToastContextType = {
    toast: addToast,
    success: (msg) => addToast('success', msg),
    error: (msg) => addToast('error', msg),
    warning: (msg) => addToast('warning', msg),
    info: (msg) => addToast('info', msg),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
          {toasts.map((t) => {
            const Icon = iconMap[t.type]
            return (
              <div
                key={t.id}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-xl animate-in slide-in-from-right ${colorMap[t.type]}`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-medium text-text-primary flex-1">{t.message}</span>
                <button onClick={() => removeToast(t.id)} className="p-0.5 rounded hover:bg-white/10">
                  <X className="w-4 h-4 text-text-muted" />
                </button>
              </div>
            )
          })}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  )
}
