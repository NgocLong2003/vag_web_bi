import { useEffect, useRef, type ReactNode } from 'react'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

export function BottomSheet({ open, onClose, title, children }: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null)
  const startY = useRef(0)
  const currentY = useRef(0)
  const dragging = useRef(false)

  // Swipe down to dismiss
  useEffect(() => {
    if (!open || !sheetRef.current) return
    const el = sheetRef.current
    const handle = el.querySelector('.sheet-handle') as HTMLElement
    const titleEl = el.querySelector('.sheet-title') as HTMLElement

    function onStart(e: TouchEvent) {
      startY.current = e.touches[0].clientY
      currentY.current = startY.current
      dragging.current = true
      el.style.transition = 'none'
    }
    function onMove(e: TouchEvent) {
      if (!dragging.current) return
      currentY.current = e.touches[0].clientY
      const dy = Math.max(0, currentY.current - startY.current)
      el.style.transform = `translateY(${dy}px)`
    }
    function onEnd() {
      if (!dragging.current) return
      dragging.current = false
      el.style.transition = ''
      if (currentY.current - startY.current > 80) {
        onClose()
      } else {
        el.style.transform = ''
      }
    }

    const targets = [handle, titleEl].filter(Boolean)
    targets.forEach((t) => t?.addEventListener('touchstart', onStart, { passive: true }))
    document.addEventListener('touchmove', onMove, { passive: true })
    document.addEventListener('touchend', onEnd)

    return () => {
      targets.forEach((t) => t?.removeEventListener('touchstart', onStart))
      document.removeEventListener('touchmove', onMove)
      document.removeEventListener('touchend', onEnd)
    }
  }, [open, onClose])

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 z-[9980] bg-black/40 backdrop-blur-sm transition-opacity ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className={`fixed inset-x-0 bottom-0 z-[9985] flex max-h-[85dvh] flex-col overflow-hidden rounded-t-2xl bg-white shadow-[0_-8px_40px_rgba(0,0,0,0.18)] transition-transform duration-300 ${
          open ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        {/* Handle */}
        <div className="sheet-handle mx-auto mt-2.5 mb-1.5 h-1 w-9 shrink-0 rounded-full bg-surface-3" />

        {/* Title */}
        <div className="sheet-title shrink-0 border-b border-surface-1 px-4 pb-2.5 text-sm font-bold">
          {title}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 pb-6">{children}</div>
      </div>
    </>
  )
}
