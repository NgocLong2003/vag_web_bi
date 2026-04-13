import { themes, DEFAULT_THEME, type ThemeKey, type ThemePalette } from './themes'

/**
 * Lấy palette theo tên theme.
 * Component gọi: const palette = useTheme('teal')
 * Rồi dùng: palette[500], palette[50], palette[200]...
 */
export function useTheme(key?: ThemeKey): ThemePalette {
  return themes[key || DEFAULT_THEME]
}

/**
 * Inject CSS variables vào root element.
 * Gọi 1 lần ở layout component hoặc App.tsx:
 *   applyThemeVars('teal')
 *
 * Sau đó trong CSS/Tailwind dùng:
 *   var(--theme-500), var(--theme-50), ...
 */
export function applyThemeVars(key?: ThemeKey): void {
  const palette = themes[key || DEFAULT_THEME]
  const root = document.documentElement
  root.style.setProperty('--theme-900', palette[900])
  root.style.setProperty('--theme-700', palette[700])
  root.style.setProperty('--theme-500', palette[500])
  root.style.setProperty('--theme-400', palette[400])
  root.style.setProperty('--theme-200', palette[200])
  root.style.setProperty('--theme-50', palette[50])
}