/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#0A0B0D',
        darkCard: '#13161C',
        darkBorder: '#232A35',
        accentPrimary: '#00D4FF',
        accentSuccess: '#00E676',
        accentWarning: '#F5A623',
        accentDanger: '#FF4D4F',
        darkText: '#F3F4F6',
        darkMuted: '#9CA3AF',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
      boxShadow: {
        subtle: '0 2px 8px -1px rgba(0, 0, 0, 0.5)',
      }
    },
  },
  plugins: [],
}
