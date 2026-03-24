/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#7C6FCD",
          hover:   "#9080D8",
          soft:    "#2D2550",
        },
        bg: {
          primary:   'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          card:      'var(--bg-card)',
          elevated:  'var(--bg-elevated)',
        },
        border:  'var(--border)',
        text1:   'var(--text-1)',
        text2:   'var(--text-2)',
        text3:   'var(--text-3)',
        success: "#10B981",
        error:   "#EF4444",
        warning: "#F59E0B",
        muted:   'var(--text-3)',
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
          "Noto Sans JP",
          "Noto Sans CJK SC",
        ],
      },
    },
  },
  plugins: [],
};
