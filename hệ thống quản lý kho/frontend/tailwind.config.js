/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Geist', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        wood: {
          50: '#FDF8F0',   // Soft Parchment (nền sáng tự nhiên)
          100: '#F5EDE0',  // Cream Linen (nền thẻ, header)
          200: '#E8D5B7',  // Light Birch (đường viền divider)
          300: '#D4A04A',  // Golden Amber (hổ phách sáng)
          400: '#C4893B',  // Honey Oak (sồi mật ong - secondary)
          500: '#8B5E3C',  // Warm Cedar (tuyết tùng ấm - PRIMARY BRAND)
          600: '#754B2E',  // Warm Cedar hover
          700: '#5C3A1E',  // Dark Oak (gỗ sồi đậm)
          800: '#4A2D16',  // Deep Timber
          900: '#3B2314',  // Deep Walnut (óc chó đậm - Sidebar background)
          950: '#26140A',  // Midnight Walnut
        },
        forest: {
          50: '#F1F7F2',
          100: '#DDECE0',
          200: '#B8D7BE',
          500: '#2D5F3A',  // Forest Green (Thành công / An toàn)
          600: '#234C2E',
          700: '#1A3922',
        },
        rust: {
          50: '#FDF3EE',
          100: '#F9E2D6',
          200: '#F2C1A8',
          500: '#A0522D',  // Warm Rust (Cảnh báo tồn / Xuất âm)
          600: '#854222',
          700: '#693319',
        },
        sage: {
          50: '#F4F7F4',
          100: '#E5EDE6',
          500: '#7A9A7E',  // Muted Sage
          600: '#638067',
        },
        charcoal: {
          DEFAULT: '#3C3C3C',
          50: '#F7F7F7',
          100: '#EFEFEF',
          500: '#555555',
          700: '#3C3C3C',
          900: '#222222',
        },
      },
      borderRadius: {
        'btn': '6px', // Button radius từ Figma: 6.0px
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      }
    },
  },
  plugins: [],
}
