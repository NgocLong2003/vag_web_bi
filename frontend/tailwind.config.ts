import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand palette (matching current CSS variables)
        brand: {
          50: '#eef2ff',
          100: '#dbeafe',
          500: '#4a78df',
          600: '#1a46c4',
          700: '#153aa0',
          900: '#0f1623',
        },
        emerald: {
          50: '#eafaf4',
          500: '#2db87e',
          700: '#056944',
        },
        surface: {
          0: '#f7f8fa',
          1: '#eef0f4',
          2: '#d8dce6',
          3: '#b0b8c9',
          4: '#8b95aa',
          5: '#5a6478',
          6: '#3d4a63',
          7: '#1e2a3a',
        },
      },
      fontFamily: {
        sans: ['"Nunito Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }], // 10px
      },
    },
  },
  plugins: [],
} satisfies Config
