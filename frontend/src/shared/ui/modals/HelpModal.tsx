import {
  X, HelpCircle, MessageCircle, BookOpen,
  Calendar, Building2, Users, Download, MousePointer,
} from 'lucide-react'

// ============================================================================
// HelpModal — Help & guidance modal
//
// Current features:
//   - Usage guide (step by step)
//   - Contact info
//   - Version
//
// Future features:
//   - Keyboard shortcuts reference
//   - FAQ / troubleshooting
//   - Video tutorials
//   - Changelog / what's new
//   - Feedback form
// ============================================================================

interface HelpModalProps {
  open: boolean
  onClose: () => void
}

const GUIDE_STEPS = [
  {
    icon: Calendar,
    title: 'Chon ky bao cao',
    desc: 'Bam vao nut ky o thanh cong cu de chon thang hoac quy can xem bao cao. Bam ten = chon 1 ky, bam checkbox = chon nhieu ky.',
  },
  {
    icon: Building2,
    title: 'Loc theo bo phan',
    desc: 'Bam vao logo cong ty tren thanh header de loc du lieu theo bo phan. Bam logo cong ty tong = xem tat ca.',
  },
  {
    icon: Users,
    title: 'Chon nhan vien',
    desc: 'Su dung bo loc NV de chon nhan vien kinh doanh can xem. Ho thong tu dong hien thi cac khach hang lien quan.',
  },
  {
    icon: MousePointer,
    title: 'Xem chi tiet khach hang',
    desc: 'Bam vao ten khach hang trong bang de xem lich su giao dich chi tiet: ban ra, tra lai, thanh toan, thuong.',
  },
  {
    icon: Download,
    title: 'Xuat bao cao',
    desc: 'Bam nut "Tai xuong" o goc phai header de xuat file Excel hoac PDF. Co the xuat tung cot hoac toan bo bao cao.',
  },
]

export function HelpModal({ open, onClose }: HelpModalProps) {
  if (!open) return null

  return (
    <>
      <div className="smodal-overlay" onClick={onClose} />
      <div className="smodal">
        <div className="smodal-head">
          <h3 className="smodal-title">
            <HelpCircle className="h-4 w-4" /> Tro giup
          </h3>
          <button className="smodal-close" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="smodal-body">
          {/* Guide steps */}
          <div className="smodal-section">
            <div className="smodal-label">Huong dan su dung</div>
            <div className="help-steps">
              {GUIDE_STEPS.map((step, i) => {
                const Icon = step.icon
                return (
                  <div key={i} className="help-step">
                    <div className="help-step-icon">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="help-step-content">
                      <div className="help-step-title">{step.title}</div>
                      <div className="help-step-desc">{step.desc}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Shortcuts (future) */}
          <div className="smodal-section">
            <div className="smodal-label">Phim tat</div>
            <div className="smodal-rows">
              <div className="smodal-row">
                <kbd className="help-kbd">Esc</kbd>
                <span className="smodal-row-val">Dong modal / dropdown</span>
              </div>
              <div className="smodal-row">
                <kbd className="help-kbd">F11</kbd>
                <span className="smodal-row-val">Toan man hinh</span>
              </div>
            </div>
          </div>

          {/* Contact */}
          <div className="smodal-section">
            <div className="smodal-label">Lien he ho tro</div>
            <div className="smodal-rows">
              <div className="smodal-row">
                <MessageCircle className="h-3.5 w-3.5" />
                <span className="smodal-row-key">Email</span>
                <span className="smodal-row-val">longnv.bcl@vietanh-group.com</span>
              </div>
              <div className="smodal-row">
                <BookOpen className="h-3.5 w-3.5" />
                <span className="smodal-row-key">Don vi</span>
                <span className="smodal-row-val">Ban Chien Luoc</span>
              </div>
            </div>
          </div>

          {/* Version */}
          <div className="smodal-section" style={{ textAlign: 'center', paddingBottom: 16 }}>
            <div style={{ fontSize: 11, color: 'var(--g3)' }}>VietAnh BI Dashboard v2.0</div>
            <div style={{ fontSize: 10, color: 'var(--g3)', marginTop: 2 }}>Ban Chien Luoc &mdash; Viet Anh Group</div>
          </div>
        </div>
      </div>
    </>
  )
}