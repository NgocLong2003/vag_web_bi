// ============================================================================
// Báo cáo Khách hàng — Định nghĩa cột
//
// 7 cột dữ liệu:
//   1. du_no_dk    — Dư nợ đầu tháng (ADMIN chốt số)
//   2. ban_ra      — Bán ra (khoảng ngày xuất bán)
//   3. tt1         — Thanh toán trước lấn kỳ
//   4. tt2         — Thanh toán lấn kỳ (chỉ nhóm A)
//   5. du_no_tk    — Dư nợ cần thu trong kỳ
//   6. du_no_ct    — Dư nợ cuối tháng (ADMIN chốt số)
//   7. du_no_ck    — Dư nợ cuối kỳ (sau thanh toán)
//
// Cột tt1 + tt2 có thể gộp thành tt_merged khi không tách
// ============================================================================

import type { ColumnDef, KyBaoCao } from '../../shared/components/TreeTable/types'
import { fmtDate as fmtD, isoDate as toISO } from '@shared/utils/format'

/** ID tất cả các cột gốc (dùng để fetch data) */
export const COLUMN_IDS = ['du_no_dk', 'ban_ra', 'tt1', 'tt2', 'du_no_tk', 'du_no_ct', 'du_no_ck'] as const
export type ColumnId = typeof COLUMN_IDS[number]

/** Các cột hiển thị số nghịch (dư nợ: cao = xấu) */
export const INVERSE_COLS = new Set(['du_no_dk', 'du_no_tk', 'du_no_ct', 'du_no_ck'])

/** Bộ phận nhóm A (thanh toán theo ngày thu tiền) */
export const BP_NHOM_A = ['VA', 'VB', 'SF']

/** Kiểm tra BP có thuộc nhóm A không */
export function isBPNhomA(bp: string | null | undefined): boolean {
  return !bp || BP_NHOM_A.includes(bp)
}

/** Tính ngày phụ trợ từ kỳ báo cáo */
export function computeDates(kbc: KyBaoCao) {
  const dDNDK = toISO(kbc.ngay_du_no_dau_ki)
  const dBDXB = toISO(kbc.ngay_bd_xuat_ban)
  const dKTXB = toISO(kbc.ngay_kt_xuat_ban)
  const dBDTT = toISO(kbc.ngay_bd_thu_tien)
  const dKTTT = toISO(kbc.ngay_kt_thu_tien)
  const dBDLK = toISO(kbc.ngay_bd_lan_ki || '')
  const dKTLK = toISO(kbc.ngay_kt_lan_ki || '')
  const dDNCK = toISO(kbc.ngay_du_no_cuoi_ki)

  // Ngày trước lấn kỳ = ngày đầu lấn kỳ - 1
  let ngayTruocLK = ''
  if (dBDLK) {
    const d = new Date(dBDLK)
    d.setDate(d.getDate() - 1)
    ngayTruocLK = d.toISOString().substring(0, 10)
  }

  // Ngày dư nợ đầu kỳ + 1 (hiển thị trên header)
  let ngayDNDKPlus1 = ''
  if (dDNDK) {
    const d = new Date(dDNDK)
    d.setDate(d.getDate() + 1)
    ngayDNDKPlus1 = d.toISOString().substring(0, 10)
  }

  return {
    dDNDK, dBDXB, dKTXB, dBDTT, dKTTT, dBDLK, dKTLK, dDNCK,
    ngayTruocLK, ngayDNDKPlus1,
  }
}

/** Build danh sách cột hiển thị (tách hoặc gộp thanh toán) */
export function buildDisplayColumns(
  kbc: KyBaoCao,
  ttSplit: boolean,
  selectedBP: string,
): ColumnDef[] {
  const dates = computeDates(kbc)
  const cols: ColumnDef[] = []

  // 1. Dư nợ đầu tháng
  cols.push({
    id: 'du_no_dk',
    label: 'DƯ NỢ ĐẦU THÁNG',
    subLabel: `ADMIN chốt số\n${fmtD(dates.ngayDNDKPlus1)}`,
    className: 'col-cn',
    minWidth: 120,
    isInverse: true,
  })

  // 2. Bán ra
  cols.push({
    id: 'ban_ra',
    label: 'BÁN RA',
    subLabel: `${fmtD(dates.dBDXB)}\n↓\n${fmtD(dates.dKTXB)}`,
    className: 'col-ds',
    minWidth: 120,
  })

  // 3. Thanh toán
  if (ttSplit) {
    // Tách 2 cột
    let tt1Date = ''
    if (selectedBP) {
      tt1Date = isBPNhomA(selectedBP)
        ? `${fmtD(dates.dBDTT)}\n↓\n${fmtD(dates.ngayTruocLK)}`
        : `${fmtD(dates.dBDXB)}\n↓\n${fmtD(dates.ngayTruocLK)}`
    }
    cols.push({
      id: 'tt1',
      label: 'THANH TOÁN',
      subLabel: tt1Date,
      className: 'col-dt-sub',
      minWidth: 120,
    })

    let tt2Date = ''
    if (selectedBP) {
      tt2Date = isBPNhomA(selectedBP)
        ? `${fmtD(dates.dBDLK)}\n↓\n${fmtD(dates.dKTTT)}`
        : `${fmtD(dates.dBDXB)}\n↓\n${fmtD(dates.dKTXB)}`
    }
    cols.push({
      id: 'tt2',
      label: 'THANH TOÁN',
      subLabel: tt2Date,
      className: 'col-dt-sub',
      minWidth: 120,
    })
  } else {
    // Gộp 1 cột
    let ttDate = ''
    if (selectedBP) {
      ttDate = isBPNhomA(selectedBP)
        ? `${fmtD(dates.dBDTT)}\n↓\n${fmtD(dates.dKTTT)}`
        : `${fmtD(dates.dBDXB)}\n↓\n${fmtD(dates.dKTXB)}`
    }
    cols.push({
      id: 'tt_merged',
      label: 'THANH TOÁN',
      subLabel: ttDate,
      className: 'col-dt',
      minWidth: 130,
    })
  }

  // 5. Dư nợ cần thu trong kỳ
  cols.push({
    id: 'du_no_tk',
    label: 'DƯ NỢ CẦN THU TRONG KỲ',
    subLabel: 'Bán ra - Trả về\n- Thanh toán - Thưởng',
    className: 'col-dntk',
    minWidth: 140,
    isInverse: true,
  })

  // 6. Dư nợ cuối tháng
  cols.push({
    id: 'du_no_ct',
    label: 'DƯ NỢ CUỐI THÁNG',
    subLabel: `ADMIN chốt số\n${fmtD(dates.dDNCK)}`,
    className: 'col-cn2',
    minWidth: 120,
    isInverse: true,
  })

  // 7. Dư nợ cuối kỳ
  cols.push({
    id: 'du_no_ck',
    label: 'DƯ NỢ CUỐI KỲ',
    subLabel: `Toàn bộ dư nợ ${kbc.ten_kbc} sau khi\nthanh toán tới ${fmtD(dates.dKTTT)}`,
    className: 'col-dnck',
    minWidth: 140,
    isInverse: true,
  })

  return cols
}