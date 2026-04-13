import { Link } from 'react-router-dom'

export default function DashboardListPage() {
  // TODO: Fetch dashboards from API, group by category
  return (
    <div className="mx-auto max-w-[900px] p-6">
      <h2 className="mb-5 text-xl font-extrabold text-surface-7">Chọn Dashboard</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* TODO: Map over dashboards */}
        <Link
          to="/r/bao-cao-kinh-doanh"
          className="rounded-xl border-[1.5px] border-surface-2 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-600 hover:shadow-md"
        >
          <h3 className="text-base font-bold text-surface-7">Báo cáo Kinh Doanh</h3>
          <p className="mt-1 text-sm text-surface-4">Công nợ, doanh số, doanh thu</p>
        </Link>
      </div>
    </div>
  )
}
