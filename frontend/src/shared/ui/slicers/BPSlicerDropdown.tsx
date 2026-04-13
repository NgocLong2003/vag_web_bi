import { useState, useRef, useEffect, useCallback } from 'react'
import { BRANDS } from '@shared/config/brands'
import { useResponsive } from '@shared/hooks/useResponsive'
import { ChevronDown } from 'lucide-react'

interface BPSlicerDropdownProps {
  value: string
  onChange: (maBp: string) => void
  allowedBPs?: string[]
}

export function BPSlicerDropdown({ value, onChange, allowedBPs }: BPSlicerDropdownProps) {
  const { isMobile, isLandscape } = useResponsive()
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const parentBrand = BRANDS.find((b) => b.ma_bp === '')
  const childBrands = BRANDS
    .filter((b) => b.ma_bp !== '')
    .filter((b) => {
      if (!allowedBPs?.length) return true
      const codes = b.ma_bp.split(',').map((c) => c.trim())
      return codes.some((code) => allowedBPs.includes(code))
    })
    .sort((a, b) => a.sort_order - b.sort_order)

  const selectedBrand = value === '' ? parentBrand : BRANDS.find((b) => b.ma_bp === value)

  const close = useCallback(() => setOpen(false), [])

  function handleSelect(maBp: string) {
    onChange(maBp)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    function h(e: MouseEvent) {
      if (triggerRef.current?.contains(e.target as Node) || panelRef.current?.contains(e.target as Node)) return
      close()
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [open, close])

  useEffect(() => {
    if (!open) return
    function h(e: KeyboardEvent) { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [open, close])

  function getLogo(brand: typeof parentBrand) {
    if (!brand) return ''
    return brand.logo_horizontal || brand.logo_vertical
  }

  function panelStyle(): React.CSSProperties {
    if (isMobile && !isLandscape) {
      return { position: 'fixed', left: 0, right: 0, bottom: 0, top: 'auto', width: '100%', maxHeight: '70vh', borderRadius: '16px 16px 0 0' }
    }
    if (isMobile && isLandscape) {
      return { position: 'fixed', left: 0, top: 0, bottom: 0, right: 'auto', width: 280, maxHeight: '100vh', borderRadius: '0 12px 12px 0' }
    }
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect()
      return { position: 'fixed', top: rect.bottom + 6, left: Math.min(rect.left, window.innerWidth - 290), width: 280, borderRadius: 12 }
    }
    return { position: 'fixed', top: 80, left: 16, width: 280, borderRadius: 12 }
  }

  return (
    <div className="bpdd-wrap">
      <button ref={triggerRef} className={`bpdd-trigger ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
        {selectedBrand && (
          <img src={getLogo(selectedBrand)} alt={selectedBrand.thuong_hieu} className="bpdd-trigger-logo" onError={(e) => { e.currentTarget.style.display = 'none' }} />
        )}
        <ChevronDown className={`bpdd-trigger-chev ${open ? 'rotated' : ''}`} />
      </button>

      {open && (
        <div ref={panelRef} className="bpdd-panel" style={panelStyle()} onClick={(e) => e.stopPropagation()}>
          {parentBrand && (
            <div className={`bpdd-parent ${value === '' ? 'active' : ''}`} onClick={() => handleSelect('')}>
              <img src={getLogo(parentBrand)} alt={parentBrand.thuong_hieu} className="bpdd-parent-logo" onError={(e) => { e.currentTarget.style.display = 'none' }} />
            </div>
          )}
          <div className="bpdd-divider" />
          <div className="bpdd-list">
            {childBrands.map((brand) => (
              <div key={brand.ma_bp} className={`bpdd-item ${value === brand.ma_bp ? 'active' : ''}`} onClick={() => handleSelect(brand.ma_bp)}>
                <div className="bpdd-indent" />
                <img src={getLogo(brand)} alt={brand.thuong_hieu} className="bpdd-item-logo"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                    const p = e.currentTarget.parentElement
                    if (p && !p.querySelector('.bpdd-item-fallback')) {
                      const fb = document.createElement('span'); fb.className = 'bpdd-item-fallback'; fb.textContent = brand.thuong_hieu; p.appendChild(fb)
                    }
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}