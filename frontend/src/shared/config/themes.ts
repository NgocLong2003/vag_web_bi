// ============================================================================
// THEME LIBRARY — Mỗi report chọn 1 theme từ đây
// Không được hardcode hex trong component, luôn dùng theme tokens
// ============================================================================

export interface ThemePalette {
  name: string
  /** Màu chính — dùng cho button, active state, accent (20%) */
  500: string
  /** Nhạt hơn — dùng cho hover, secondary */
  400: string
  /** Rất nhạt — dùng cho background highlight, badge bg */
  200: string
  /** Gần trắng — dùng cho tinted background */
  50: string
  /** Đậm hơn — dùng cho text trên nền nhạt, header */
  700: string
  /** Đậm nhất — dùng cho text nhấn mạnh */
  900: string
}

export const themes = {
  indigo: {
    name: 'Indigo',
    900: '#312e81',
    700: '#4338ca',
    500: '#4f46e5',
    400: '#818cf8',
    200: '#c7d2fe',
    50: '#eef2ff',
  },
  teal: {
    name: 'Teal',
    900: '#134e4a',
    700: '#0f766e',
    500: '#0d9488',
    400: '#2dd4bf',
    200: '#99f6e4',
    50: '#f0fdfa',
  },
  slateBlue: {
    name: 'Slate Blue',
    900: '#1e2a4a',
    700: '#2d4373',
    500: '#3b5998',
    400: '#5b7ec2',
    200: '#a8bde0',
    50: '#edf1f9',
  },
  emerald: {
    name: 'Emerald',
    900: '#064e3b',
    700: '#047857',
    500: '#059669',
    400: '#34d399',
    200: '#a7f3d0',
    50: '#ecfdf5',
  },
  deepOcean: {
    name: 'Deep Ocean',
    900: '#0f172a',
    700: '#1e3a5f',
    500: '#2563eb',
    400: '#60a5fa',
    200: '#93c5fd',
    50: '#eef3fa',
  },
  warmCoral: {
    name: 'Warm Coral',
    900: '#7c2d12',
    700: '#c2410c',
    500: '#ea580c',
    400: '#fb923c',
    200: '#fed7aa',
    50: '#fff7ed',
  },
} satisfies Record<string, ThemePalette>

export type ThemeKey = keyof typeof themes

/** Theme mặc định cho toàn hệ thống */
export const DEFAULT_THEME: ThemeKey = 'teal'


/**
 * DATA PALETTE — dùng cho chart, category, legend
 * Cố định xuyên suốt mọi theme/report
 * Thứ tự: dùng lần lượt từ [0] trở đi
 */
export const dataPalette = [
  '#4f46e5', // indigo
  '#0d9488', // teal
  '#ea580c', // orange
  '#8b5cf6', // violet
  '#0284c7', // sky
  '#d97706', // amber
  '#dc2626', // red
  '#059669', // emerald
  '#db2777', // pink
  '#2563eb', // blue
  '#65a30d', // lime
  '#9333ea', // purple
] as const

/** Lấy màu cho index, tự loop nếu > 12 category */
export function dataColor(index: number): string {
  return dataPalette[index % dataPalette.length]
}