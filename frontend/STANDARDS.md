# VietAnh BI — Tiêu chuẩn dự án

> Tài liệu này ghi lại các quy tắc bắt buộc cho mọi dev tham gia dự án.
> Các tiêu chuẩn được enforce trong code thông qua shared functions/components —
> dev **phải** dùng các component/hàm có sẵn, không tự viết lại.

---

## 1. Số liệu & Định dạng

| Quy tắc | Ví dụ | Enforce bởi |
|---------|-------|-------------|
| Dấu `,` ngăn cách phần nghìn | `1,234,567` | `fmtNumber()` |
| Dấu `.` cho thập phân | `1,234.56` | `fmtNumber(v, 2)` |
| Tự thêm dấu `,` khi nhập liệu | Gõ `1234567` → hiện `1,234,567` | `<NumberInput />` |
| Viết gọn số ≥ 10,000 (cho label/chart) | `15,000` → `15 nghìn`, `2,500,000` → `2.5 triệu`, `1,000,000,000` → `1 tỷ` | `fmtCompact()` |
| Null / chưa có dữ liệu | `—` (em dash) | `fmtNumber()` trả về `—` |

### Các hàm bắt buộc dùng

```typescript
import { fmtNumber, fmtCompact, fmtPercent, fmtDate } from '@shared/utils/format'
import { NumberInput } from '@shared/ui/inputs/NumberInput'

fmtNumber(1234567)        // "1,234,567"
fmtNumber(1234.5, 1)      // "1,234.5"
fmtNumber(null)            // "—"

fmtCompact(15000)          // "15 nghìn"
fmtCompact(2500000)        // "2.5 triệu"
fmtCompact(1000000000)     // "1 tỷ"

fmtPercent(0.856, 1)       // "85.6%"
fmtDate("2026-01-15")      // "15/01/2026"
```

### Chưa quyết định (sẽ bổ sung)

- [ ] Số âm: màu đỏ? Ngoặc đơn `(1,234)`? Dấu trừ `-1,234`?
- [ ] Số bằng 0: hiển thị `0` hay `—` hay để trống?
- [ ] Phần trăm: bao nhiêu chữ số thập phân mặc định?
- [ ] Ngày tháng: `dd/MM/yyyy` (hiện tại) — cần confirm
- [ ] Tiền tệ: có hiển thị đơn vị `đ` / `VNĐ` không?

---

## 2. Bố cục & Navigation

### Desktop
- Header chứa: **Hỏi AI**, **Tải báo cáo**, **Toàn màn hình**, **Cài đặt**

### Mobile
- **Bỏ Header**, thay bằng **Bottom Dock**
- **Home ngoài cùng tay trái** (bắt buộc, không được thay đổi vị trí)
- Các nút còn lại tùy sắp xếp theo từng trang báo cáo

**Enforce bởi:** `<BottomDock />` — Home luôn được inject ở vị trí đầu tiên, dev chỉ cần truyền `actions` cho các nút còn lại.

### Chưa quyết định

- [ ] Header chiều cao
- [ ] Bottom Dock chiều cao
- [ ] Sidebar width, slide direction
- [ ] Spacing grid (4px? 8px?)
- [ ] Max content width

---

## 3. Icon & Hình ảnh

| Quy tắc | Chi tiết |
|---------|---------|
| Logo công ty / thương hiệu | **PNG** duy nhất được phép |
| Mọi icon khác | **100% SVG** |
| Emoji icons | **CẤM** (`❌`, `✅`, `⚠️`...) — lý do: mỗi máy hiển thị khác nhau |

**Enforce bởi:** Code review + icon library chuẩn (Lucide React). Không import emoji vào JSX.

### Chưa quyết định

- [ ] Icon library chính thức (hiện dùng Lucide)
- [ ] Icon sizes chuẩn (button, menu, table)
- [ ] Stroke width chuẩn

---

## 4. Loading & Feedback

| Quy tắc | Chi tiết |
|---------|---------|
| Loading overlay | Mặc định dùng **file GIF** (`/public/assets/loading.gif`) |
| Fallback | CSS spinner nếu GIF chưa có |

**Enforce bởi:** `<LoadingOverlay />` — tự render GIF, tự fallback.

### Chưa quyết định

- [ ] File GIF cụ thể (cần bạn cung cấp)
- [ ] Skeleton shimmer cho table cells
- [ ] Toast position, duration, colors
- [ ] Error state design
- [ ] Empty state design

---

## 5. Tải Xuống / Export

| Quy tắc | Chi tiết |
|---------|---------|
| Mọi trang báo cáo | **BẮT BUỘC** có cả **Excel** (phân tích) + **PDF** (in ấn) |

**Enforce bởi:** `<ExportBar />` — luôn render 2 nút Excel + PDF. Dev không thể bỏ 1 trong 2.

```typescript
import { ExportBar } from '@shared/ui/actions/ExportButton'

<ExportBar
  excel={{ url: '/api/report/export-excel', payload: () => filters }}
  pdf={{ url: '/api/report/export-pdf', payload: () => filters }}
/>
```

### Chưa quyết định

- [ ] Excel format (có giống giao diện web không?)
- [ ] PDF layout (A4 dọc/ngang? Logo? Watermark?)
- [ ] Tên file convention
- [ ] Nút tải ở toolbar hay dropdown

---

## 6–12. Chưa quyết định

Các mục sau sẽ được bổ sung dần trong quá trình phát triển:

- [ ] **Chữ (Typography):** font, size scale, weight, line height
- [ ] **Màu sắc:** palette, semantic colors, dark mode
- [ ] **Bảng (Table):** row height, sticky, sort, hover, pagination
- [ ] **Biểu đồ (Chart):** library, palette, tooltip, legend
- [ ] **Tương tác & UX:** drill-down, filter mode, keyboard shortcuts
- [ ] **Phân quyền & Bảo mật:** watermark, session timeout, audit log
- [ ] **Performance:** virtual scroll, API timeout, cache, data freshness

---

## Nguyên tắc chung

1. **Dùng shared component/hàm có sẵn** — không tự viết lại logic format, export, loading
2. **Mọi số hiển thị** phải qua `fmtNumber()` hoặc `fmtCompact()`
3. **Mọi ô nhập số** phải dùng `<NumberInput />`
4. **Mọi trang báo cáo** phải có `<ExportBar />` với cả Excel + PDF
5. **Không dùng emoji** làm icon
6. **Thiết kế responsive** — desktop + mobile cho mọi trang
