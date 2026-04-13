import React, { useState, useEffect } from 'react'
import { ENDPOINTS } from '@shared/api/endpoints'
import { useFilterStore } from '@shared/stores/useFilterStore'
import { useResponsive } from '@shared/hooks/useResponsive'
import { ReportShell } from '@features/reports/_shared/ReportShell'
import { useReportData } from '@features/reports/_shared/useReportData'
import { ExportBar } from '@shared/ui/actions/ExportButton'
import { KBCPicker } from '@shared/ui/slicers/KBCPicker'
import { BPSlicerStrip } from '@shared/ui/slicers/BPSlicerStrip'
import { BPSlicerDropdown } from '@shared/ui/slicers/BPSlicerDropdown'
import { toast } from '@shared/ui/feedback/Toast'
import { today, firstDayOfMonth } from '@shared/utils/format'
import { apiClient } from '@shared/api/client'
import type { KBCRecord } from '@shared/ui/slicers/kbc-picker.types'

export default function KinhDoanhPage() {
  const { data: reportData, isLoading, error } = useReportData({
    hierarchyUrl: ENDPOINTS.reports.kinhDoanh.hierarchy,
    khachhangUrl: ENDPOINTS.reports.kinhDoanh.khachhang,
  })

  const { isMobile } = useResponsive()
  const { selectedBP, setSelectedBP, currentKBC, setCurrentKBC } = useFilterStore()
  const [allExpanded, setAllExpanded] = useState(true)

  const [kbcList, setKbcList] = useState<KBCRecord[]>([])
  const [kbcLoading, setKbcLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function loadKBC() {
      try {
        const res = await apiClient.get<{ success: boolean; data: KBCRecord[] }>(ENDPOINTS.reports.kinhDoanh.kyBaoCao)
        if (!cancelled && res.success) setKbcList(res.data)
      } catch {
        if (!cancelled) { console.warn('KBC API failed, using mock data'); setKbcList(MOCK_KBC) }
      } finally {
        if (!cancelled) setKbcLoading(false)
      }
    }
    loadKBC()
    return () => { cancelled = true }
  }, [])

  function onKBCChange(kbc: typeof currentKBC) {
    setCurrentKBC(kbc)
    if (kbc) toast('Da chon: ' + kbc.ten_kbc)
  }

  const [columns] = useState([
    { id: 'c0', type: 'cn' as const, label: 'Cong no', dateA: today(), dateB: '', loaded: false, loading: false, data: {} },
    { id: 'c1', type: 'ds' as const, label: 'Doanh so', dateA: firstDayOfMonth(), dateB: today(), loaded: false, loading: false, data: {} },
    { id: 'c2', type: 'dt' as const, label: 'Doanh thu', dateA: firstDayOfMonth(), dateB: today(), loaded: false, loading: false, data: {} },
  ])

  // --- Toolbar: KBC picker + BP dropdown + NV + action buttons ---
  const toolbar = (
    <>
      <KBCPicker
        kbcList={kbcList}
        value={currentKBC}
        onChange={onKBCChange}
        label={kbcLoading ? 'Dang tai...' : undefined}
      />

      <BPSlicerDropdown
        value={selectedBP}
        onChange={setSelectedBP}
        allowedBPs={reportData?.allowedBP}
      />

      <div className="mx-1 h-5 w-px bg-surface-2" />

      <button className="flex h-8 items-center gap-1.5 rounded-md border border-surface-2 bg-surface-0 px-3 text-xs font-semibold text-surface-5 hover:bg-white">
        NV <span className="rounded-full bg-surface-3 px-1.5 text-[10px] font-bold text-white">&infin;</span>
      </button>

      <div className="mx-1 h-5 w-px bg-surface-2" />

      <button onClick={() => setAllExpanded((v) => !v)} className="flex h-8 items-center gap-1 rounded-md border border-surface-2 bg-white px-3 text-xs font-semibold text-surface-5 hover:bg-surface-0">
        {allExpanded ? 'Thu' : 'Mo'}
      </button>
      <button onClick={() => toast('TODO: Reload')} className="flex h-8 items-center gap-1 rounded-md border border-surface-2 bg-white px-3 text-xs font-semibold text-surface-5 hover:bg-surface-0">
        Tai lai
      </button>

      <div className="mx-1 h-5 w-px bg-surface-2" />

      <button className="flex h-8 items-center gap-1 rounded-md border border-brand-500 bg-white px-3 text-xs font-semibold text-brand-600 hover:bg-brand-50">
        + Them cot
      </button>

      <ExportBar
        excel={{ url: ENDPOINTS.reports.kinhDoanh.exportExcel, payload: () => ({ rows: [], col_headers: [], bp: selectedBP }), filename: 'BaoCaoKD.xlsx' }}
        pdf={{ url: ENDPOINTS.reports.kinhDoanh.exportExcel, payload: () => ({ rows: [], col_headers: [], bp: selectedBP }), filename: 'BaoCaoKD.pdf' }}
        disabled={!columns.some((c) => c.loaded)}
      />
    </>
  )

  // --- Mobile sheets ---
  const sheets = {
    filter: {
      title: 'Bo loc',
      content: (
        <div className="space-y-4 px-2 pb-4">
          <div>
            <label className="mb-2 block text-xs font-bold uppercase text-surface-4">Ky bao cao</label>
            <KBCPicker kbcList={kbcList} value={currentKBC} onChange={onKBCChange} />
          </div>
          <div>
            <label className="mb-2 block text-xs font-bold uppercase text-surface-4">Bo phan</label>
            <BPSlicerStrip value={selectedBP} onChange={setSelectedBP} allowedBPs={reportData?.allowedBP} />
          </div>
        </div>
      ),
    },
    actions: {
      title: 'Thao tac',
      content: (
        <div className="space-y-2 px-2 pb-4">
          <button onClick={() => setAllExpanded((v) => !v)} className="flex w-full items-center gap-3 rounded-lg border border-surface-2 bg-white p-3 text-sm font-semibold">{allExpanded ? 'Thu gon' : 'Mo rong'}</button>
          <button className="flex w-full items-center gap-3 rounded-lg border border-surface-2 bg-white p-3 text-sm font-semibold">Tai lai</button>
          <button className="flex w-full items-center gap-3 rounded-lg border border-emerald-500 bg-white p-3 text-sm font-semibold text-emerald-700">Xuat Excel</button>
        </div>
      ),
    },
  }

  // --- Content ---
  let content: React.ReactNode
  if (isLoading) {
    content = <div className="flex h-full items-center justify-center text-surface-4"><p className="text-sm">Dang tai...</p></div>
  } else if (error) {
    content = <div className="flex h-full items-center justify-center text-surface-4"><div className="text-center"><p className="text-sm font-semibold text-red-500">Loi tai du lieu</p><p className="mt-1 text-xs">{error}</p></div></div>
  } else {
    content = (
      <div className="flex h-full items-center justify-center text-surface-4">
        <div className="text-center">
          <p className="text-lg font-bold">Bao cao Kinh Doanh</p>
          <p className="mt-2 text-sm">{reportData?.roots.length || 0} root NV | {reportData?.khMap.size || 0} KH | {reportData?.allowedNV.size || 0} NV (RLS)</p>
          <p className="mt-1 text-sm">KBC: <strong>{currentKBC ? currentKBC.ten_kbc : 'Chua chon'}</strong></p>
          <p className="mt-1 text-sm">BP: <strong>{selectedBP || 'Tat ca'}</strong></p>
          {currentKBC && <p className="mt-1 text-xs text-surface-3">Ban ra: {currentKBC.ngay_bd_xuat_ban} - {currentKBC.ngay_kt_xuat_ban}<br/>Thu tien: {currentKBC.ngay_bd_thu_tien} - {currentKBC.ngay_kt_thu_tien}</p>}
        </div>
      </div>
    )
  }

  return (
    <>
      {!isMobile && <div className="bp-header-strip"><BPSlicerStrip value={selectedBP} onChange={setSelectedBP} allowedBPs={reportData?.allowedBP} /></div>}
      <ReportShell toolbar={toolbar} sheets={sheets}>{content}</ReportShell>
    </>
  )
}

const MOCK_KBC: KBCRecord[] = [
  { id:100, ma_kbc:'N2026', ten_kbc:'Năm 2026', loai_kbc:'Năm' as const, parent_id:null, sort_order:1, ngay_du_no_dau_ki:null, ngay_bd_xuat_ban:null, ngay_kt_xuat_ban:null, ngay_bd_thu_tien:null, ngay_kt_thu_tien:null, ngay_bd_lan_ki:null, ngay_kt_lan_ki:null, ngay_du_no_cuoi_ki:null },
  { id:110, ma_kbc:'Q1-2026', ten_kbc:'Quý 1/2026', loai_kbc:'Quý' as const, parent_id:100, sort_order:1, ngay_du_no_dau_ki:null, ngay_bd_xuat_ban:null, ngay_kt_xuat_ban:null, ngay_bd_thu_tien:null, ngay_kt_thu_tien:null, ngay_bd_lan_ki:null, ngay_kt_lan_ki:null, ngay_du_no_cuoi_ki:null },
  { id:111, ma_kbc:'T01-2026', ten_kbc:'Tháng 1/2026', loai_kbc:'Tháng' as const, parent_id:110, sort_order:1, ngay_du_no_dau_ki:'2025-12-31', ngay_bd_xuat_ban:'2026-01-01', ngay_kt_xuat_ban:'2026-01-31', ngay_bd_thu_tien:'2026-01-01', ngay_kt_thu_tien:'2026-02-15', ngay_bd_lan_ki:'2026-02-01', ngay_kt_lan_ki:'2026-02-15', ngay_du_no_cuoi_ki:'2026-01-31' },
  { id:112, ma_kbc:'T02-2026', ten_kbc:'Tháng 2/2026', loai_kbc:'Tháng' as const, parent_id:110, sort_order:2, ngay_du_no_dau_ki:'2026-01-31', ngay_bd_xuat_ban:'2026-02-01', ngay_kt_xuat_ban:'2026-02-28', ngay_bd_thu_tien:'2026-02-01', ngay_kt_thu_tien:'2026-03-15', ngay_bd_lan_ki:'2026-03-01', ngay_kt_lan_ki:'2026-03-15', ngay_du_no_cuoi_ki:'2026-02-28' },
  { id:113, ma_kbc:'T03-2026', ten_kbc:'Tháng 3/2026', loai_kbc:'Tháng' as const, parent_id:110, sort_order:3, ngay_du_no_dau_ki:'2026-02-28', ngay_bd_xuat_ban:'2026-03-01', ngay_kt_xuat_ban:'2026-03-31', ngay_bd_thu_tien:'2026-03-01', ngay_kt_thu_tien:'2026-04-15', ngay_bd_lan_ki:'2026-04-01', ngay_kt_lan_ki:'2026-04-15', ngay_du_no_cuoi_ki:'2026-03-31' },
  { id:120, ma_kbc:'Q2-2026', ten_kbc:'Quý 2/2026', loai_kbc:'Quý' as const, parent_id:100, sort_order:2, ngay_du_no_dau_ki:null, ngay_bd_xuat_ban:null, ngay_kt_xuat_ban:null, ngay_bd_thu_tien:null, ngay_kt_thu_tien:null, ngay_bd_lan_ki:null, ngay_kt_lan_ki:null, ngay_du_no_cuoi_ki:null },
  { id:121, ma_kbc:'T04-2026', ten_kbc:'Tháng 4/2026', loai_kbc:'Tháng' as const, parent_id:120, sort_order:1, ngay_du_no_dau_ki:'2026-03-31', ngay_bd_xuat_ban:'2026-04-01', ngay_kt_xuat_ban:'2026-04-30', ngay_bd_thu_tien:'2026-04-01', ngay_kt_thu_tien:'2026-05-15', ngay_bd_lan_ki:'2026-05-01', ngay_kt_lan_ki:'2026-05-15', ngay_du_no_cuoi_ki:'2026-04-30' },
  { id:122, ma_kbc:'T05-2026', ten_kbc:'Tháng 5/2026', loai_kbc:'Tháng' as const, parent_id:120, sort_order:2, ngay_du_no_dau_ki:'2026-04-30', ngay_bd_xuat_ban:'2026-05-01', ngay_kt_xuat_ban:'2026-05-31', ngay_bd_thu_tien:'2026-05-01', ngay_kt_thu_tien:'2026-06-15', ngay_bd_lan_ki:'2026-06-01', ngay_kt_lan_ki:'2026-06-15', ngay_du_no_cuoi_ki:'2026-05-31' },
  { id:123, ma_kbc:'T06-2026', ten_kbc:'Tháng 6/2026', loai_kbc:'Tháng' as const, parent_id:120, sort_order:3, ngay_du_no_dau_ki:'2026-05-31', ngay_bd_xuat_ban:'2026-06-01', ngay_kt_xuat_ban:'2026-06-30', ngay_bd_thu_tien:'2026-06-01', ngay_kt_thu_tien:'2026-07-15', ngay_bd_lan_ki:'2026-07-01', ngay_kt_lan_ki:'2026-07-15', ngay_du_no_cuoi_ki:'2026-06-30' },
]