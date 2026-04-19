import React, { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@shared/api/client'
import { ENDPOINTS } from '@shared/api/endpoints'
import {
  Pencil, Save, X, Check, Trash2, Plus, ExternalLink,
} from 'lucide-react'

// ============================================================================
// DashboardsTab — Quản lý danh sách dashboard
//
// Chức năng:
//   - Xem danh sách (bảng, đầy đủ thông tin)
//   - Thêm mới (modal, các trường thay đổi theo loại dashboard)
//   - Sửa inline (click Sửa → hàng chuyển thành input)
//   - Xóa (xác nhận trước khi xóa)
//   - Toggle hoạt động/khóa
//
// Loại dashboard và trường tương ứng:
//   powerbi   → cần Power BI URL, không cần slug đặc biệt
//   report    → không cần URL, slug phải khớp route React (/r/:slug)
//   analytics → không cần URL, không cần cấu hình thêm
// ============================================================================

interface DashboardRow {
  id: number
  slug: string
  name: string
  description: string
  dashboard_type: string
  category: string
  color: string
  update_mode: string
  update_interval: string
  sort_order: number
  is_active: number
  powerbi_url: string
  icon_svg: string
  updated_at: string
}

const COLOR_OPTIONS = [
  { value: 'teal', label: 'Xanh lá', hex: '#0d9488' },
  { value: 'blue', label: 'Xanh dương', hex: '#1a46c4' },
  { value: 'purple', label: 'Tím', hex: '#7c3aed' },
  { value: 'amber', label: 'Vàng cam', hex: '#d97706' },
  { value: 'rose', label: 'Hồng đỏ', hex: '#e11d48' },
  { value: 'emerald', label: 'Xanh ngọc', hex: '#059669' },
  { value: 'indigo', label: 'Chàm', hex: '#4f46e5' },
  { value: 'cyan', label: 'Xanh biển', hex: '#0891b2' },
]

const TYPE_OPTIONS = [
  { value: 'powerbi', label: 'Power BI' },
  { value: 'report', label: 'Báo cáo tự viết' },
  { value: 'analytics', label: 'Thống kê hệ thống' },
]

/** SVG icon mặc định theo loại dashboard */
const DEFAULT_ICON_SVG: Record<string, string> = {
  report: '<svg viewBox="0 0 52 52" fill="none"><rect x="8" y="4" width="36" height="44" rx="6" fill="currentFill" stroke="currentStroke" stroke-width="2"/><rect x="14" y="16" width="24" height="2.5" rx="1.2" fill="currentStroke" opacity=".2"/><rect x="14" y="22" width="20" height="2.5" rx="1.2" fill="currentStroke" opacity=".15"/><rect x="14" y="28" width="22" height="2.5" rx="1.2" fill="currentStroke" opacity=".1"/><rect x="14" y="34" width="18" height="2.5" rx="1.2" fill="currentStroke" opacity=".08"/></svg>',
  powerbi: '<svg viewBox="0 0 52 52" fill="none"><rect x="4" y="6" width="44" height="36" rx="6" fill="currentFill" stroke="currentStroke" stroke-width="2"/><rect x="8" y="10" width="18" height="14" rx="3" fill="currentStroke" opacity=".1" stroke="currentStroke" stroke-width="1" opacity=".15"/><rect x="30" y="10" width="14" height="6" rx="2" fill="currentStroke" opacity=".12"/><rect x="30" y="19" width="14" height="5" rx="2" fill="currentStroke" opacity=".08"/><rect x="11" y="18" width="3" height="4" rx="1" fill="currentStroke" opacity=".25"/><rect x="16" y="15" width="3" height="7" rx="1" fill="currentStroke" opacity=".3"/><rect x="21" y="12" width="3" height="10" rx="1" fill="currentStroke" opacity=".2"/><rect x="8" y="28" width="36" height="6" rx="2" fill="currentStroke" opacity=".07"/><line x1="20" y1="44" x2="32" y2="44" stroke="currentStroke" stroke-width="2" stroke-linecap="round" opacity=".2"/><line x1="26" y1="42" x2="26" y2="44" stroke="currentStroke" stroke-width="1.5" opacity=".2"/></svg>',
  analytics: '<svg viewBox="0 0 52 52" fill="none"><path d="M4 40L12 28l8 6 8-14 8 4 8-12v28H4z" fill="currentFill"/><polyline points="4,40 12,28 20,34 28,20 36,24 44,12" stroke="currentStroke" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="12" cy="28" r="2.5" fill="#fff" stroke="currentStroke" stroke-width="2"/><circle cx="28" cy="20" r="2.5" fill="#fff" stroke="currentStroke" stroke-width="2"/><circle cx="44" cy="12" r="3" fill="#fff" stroke="currentStroke" stroke-width="2"/></svg>',
}

function getDefaultIcon(type: string): string {
  return DEFAULT_ICON_SVG[type] || DEFAULT_ICON_SVG.report
}

const EMPTY_FORM: Partial<DashboardRow> = {
  name: '', slug: '', description: '', dashboard_type: 'report',
  category: '', powerbi_url: '', sort_order: 0, is_active: 1,
  color: 'teal', update_mode: 'scheduled', update_interval: '',
  icon_svg: getDefaultIcon('report'),
}

export function DashboardsTab() {
  const [rows, setRows] = useState<DashboardRow[]>([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<Partial<DashboardRow>>({})
  const [saving, setSaving] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState<Partial<DashboardRow>>({ ...EMPTY_FORM })
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const categories = [...new Set(rows.map(r => r.category).filter(Boolean))].sort()

  const load = useCallback(async () => {
    try {
      // Admin dùng /api/dashboards/all để thấy cả dashboard đã tắt
      const res = await apiClient.get<{ success: boolean; data: DashboardRow[] }>('/api/dashboards/all')
      if (res.success) {
        setRows(res.data)
      }
    } catch (e) { console.error('[AdminDashboards] API lỗi:', e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  function flash(text: string, type: 'ok' | 'err' = 'ok') {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  // ── Sửa ──
  function startEdit(d: DashboardRow) {
    setEditId(d.id)
    setForm({
      name: d.name, slug: d.slug, description: d.description,
      dashboard_type: d.dashboard_type, category: d.category,
      powerbi_url: d.powerbi_url, sort_order: d.sort_order,
      is_active: d.is_active, color: d.color,
      update_mode: d.update_mode, update_interval: d.update_interval,
      icon_svg: d.icon_svg || getDefaultIcon(d.dashboard_type),
    })
  }

  async function saveEdit() {
    if (!editId) return
    const err = validateForm(form)
    if (err) { flash(err, 'err'); return }
    setSaving(true)
    try {
      const res = await apiClient.post<{ success: boolean; error?: string }>(`/api/dashboards/${editId}`, form)
      if (res.success) { await load(); setEditId(null); flash('Đã cập nhật dashboard') }
      else flash(res.error || 'Có lỗi xảy ra', 'err')
    } catch (e) { flash(String(e), 'err') }
    finally { setSaving(false) }
  }

  // ── Thêm mới ──
  async function saveAdd() {
    const err = validateForm(addForm)
    if (err) { flash(err, 'err'); return }
    setSaving(true)
    try {
      const fd = new URLSearchParams()
      fd.append('name', addForm.name || '')
      fd.append('slug', addForm.slug || '')
      fd.append('powerbi_url', addForm.powerbi_url || '')
      fd.append('description', addForm.description || '')
      fd.append('dashboard_type', addForm.dashboard_type || 'report')
      fd.append('category', addForm.category || '')
      fd.append('sort_order', String(addForm.sort_order || 0))
      const res = await fetch('/admin/dashboard/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: fd.toString(),
        credentials: 'same-origin',
        redirect: 'manual',
      })
      if (res.ok || res.type === 'opaqueredirect') {
        await load()
        setShowAdd(false)
        setAddForm({ ...EMPTY_FORM })
        flash('Đã thêm dashboard mới')
      } else { flash('Lỗi khi thêm dashboard', 'err') }
    } catch (e) { flash(String(e), 'err') }
    finally { setSaving(false) }
  }

  // ── Xóa ──
  async function handleDelete(d: DashboardRow) {
    if (!confirm(`Xóa dashboard "${d.name}"?\nTất cả phân quyền liên quan sẽ bị xóa theo.`)) return
    try {
      const res = await fetch(`/admin/dashboard/${d.id}/delete`, {
        method: 'POST', credentials: 'same-origin', redirect: 'manual',
      })
      if (res.ok || res.type === 'opaqueredirect') { await load(); flash('Đã xóa dashboard') }
      else flash('Lỗi khi xóa', 'err')
    } catch (e) { flash(String(e), 'err') }
  }

  // ── Validation theo loại ──
  function validateForm(f: Partial<DashboardRow>): string | null {
    if (!f.name?.trim()) return 'Tên dashboard không được để trống'
    if (!f.slug?.trim()) return 'Slug không được để trống'
    if (f.dashboard_type === 'powerbi' && !f.powerbi_url?.trim()) {
      return 'Dashboard Power BI cần có URL nhúng'
    }
    return null
  }

  function ef(field: keyof DashboardRow, value: string | number) {
    setForm(prev => {
      const next = { ...prev, [field]: value }
      // Tự động cập nhật icon mặc định khi đổi loại dashboard
      if (field === 'dashboard_type') {
        const currentIcon = prev.icon_svg || ''
        const wasDefault = !currentIcon || Object.values(DEFAULT_ICON_SVG).includes(currentIcon)
        if (wasDefault) {
          next.icon_svg = getDefaultIcon(value as string)
        }
      }
      return next
    })
  }
  function af(field: keyof DashboardRow, value: string | number) {
    setAddForm(prev => {
      const next = { ...prev, [field]: value }
      // Tự động cập nhật icon mặc định khi đổi loại dashboard
      if (field === 'dashboard_type') {
        const currentIcon = prev.icon_svg || ''
        const wasDefault = !currentIcon || Object.values(DEFAULT_ICON_SVG).includes(currentIcon)
        if (wasDefault) {
          next.icon_svg = getDefaultIcon(value as string)
        }
      }
      return next
    })
  }

  function colorHex(name: string) {
    return COLOR_OPTIONS.find(c => c.value === name)?.hex || '#0d9488'
  }

  if (loading) return <div className="adm-placeholder">Đang tải...</div>

  return (
    <>
      {msg && <div className={`adm-flash ${msg.type}`}>{msg.text}</div>}

      {/* Thanh công cụ */}
      <div className="adm-toolbar">
        <span className="adm-toolbar-count">{rows.length} dashboard</span>
        <button className="adm-btn-add" onClick={() => setShowAdd(true)}>
          <Plus className="h-3.5 w-3.5" /> Thêm dashboard
        </button>
      </div>

      {/* Bảng danh sách */}
      <div className="adm-table-wrap">
        <table className="adm-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>TT</th>
              <th>Tên / Đường dẫn</th>
              <th>Mô tả</th>
              <th>Phân loại</th>
              <th style={{ width: 90 }}>Loại</th>
              <th style={{ width: 80 }}>Màu sắc</th>
              <th style={{ width: 100 }}>Cập nhật</th>
              <th style={{ width: 100 }}>Tần suất</th>
              <th style={{ width: 50 }}>Trạng thái</th>
              <th style={{ width: 90 }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => {
              const isE = editId === d.id
              return (
                <React.Fragment key={d.id}>
                <tr className={isE ? 'editing' : ''}>
                  {/* Thứ tự */}
                  <td className="adm-td-num">
                    {isE ? <input className="adm-input adm-input-sm" type="number" value={form.sort_order ?? 0} onChange={e => ef('sort_order', +e.target.value)} style={{ width: 44 }} /> : d.sort_order}
                  </td>

                  {/* Tên + Slug */}
                  <td>
                    {isE ? (
                      <>
                        <input className="adm-input" value={form.name || ''} onChange={e => ef('name', e.target.value)} placeholder="Tên dashboard" />
                        <input className="adm-input adm-input-slug" value={form.slug || ''} onChange={e => ef('slug', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))} placeholder="duong-dan-url" />
                      </>
                    ) : (
                      <>
                        <div className="adm-td-name">{d.name}</div>
                        <div className="adm-td-slug">/d/{d.slug}</div>
                      </>
                    )}
                  </td>

                  {/* Mô tả */}
                  <td>
                    {isE ? <input className="adm-input" value={form.description || ''} onChange={e => ef('description', e.target.value)} placeholder="Mô tả ngắn" />
                      : <div className="adm-td-desc">{d.description || '\u2014'}</div>}
                  </td>

                  {/* Phân loại */}
                  <td>
                    {isE ? <input className="adm-input" value={form.category || ''} onChange={e => ef('category', e.target.value)} list="cat-list" placeholder="Kinh doanh, Kế toán..." />
                      : <span className="adm-td-cat">{d.category || '\u2014'}</span>}
                  </td>

                  {/* Loại dashboard */}
                  <td>
                    {isE ? (
                      <select className="adm-select" value={form.dashboard_type || 'report'} onChange={e => ef('dashboard_type', e.target.value)}>
                        {TYPE_OPTIONS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                      </select>
                    ) : <span className={`adm-type-badge ${d.dashboard_type}`}>{TYPE_OPTIONS.find(t => t.value === d.dashboard_type)?.label || d.dashboard_type}</span>}
                  </td>

                  {/* Màu sắc */}
                  <td>
                    {isE ? (
                      <select className="adm-select" value={form.color || 'teal'} onChange={e => ef('color', e.target.value)}>
                        {COLOR_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                      </select>
                    ) : (
                      <div className="adm-color-dot">
                        <span className="adm-color-circle" style={{ background: colorHex(d.color) }} />
                        <span>{COLOR_OPTIONS.find(c => c.value === d.color)?.label || d.color}</span>
                      </div>
                    )}
                  </td>

                  {/* Chế độ cập nhật */}
                  <td>
                    {isE ? (
                      <select className="adm-select" value={form.update_mode || 'scheduled'} onChange={e => ef('update_mode', e.target.value)}>
                        <option value="realtime">Thời gian thực</option>
                        <option value="scheduled">Định kỳ</option>
                      </select>
                    ) : (
                      d.update_mode === 'realtime'
                        ? <span className="adm-live-badge">Thời gian thực</span>
                        : <span className="adm-sched-badge">Định kỳ</span>
                    )}
                  </td>

                  {/* Tần suất */}
                  <td>
                    {isE ? <input className="adm-input" value={form.update_interval || ''} onChange={e => ef('update_interval', e.target.value)} placeholder="Mỗi 30 phút" />
                      : <span className="adm-td-interval">{d.update_interval || '\u2014'}</span>}
                  </td>

                  {/* Trạng thái */}
                  <td className="adm-td-center">
                    {isE ? (
                      <label className="adm-toggle">
                        <input type="checkbox" checked={!!form.is_active} onChange={e => ef('is_active', e.target.checked ? 1 : 0)} />
                        <span className="adm-toggle-slider" />
                      </label>
                    ) : (
                      d.is_active
                        ? <span className="adm-status-on"><Check className="h-3.5 w-3.5" /> Bật</span>
                        : <span className="adm-status-off"><X className="h-3.5 w-3.5" /> Tắt</span>
                    )}
                  </td>

                  {/* Thao tác */}
                  <td>
                    {isE ? (
                      <div className="adm-actions">
                        <button className="adm-btn-save" onClick={saveEdit} disabled={saving} title="Lưu"><Save className="h-3.5 w-3.5" /></button>
                        <button className="adm-btn-cancel" onClick={() => setEditId(null)} title="Hủy"><X className="h-3.5 w-3.5" /></button>
                      </div>
                    ) : (
                      <div className="adm-actions">
                        <button className="adm-btn-edit" onClick={() => startEdit(d)} title="Sửa"><Pencil className="h-3.5 w-3.5" /></button>
                        <button className="adm-btn-delete" onClick={() => handleDelete(d)} title="Xóa"><Trash2 className="h-3.5 w-3.5" /></button>
                      </div>
                    )}
                  </td>
                </tr>

                {/* Hàng mở rộng: Power BI URL + Biểu tượng SVG — ngay trong bảng */}
                {isE && (
                  <tr className="adm-expand-row">
                    <td colSpan={10}>
                      <div className="adm-expand-content">
                        {/* Power BI URL — chỉ hiện khi loại Power BI */}
                        {form.dashboard_type === 'powerbi' && (
                          <div className="adm-expand-field">
                            <label>Đường dẫn Power BI</label>
                            <div className="adm-expand-url">
                              <input className="adm-input" value={form.powerbi_url || ''} onChange={e => ef('powerbi_url', e.target.value)} placeholder="https://app.powerbi.com/view?r=..." />
                              {form.powerbi_url && (
                                <a href={form.powerbi_url} target="_blank" rel="noreferrer" className="adm-url-link" title="Mở trong tab mới">
                                  <ExternalLink className="h-3.5 w-3.5" />
                                </a>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Biểu tượng SVG + Xem trước */}
                        <div className="adm-expand-field">
                          <div className="adm-icon-editor-head">
                            <label>Biểu tượng SVG</label>
                            <button
                              type="button"
                              className="adm-btn-reset-icon"
                              onClick={() => ef('icon_svg', getDefaultIcon(form.dashboard_type || 'report'))}
                            >
                              Đặt mặc định
                            </button>
                          </div>
                          <div className="adm-expand-icon">
                            <textarea
                              className="adm-textarea"
                              rows={3}
                              value={form.icon_svg || ''}
                              onChange={e => ef('icon_svg', e.target.value)}
                              placeholder='<svg viewBox="0 0 52 52">...</svg>'
                              spellCheck={false}
                            />
                            <div className="adm-icon-preview-box"
                              style={{ '--stroke': colorHex(form.color || 'teal'), '--fill': colorHex(form.color || 'teal') + '18' } as React.CSSProperties}
                              dangerouslySetInnerHTML={{ __html: form.icon_svg || getDefaultIcon(form.dashboard_type || 'report') }}
                            />
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Gợi ý phân loại */}
      <datalist id="cat-list">
        {categories.map(c => <option key={c} value={c} />)}
      </datalist>

      {/* ══ Modal thêm mới ══ */}
      {showAdd && (
        <>
          <div className="adm-modal-overlay" onClick={() => setShowAdd(false)} />
          <div className="adm-modal">
            <div className="adm-modal-head">
              <h3>Thêm Dashboard</h3>
              <button className="smodal-close" onClick={() => setShowAdd(false)}><X className="h-4 w-4" /></button>
            </div>
            <div className="adm-modal-body">
              <div className="adm-form-grid">
                <div className="adm-fg">
                  <label>Tên dashboard *</label>
                  <input className="adm-input" value={addForm.name || ''} onChange={e => af('name', e.target.value)} placeholder="Báo cáo doanh thu" />
                </div>
                <div className="adm-fg">
                  <label>Đường dẫn (slug) *</label>
                  <input className="adm-input adm-input-slug" value={addForm.slug || ''} onChange={e => af('slug', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))} placeholder="bao-cao-doanh-thu" />
                </div>
                <div className="adm-fg">
                  <label>Loại dashboard</label>
                  <select className="adm-select" value={addForm.dashboard_type || 'report'} onChange={e => af('dashboard_type', e.target.value)}>
                    {TYPE_OPTIONS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div className="adm-fg">
                  <label>Phân loại nghiệp vụ</label>
                  <input className="adm-input" value={addForm.category || ''} onChange={e => af('category', e.target.value)} list="cat-list" placeholder="Kinh doanh, Kế toán..." />
                </div>

                {/* Chỉ hiện URL khi loại là Power BI */}
                {addForm.dashboard_type === 'powerbi' && (
                  <div className="adm-fg adm-fg-full">
                    <label>Đường dẫn Power BI *</label>
                    <input className="adm-input" value={addForm.powerbi_url || ''} onChange={e => af('powerbi_url', e.target.value)} placeholder="https://app.powerbi.com/view?r=..." />
                  </div>
                )}

                <div className="adm-fg adm-fg-full">
                  <label>Mô tả</label>
                  <input className="adm-input" value={addForm.description || ''} onChange={e => af('description', e.target.value)} placeholder="Mô tả ngắn về dashboard" />
                </div>
                <div className="adm-fg">
                  <label>Thứ tự hiển thị</label>
                  <input className="adm-input" type="number" value={addForm.sort_order ?? 0} onChange={e => af('sort_order', +e.target.value)} />
                </div>
                <div className="adm-fg">
                  <label>Màu sắc đại diện</label>
                  <select className="adm-select" value={addForm.color || 'teal'} onChange={e => af('color', e.target.value)}>
                    {COLOR_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>

                {/* Biểu tượng SVG */}
                <div className="adm-fg adm-fg-full">
                  <div className="adm-icon-editor-head">
                    <label>Biểu tượng SVG</label>
                    <button
                      type="button"
                      className="adm-btn-reset-icon"
                      onClick={() => af('icon_svg', getDefaultIcon(addForm.dashboard_type || 'report'))}
                    >
                      Đặt mặc định
                    </button>
                  </div>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <textarea
                      className="adm-textarea"
                      rows={3}
                      value={addForm.icon_svg || ''}
                      onChange={e => af('icon_svg', e.target.value)}
                      placeholder='<svg viewBox="0 0 52 52">...</svg>'
                      spellCheck={false}
                      style={{ flex: 1 }}
                    />
                    <div
                      className="adm-icon-preview-box adm-icon-preview-box-sm"
                      style={{ '--stroke': COLOR_OPTIONS.find(c => c.value === (addForm.color || 'teal'))?.hex || '#0d9488', '--fill': (COLOR_OPTIONS.find(c => c.value === (addForm.color || 'teal'))?.hex || '#0d9488') + '18' } as React.CSSProperties}
                      dangerouslySetInnerHTML={{ __html: addForm.icon_svg || getDefaultIcon(addForm.dashboard_type || 'report') }}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="adm-modal-foot">
              <button className="adm-btn-cancel-lg" onClick={() => setShowAdd(false)}>Hủy</button>
              <button className="adm-btn-save-lg" onClick={saveAdd} disabled={saving}>
                {saving ? 'Đang lưu...' : 'Thêm'}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  )
}