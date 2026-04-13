// ============================================================================
// STANDARDS: Loading & Feedback
// - Loading overlay mặc định dùng file GIF
// - Đặt GIF tại: /public/assets/loading.gif (thay bằng file GIF thực tế)
// ============================================================================

interface LoadingOverlayProps {
  visible: boolean
  message?: string
  /** Custom GIF path — mặc định: /assets/loading.gif */
  gifSrc?: string
}

const DEFAULT_GIF = '/assets/loading.gif'

export function LoadingOverlay({
  visible,
  message = 'Đang tải…',
  gifSrc = DEFAULT_GIF,
}: LoadingOverlayProps) {
  if (!visible) return null

  return (
    <div className="fixed inset-0 z-[9950] flex flex-col items-center justify-center gap-4 bg-surface-0/85 backdrop-blur-sm">
      <img
        src={gifSrc}
        alt="Loading"
        className="h-16 w-16 object-contain"
        /* Fallback: nếu GIF chưa có, hiển thị CSS spinner */
        onError={(e) => {
          const el = e.currentTarget
          el.style.display = 'none'
          el.nextElementSibling?.classList.remove('hidden')
        }}
      />
      {/* Fallback CSS spinner — ẩn khi có GIF */}
      <div className="hidden flex items-center gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-3.5 w-3.5 rounded-full bg-gradient-to-br from-brand-600 to-brand-500"
            style={{
              animation: 'bounce 0.6s ease-in-out infinite alternate',
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
      </div>
      <p className="text-sm font-semibold text-surface-5">{message}</p>
    </div>
  )
}
