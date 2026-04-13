import { create } from 'zustand'
import { useEffect } from 'react'

// ═══ Store ═══
interface ToastItem {
  id: string
  message: string
  type: 'ok' | 'error' | 'info'
}

interface ToastStore {
  toasts: ToastItem[]
  add: (message: string, type?: 'ok' | 'error' | 'info') => void
  remove: (id: string) => void
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  add: (message, type = 'ok') => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }))
    // Auto-remove after 3.5s
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, 3500)
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

/** Convenience function — call from anywhere */
export const toast = (message: string, type: 'ok' | 'error' | 'info' = 'ok') => {
  useToastStore.getState().add(message, type)
}

// ═══ Component ═══
export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-1.5 pointer-events-none max-md:bottom-16 max-md:right-3 max-md:left-3">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="pointer-events-auto flex items-center gap-2 rounded-lg border border-surface-2 bg-white px-3 py-2 text-xs shadow-md animate-in slide-in-from-bottom-2 max-w-[280px] max-md:max-w-full"
        >
          <span
            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] ${
              t.type === 'ok'
                ? 'bg-emerald-50 text-emerald-700'
                : t.type === 'error'
                  ? 'bg-red-50 text-red-600'
                  : 'bg-brand-50 text-brand-600'
            }`}
          >
            {t.type === 'ok' ? '✓' : t.type === 'error' ? '✕' : 'i'}
          </span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  )
}
