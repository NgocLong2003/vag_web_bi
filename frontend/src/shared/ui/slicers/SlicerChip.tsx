import { useState, useRef, useEffect, useCallback } from 'react'
import { useResponsive } from '@shared/hooks/useResponsive'

// ============================================================================
// SlicerChip — Compact chip trigger with popover
//
// Wraps any slicer content (KBC tree, BP dropdown, NV picker...) in a
// consistent chip UI. Click chip → open popover with slicer content inside.
//
// Props:
//   icon     — SVG icon element
//   label    — short label e.g. "Kỳ", "BP"
//   value    — current display value e.g. "T4/2026", "Sanfovet"
//   active   — whether a specific filter is applied (not default/all)
//   children — slicer content rendered inside popover
//   width    — popover width (default 320)
// ============================================================================

interface SlicerChipProps {
  icon: React.ReactNode
  label: string
  value?: string
  active?: boolean
  children: React.ReactNode
  width?: number
}

export function SlicerChip({
  icon,
  label,
  value,
  active = false,
  children,
  width = 320,
}: SlicerChipProps) {
  const { isMobile, isLandscape } = useResponsive()
  const [open, setOpen] = useState(false)
  const chipRef = useRef<HTMLButtonElement>(null)
  const popRef = useRef<HTMLDivElement>(null)

  const close = useCallback(() => setOpen(false), [])

  // Click outside
  useEffect(() => {
    if (!open) return
    function handle(e: MouseEvent) {
      if (chipRef.current?.contains(e.target as Node)) return
      if (popRef.current?.contains(e.target as Node)) return
      close()
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [open, close])

  // Escape
  useEffect(() => {
    if (!open) return
    function handle(e: KeyboardEvent) { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [open, close])

  function popStyle(): React.CSSProperties {
    if (isMobile && !isLandscape) {
      return {
        position: 'fixed', left: 0, right: 0, bottom: 0, top: 'auto',
        width: '100%', maxHeight: '70vh', borderRadius: '16px 16px 0 0',
      }
    }
    if (isMobile && isLandscape) {
      return {
        position: 'fixed', left: 0, top: 0, bottom: 0, right: 'auto',
        width, maxHeight: '100vh', borderRadius: '0 12px 12px 0',
      }
    }
    if (chipRef.current) {
      const rect = chipRef.current.getBoundingClientRect()
      return {
        position: 'fixed',
        top: rect.bottom + 6,
        left: Math.min(rect.left, window.innerWidth - width - 10),
        width, borderRadius: 12,
      }
    }
    return { position: 'fixed', top: 80, left: 16, width, borderRadius: 12 }
  }

  return (
    <div className="sc-wrap">
      <button
        ref={chipRef}
        className={`sc-chip ${open ? 'open' : ''} ${active ? 'active' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span className="sc-icon">{icon}</span>
        <span className="sc-label">{label}</span>
        {value && <span className="sc-value">{value}</span>}
        <svg className={`sc-chev ${open ? 'rotated' : ''}`} viewBox="0 0 10 10">
          <path d="M2.5 3.5L5 6.5L7.5 3.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div ref={popRef} className="sc-popover" style={popStyle()} onClick={(e) => e.stopPropagation()}>
          {children}
        </div>
      )}
    </div>
  )
}