import { useParams } from 'react-router-dom'

export default function DashboardViewPage() {
  const { slug } = useParams<{ slug: string }>()

  // TODO: Migrate Power BI embed logic from templates/dashboard.html
  // - Fetch report URL via /api/report-url
  // - Decode obfuscated URL
  // - Render iframe
  // - Shield protection (desktop only)

  return (
    <div className="flex h-full items-center justify-center text-surface-4">
      <p>Power BI Dashboard: <strong>{slug}</strong></p>
      <p className="mt-2 text-xs">TODO: Migrate iframe embed logic</p>
    </div>
  )
}
