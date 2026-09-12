/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#FAF7FC',
          100: '#F1EAF6',
          200: '#E2D3EB',
          300: '#C8ACD9',
          400: '#A87AC0',
          500: '#814DA5',
          600: '#5B2A86',
          700: '#4A226E',
          800: '#3E1A5F',
          900: '#301348',
          950: '#1F0B31',
        },
        campus: {
          green: '#175C4A',
          gold: '#B17A24',
        },
        paper: {
          DEFAULT: '#FFFEFC',
          warm: '#F7F5F1',
        },
        ink: {
          DEFAULT: '#211D24',
          muted: '#6F6873',
        },
        stone: '#DDD7DF',
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"Microsoft YaHei"', 'sans-serif'],
        serif: ['"Noto Serif SC"', 'SimSun', 'serif'],
      },
      borderRadius: {
        card: '8px',
      },
      boxShadow: {
        panel: '0 1px 2px rgb(33 29 36 / 0.06)',
        focus: '0 0 0 3px rgb(91 42 134 / 0.18)',
      },
      transitionDuration: {
        fast: '120ms',
        feedback: '180ms',
        page: '260ms',
      },
      maxWidth: {
        content: '1200px',
      },
    },
  },
  plugins: [],
}
