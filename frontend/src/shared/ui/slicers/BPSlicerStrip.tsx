import { useCallback, useRef, useEffect } from 'react'
import { BRANDS, type Brand } from '@shared/config/brands'

// ============================================================================
// BPSlicerStrip — Dải logo ngang để chọn bộ phận (Loại 2)
//
// UX:
//   - Logo công ty tổng (Việt Anh Group) ở đầu = "Tất cả"
//   - Click công ty tổng = chọn tất cả (value='')
//   - Click công ty con = chọn BP đó
//   - Click lại công ty con đang active = bỏ chọn → về "Tất cả"
//   - Công ty tổng luôn active khi value='' (bao quát tất cả)
//   - Có divider giữa công ty tổng và các công ty con
// ============================================================================

interface BPSlicerStripProps {
  value: string
  onChange: (maBp: string) => void
  allowedBPs?: string[]
}

export function BPSlicerStrip({ value, onChange, allowedBPs }: BPSlicerStripProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Separate parent company (ma_bp='') from children
  const parentBrand = BRANDS.find((b) => b.ma_bp === '')

  // Filter: a brand is visible if ANY of its ma_bp codes is in allowedBPs
  const childBrands = BRANDS
    .filter((b) => b.ma_bp !== '')
    .filter((b) => {
      if (!allowedBPs?.length) return true
      const codes = b.ma_bp.split(',').map((c) => c.trim())
      return codes.some((code) => allowedBPs.includes(code))
    })
    .sort((a, b) => a.sort_order - b.sort_order)

  const handleClick = useCallback(
    (maBp: string) => {
      // Toggle: click same child = deselect → "Tất cả"
      // Click parent = always "Tất cả"
      if (maBp === '') {
        onChange('')
      } else {
        onChange(value === maBp ? '' : maBp)
      }
    },
    [value, onChange]
  )

  // Auto-scroll to active item
  useEffect(() => {
    if (!value || !scrollRef.current) return
    const activeEl = scrollRef.current.querySelector(`[data-bp="${value}"]`) as HTMLElement
    if (activeEl) {
      activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    }
  }, [value])

  const isAllSelected = value === ''

  return (
    <div className="bp-strip-wrap" ref={scrollRef}>
      {/* Parent company — "Tất cả" */}
      {parentBrand && (
        <>
          <button
            className={`bp-strip-item bp-strip-parent ${isAllSelected ? 'active' : ''}`}
            onClick={() => handleClick('')}
            title="Tất cả bộ phận"
            data-bp=""
          >
            <img
              src={parentBrand.logo_vertical}
              alt={parentBrand.thuong_hieu}
              className="bp-strip-logo bp-strip-logo-parent"
              loading="lazy"
            />
          </button>
          <div className="bp-strip-divider" />
        </>
      )}

      {/* Child companies */}
      {childBrands.map((brand) => (
        <button
          key={brand.ma_bp}
          data-bp={brand.ma_bp}
          className={`bp-strip-item ${value === brand.ma_bp ? 'active' : ''} ${isAllSelected ? 'all-selected' : ''}`}
          onClick={() => handleClick(brand.ma_bp)}
          title={brand.thuong_hieu}
        >
          <img
            src={brand.logo_vertical}
            alt={brand.thuong_hieu}
            className="bp-strip-logo"
            loading="lazy"
            onError={(e) => {
              const el = e.currentTarget
              el.style.display = 'none'
              const parent = el.parentElement
              if (parent && !parent.querySelector('.bp-strip-fallback')) {
                const fb = document.createElement('span')
                fb.className = 'bp-strip-fallback'
                fb.textContent = brand.ma_bp
                parent.appendChild(fb)
              }
            }}
          />
        </button>
      ))}
    </div>
  )
}