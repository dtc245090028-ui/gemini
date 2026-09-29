/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['var(--font-serif)', 'Fraunces', 'Georgia', 'serif'],
        sans: ['var(--font-sans)', 'Be Vietnam Pro', '-apple-system', 'sans-serif'],
        mono: ['var(--font-mono)', 'Space Mono', 'Courier New', 'monospace'],
      },
      fontSize: {
        'xs': ['var(--text-xs)', { lineHeight: '1.4' }],     // 12px min
        'sm': ['var(--text-sm)', { lineHeight: '1.45' }],    // 13px
        'base': ['var(--text-base)', { lineHeight: '1.5' }],  // 14px
        'md': ['var(--text-md)', { lineHeight: '1.5' }],      // 15px
        'lg': ['var(--text-lg)', { lineHeight: '1.4' }],      // 17px
        'xl': ['var(--text-xl)', { lineHeight: '1.3' }],      // 20px
        '2xl': ['var(--text-2xl)', { lineHeight: '1.25' }],   // 24px
        '3xl': ['var(--text-3xl)', { lineHeight: '1.2' }],    // 30px
      },
      colors: {
        canvas: {
          DEFAULT: 'var(--bg-canvas)',
          subtle: 'var(--bg-canvas-subtle)',
        },
        surface: {
          DEFAULT: 'var(--bg-surface)',
          warm: 'var(--bg-surface-warm)',
          hover: 'var(--bg-surface-hover)',
          active: 'var(--bg-surface-active)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          medium: 'var(--border-medium)',
          strong: 'var(--border-strong)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          inverse: 'var(--text-inverse)',
        },
        semantic: {
          alert: 'var(--semantic-alert)',
          'alert-bg': 'var(--semantic-alert-bg)',
          'alert-border': 'var(--semantic-alert-border)',
          'alert-hover': 'var(--semantic-alert-hover)',
          success: 'var(--semantic-success)',
          'success-bg': 'var(--semantic-success-bg)',
          'success-border': 'var(--semantic-success-border)',
          'success-hover': 'var(--semantic-success-hover)',
          canceled: 'var(--semantic-canceled)',
          'canceled-bg': 'var(--semantic-canceled-bg)',
          'canceled-border': 'var(--semantic-canceled-border)',
          inactive: 'var(--semantic-inactive)',
          'inactive-bg': 'var(--semantic-inactive-bg)',
          'inactive-border': 'var(--semantic-inactive-border)',
          ai: 'var(--semantic-ai)',
          'ai-bg': 'var(--semantic-ai-bg)',
          'ai-border': 'var(--semantic-ai-border)',
          'ai-btn': 'var(--semantic-ai-btn)',
          'ai-hover': 'var(--semantic-ai-btn-hover)',
          'ai-text': 'var(--semantic-ai-btn-text)',
        },
        wood: {
          50: 'var(--wood-50)',
          100: 'var(--wood-100)',
          200: 'var(--wood-200)',
          300: 'var(--wood-300)',
          400: 'var(--wood-400)',
          500: 'var(--wood-500)',
          600: 'var(--wood-600)',
          700: 'var(--wood-700)',
          800: 'var(--wood-800)',
          900: 'var(--wood-900)',
          950: 'var(--wood-950)',
        },
        forest: {
          50: 'var(--semantic-success-bg)',
          100: 'var(--semantic-success-bg)',
          200: 'var(--semantic-success-border)',
          500: 'var(--semantic-success)',
          600: 'var(--semantic-success)',
          700: 'var(--semantic-success-hover)',
        },
        rust: {
          50: 'var(--semantic-alert-bg)',
          100: 'var(--semantic-alert-bg)',
          200: 'var(--semantic-alert-border)',
          500: 'var(--semantic-alert)',
          600: 'var(--semantic-alert)',
          700: 'var(--semantic-alert-hover)',
        },
        sage: {
          50: 'var(--semantic-success-bg)',
          100: 'var(--semantic-success-bg)',
          200: 'var(--semantic-success-border)',
          500: 'var(--semantic-success)',
          600: 'var(--semantic-success)',
        },
        charcoal: {
          DEFAULT: 'var(--text-primary)',
          50: 'var(--bg-canvas-subtle)',
          100: 'var(--border-subtle)',
          500: 'var(--text-muted)',
          700: 'var(--text-secondary)',
          900: 'var(--text-primary)',
        },
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'btn': 'var(--radius-btn)',
        'input': 'var(--radius-input)',
        'card': 'var(--radius-card)',
        'modal': 'var(--radius-modal)',
        '2xl': 'var(--radius-card)',
        'xl': 'var(--radius-input)',
      },
      boxShadow: {
        'xs': 'var(--shadow-xs)',
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-lg)',
        '2xl': 'var(--shadow-modal)',
      },
      transitionDuration: {
        fast: 'var(--duration-fast)',
        normal: 'var(--duration-normal)',
      }
    },
  },
  plugins: [],
}
