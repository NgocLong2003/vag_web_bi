import { useState } from 'react'
import { useAuth } from '@shared/auth/AuthProvider'
import {
  X, User as UserIcon, Lock, Bell, Palette,
  Mail, Shield, Building2, BookOpen, Hash,
  Eye, EyeOff, Save, Check, Sun, Moon, Monitor,
} from 'lucide-react'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

type Tab = 'account' | 'password' | 'notifications' | 'appearance'

const TABS: { id: Tab; icon: typeof UserIcon; label: string }[] = [
  { id: 'account', icon: UserIcon, label: 'Tai khoan' },
  { id: 'password', icon: Lock, label: 'Mat khau' },
  { id: 'notifications', icon: Bell, label: 'Thong bao' },
  { id: 'appearance', icon: Palette, label: 'Giao dien' },
]

export function SettingsModal({ open, onClose }: SettingsModalProps) {
  const { user, refresh } = useAuth()
  const [tab, setTab] = useState<Tab>('account')

  // Password state
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  // Notification state
  const [notiEmail, setNotiEmail] = useState(true)
  const [notiAlert, setNotiAlert] = useState(true)
  const [notiSound, setNotiSound] = useState(false)

  // Appearance state
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light')

  if (!open || !user) return null

  const initials = (user.displayName || user.username || 'U')
    .split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    if (!currentPw || !newPw) { setMsg({ type: 'err', text: 'Vui long dien day du' }); return }
    setSaving(true); setMsg(null)
    try {
      const form = new URLSearchParams()
      form.append('display_name', user!.displayName)
      form.append('current_password', currentPw)
      form.append('new_password', newPw)
      const res = await fetch('/settings', {
        method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(), credentials: 'same-origin', redirect: 'manual',
      })
      if (res.ok || res.type === 'opaqueredirect' || res.redirected) {
        setMsg({ type: 'ok', text: 'Da doi mat khau thanh cong' })
        setCurrentPw(''); setNewPw(''); refresh()
      } else {
        setMsg({ type: 'err', text: 'Mat khau hien tai khong dung' })
      }
    } catch { setMsg({ type: 'err', text: 'Loi ket noi' }) }
    finally { setSaving(false) }
  }

  return (
    <>
      <div className="smodal-overlay" onClick={onClose} />
      <div className="smodal smodal-wide">
        {/* Left sidebar */}
        <div className="stg-sidebar">
          <div className="stg-sidebar-head">
            <div className="stg-sidebar-avatar">{initials}</div>
            <div className="stg-sidebar-info">
              <div className="stg-sidebar-name">{user.displayName}</div>
              <div className="stg-sidebar-role">@{user.username}</div>
            </div>
          </div>
          <nav className="stg-nav">
            {TABS.map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                className={`stg-nav-item ${tab === id ? 'active' : ''}`}
                onClick={() => { setTab(id); setMsg(null) }}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </nav>
          <div className="stg-sidebar-footer">
            VietAnh BI v2.0
          </div>
        </div>

        {/* Right content */}
        <div className="stg-content">
          <div className="stg-content-head">
            <h3 className="stg-content-title">
              {TABS.find(t => t.id === tab)?.label}
            </h3>
            <button className="smodal-close" onClick={onClose}>
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="stg-content-body">
            {/* ── Account ── */}
            {tab === 'account' && (
              <>
                <div className="stg-section">
                  <div className="stg-section-title">Thong tin ca nhan</div>
                  <div className="stg-fields">
                    <div className="stg-field">
                      <UserIcon className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Ten hien thi</span>
                      <span className="stg-field-val">{user.displayName || '\u2014'}</span>
                    </div>
                    <div className="stg-field">
                      <Mail className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Email</span>
                      <span className="stg-field-val">{user.email || '\u2014'}</span>
                    </div>
                    <div className="stg-field">
                      <Shield className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Vai tro</span>
                      <span className="stg-field-val">
                        <span className="stg-role-badge" data-role={user.role}>
                          {user.role === 'admin' ? 'Admin' : 'User'}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="stg-section">
                  <div className="stg-section-title">To chuc</div>
                  <div className="stg-fields">
                    <div className="stg-field">
                      <Building2 className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Bo phan</span>
                      <span className="stg-field-val">{user.boPhan || '\u2014'}</span>
                    </div>
                    <div className="stg-field">
                      <BookOpen className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Khoi</span>
                      <span className="stg-field-val">{user.khoi || '\u2014'}</span>
                    </div>
                    <div className="stg-field">
                      <BookOpen className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Chuc vu</span>
                      <span className="stg-field-val">{user.chucVu || '\u2014'}</span>
                    </div>
                    <div className="stg-field">
                      <Hash className="h-3.5 w-3.5" />
                      <span className="stg-field-key">Ma NVKD</span>
                      <span className="stg-field-val" style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>
                        {user.maNvkdList.length ? user.maNvkdList.join(', ') : '\u221E (tat ca)'}
                      </span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* ── Password ── */}
            {tab === 'password' && (
              <div className="stg-section">
                <div className="stg-section-title">Doi mat khau</div>
                <div className="stg-section-desc">
                  Mat khau moi can co it nhat 6 ky tu
                </div>
                <form onSubmit={handleChangePassword} className="stg-form">
                  <div className="stg-input-group">
                    <label>Mat khau hien tai</label>
                    <input
                      type={showPw ? 'text' : 'password'}
                      value={currentPw}
                      onChange={(e) => setCurrentPw(e.target.value)}
                      placeholder="Nhap mat khau hien tai"
                      autoComplete="current-password"
                    />
                  </div>
                  <div className="stg-input-group">
                    <label>Mat khau moi</label>
                    <div className="stg-input-pw">
                      <input
                        type={showPw ? 'text' : 'password'}
                        value={newPw}
                        onChange={(e) => setNewPw(e.target.value)}
                        placeholder="Nhap mat khau moi"
                        autoComplete="new-password"
                      />
                      <button type="button" className="stg-pw-toggle" onClick={() => setShowPw(!showPw)}>
                        {showPw ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  {msg && <div className={`stg-msg ${msg.type}`}>{msg.text}</div>}

                  <button type="submit" className="stg-btn-primary" disabled={saving}>
                    <Save className="h-3.5 w-3.5" />
                    {saving ? 'Dang luu...' : 'Doi mat khau'}
                  </button>
                </form>
              </div>
            )}

            {/* ── Notifications ── */}
            {tab === 'notifications' && (
              <div className="stg-section">
                <div className="stg-section-title">Tuy chon thong bao</div>
                <div className="stg-section-desc">
                  Quan ly cach ban nhan thong bao tu he thong
                </div>
                <div className="stg-toggles">
                  <label className="stg-toggle-row">
                    <div className="stg-toggle-info">
                      <div className="stg-toggle-label">Thong bao email</div>
                      <div className="stg-toggle-desc">Nhan thong bao qua email khi co canh bao moi</div>
                    </div>
                    <div className={`stg-switch ${notiEmail ? 'on' : ''}`} onClick={() => setNotiEmail(!notiEmail)}>
                      <div className="stg-switch-thumb" />
                    </div>
                  </label>
                  <label className="stg-toggle-row">
                    <div className="stg-toggle-info">
                      <div className="stg-toggle-label">Canh bao tren trang</div>
                      <div className="stg-toggle-desc">Hien thi badge canh bao tren header</div>
                    </div>
                    <div className={`stg-switch ${notiAlert ? 'on' : ''}`} onClick={() => setNotiAlert(!notiAlert)}>
                      <div className="stg-switch-thumb" />
                    </div>
                  </label>
                  <label className="stg-toggle-row">
                    <div className="stg-toggle-info">
                      <div className="stg-toggle-label">Am thanh</div>
                      <div className="stg-toggle-desc">Phat am thanh khi co thong bao moi</div>
                    </div>
                    <div className={`stg-switch ${notiSound ? 'on' : ''}`} onClick={() => setNotiSound(!notiSound)}>
                      <div className="stg-switch-thumb" />
                    </div>
                  </label>
                </div>
                <div className="stg-note">
                  Cac tuy chon nay se duoc luu tu dong
                </div>
              </div>
            )}

            {/* ── Appearance ── */}
            {tab === 'appearance' && (
              <div className="stg-section">
                <div className="stg-section-title">Giao dien</div>
                <div className="stg-section-desc">
                  Tuy chinh giao dien hien thi cua he thong
                </div>
                <div className="stg-theme-grid">
                  {([
                    { id: 'light' as const, icon: Sun, label: 'Sang', desc: 'Giao dien nen trang' },
                    { id: 'dark' as const, icon: Moon, label: 'Toi', desc: 'Giao dien nen toi' },
                    { id: 'system' as const, icon: Monitor, label: 'He thong', desc: 'Tu dong theo thiet bi' },
                  ]).map(opt => (
                    <div
                      key={opt.id}
                      className={`stg-theme-card ${theme === opt.id ? 'active' : ''}`}
                      onClick={() => setTheme(opt.id)}
                    >
                      <div className="stg-theme-icon">
                        <opt.icon className="h-5 w-5" />
                      </div>
                      <div className="stg-theme-label">{opt.label}</div>
                      <div className="stg-theme-desc">{opt.desc}</div>
                      {theme === opt.id && (
                        <div className="stg-theme-check"><Check className="h-3 w-3" /></div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="stg-note">
                  Che do toi hien dang duoc phat trien
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}