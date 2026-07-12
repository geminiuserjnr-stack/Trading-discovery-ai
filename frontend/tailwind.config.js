/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#F3F4F6',       /* Clean light gray background */
        darkCard: '#FFFFFF',     /* Pure white card backgrounds */
        darkBorder: '#E5E7EB',   /* Soft gray border */
        accentPrimary: '#2563EB', /* Professional Royal Blue accent */
        accentSuccess: '#10B981', /* Clean emerald green */
        accentWarning: '#F59E0B', /* Warm warning amber */
        accentDanger: '#EF4444',  /* High visibility crimson red */
        darkText: '#111827',     /* Deep charcoal readable text */
        darkMuted: '#6B7280',    /* Muted Slate text */
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
      }
    },
  },
  plugins: [],
}
