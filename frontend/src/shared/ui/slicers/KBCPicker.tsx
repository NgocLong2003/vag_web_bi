import { useState, useRef, useEffect, useCallback } from 'react'
import { useResponsive } from '@shared/hooks/useResponsive'
import { useKBCPicker } from './useKBCPicker'
import type { KBCPickerProps } from './kbc-picker.types'

// ============================================================================
// KBCPicker — Kỳ Báo Cáo selector
//
// UX PRINCIPLE:
//   Click tên = chọn 1 kỳ duy nhất → đóng panel → apply ngay
//   Click checkbox = toggle multi-select → panel vẫn mở → apply khi đóng
//   Click Năm/Quý name = expand/collapse (không chọn)
//
// RESPONSIVE:
//   Desktop: dropdown dưới trigger
//   Mobile dọc: bottom sheet
//   Mobile ngang: side panel trái
// ============================================================================

export function KBCPicker({ kbcList, value, onChange, label: labelOverride }: KBCPickerProps) {
  const { isMobile, isLandscape } = useResponsive()
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const {
    visibleNodes,
    label,
    query,
    setQuery,
    selectSingle,
    toggleMulti,
    toggleExpand,
    applyCurrentChecked,
  } = useKBCPicker(kbcList, onChange)

  // Close handler — apply checked set
  const close = useCallback(() => {
    if (!open) return
    setOpen(false)
    applyCurrentChecked()
  }, [open, applyCurrentChecked])

  // Open handler
  const openPanel = useCallback(() => {
    setOpen(true)
    setQuery('')
    setTimeout(() => searchRef.current?.focus(), 80)
  }, [setQuery])

  const toggle = useCallback(() => {
    if (open) close()
    else openPanel()
  }, [open, close, openPanel])

  // Click outside to close
  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (
        triggerRef.current?.contains(e.target as Node) ||
        panelRef.current?.contains(e.target as Node)
      )
        return
      close()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open, close])

  // Escape to close
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, close])

  // Handle single click on month → select + close
  function onNodeClick(id: number, isMonth: boolean, hasChildren: boolean) {
    if (isMonth) {
      selectSingle(id)
      setOpen(false) // close immediately
    } else {
      toggleExpand(id)
    }
  }

  // Handle checkbox click → multi-select, stay open
  function onCheckboxClick(e: React.MouseEvent, id: number) {
    e.stopPropagation()
    toggleMulti(id)
  }

  // Panel positioning
  function panelStyle(): React.CSSProperties {
    if (isMobile && !isLandscape) {
      // Mobile portrait: bottom sheet
      return {
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        top: 'auto',
        width: '100%',
        maxHeight: '75vh',
        borderRadius: '16px 16px 0 0',
      }
    }
    if (isMobile && isLandscape) {
      // Mobile landscape: side panel
      return {
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        right: 'auto',
        width: 320,
        maxHeight: '100vh',
        borderRadius: '0 10px 10px 0',
      }
    }
    // Desktop: dropdown below trigger
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect()
      return {
        position: 'fixed',
        top: rect.bottom + 6,
        left: Math.min(rect.left, window.innerWidth - 330),
        width: 320,
        borderRadius: 10,
      }
    }
    return { position: 'fixed', top: 80, left: 16, width: 320, borderRadius: 10 }
  }

  // Loai badge color
  function loaiClass(loai: string): string {
    if (loai === 'Năm') return 'nam'
    if (loai === 'Quý') return 'quy'
    return 'thang'
  }

  // Highlight search match
  function highlight(text: string): React.ReactNode {
    if (!query) return text
    const idx = text.toLowerCase().indexOf(query.toLowerCase())
    if (idx < 0) return text
    return (
      <>
        {text.substring(0, idx)}
        <em className="kbc-hl">{text.substring(idx, idx + query.length)}</em>
        {text.substring(idx + query.length)}
      </>
    )
  }

  return (
    <div className="kbc-wrap">
      {/* Trigger */}
      <button
        ref={triggerRef}
        className={`kbc-trigger ${open ? 'open' : ''}`}
        onClick={toggle}
      >
        <svg viewBox="0 0 16 16" strokeWidth="1.8">
          <rect x="2" y="2" width="12" height="12" rx="2" />
          <line x1="5" y1="6" x2="11" y2="6" />
          <line x1="5" y1="10" x2="9" y2="10" />
        </svg>
        <span className="kbc-lbl">{labelOverride || label}</span>
      </button>

      {/* Panel */}
      {open && (
        <div
          ref={panelRef}
          className="kbc-panel open"
          style={panelStyle()}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search */}
          <div className="kbc-panel-head">
            <input
              ref={searchRef}
              type="text"
              placeholder="Tìm kỳ báo cáo..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="kbc-panel-hint">
            Bấm tên = chọn 1 kỳ · Bấm ☑ = chọn thêm nhiều kỳ
          </div>

          {/* Tree */}
          <div className="kbc-tree">
            {visibleNodes.length === 0 && (
              <div className="kbc-empty">Không tìm thấy</div>
            )}
            {visibleNodes.map((node) => {
              const k = node.kbc
              const lc = loaiClass(k.loai_kbc)
              const lvClass = node.depth === 0 ? 'lv0' : node.depth === 1 ? 'lv1' : ''

              return (
                <div
                  key={k.id}
                  className={`ki ${node.isSingleSelected ? 'selected' : ''}`}
                  style={{ paddingLeft: 8 + node.depth * 18 }}
                  onClick={() => onNodeClick(k.id, node.isMonth, node.hasChildren)}
                >
                  {/* Toggle arrow */}
                  {node.hasChildren ? (
                    <span
                      className="ki-tog"
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleExpand(k.id)
                      }}
                    >
                      <svg viewBox="0 0 8 8">
                        {node.isExpanded ? (
                          <path d="M1 2.5L4 5.5L7 2.5" />
                        ) : (
                          <path d="M2.5 1L5.5 4L2.5 7" />
                        )}
                      </svg>
                    </span>
                  ) : (
                    <span className="ki-tog-sp" />
                  )}

                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={node.isChecked}
                    ref={(el) => {
                      if (el) el.indeterminate = node.isIndeterminate
                    }}
                    className={node.isIndeterminate ? 'has-child-sel' : ''}
                    onClick={(e) => onCheckboxClick(e, k.id)}
                    readOnly
                  />

                  {/* Dot */}
                  <span className={`ki-dot ${lc}`} />

                  {/* Name */}
                  <span className={`ki-name ${lvClass}`}>{highlight(k.ten_kbc)}</span>

                  {/* Badge */}
                  <span className={`ki-badge ${lc}`}>{k.loai_kbc}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}