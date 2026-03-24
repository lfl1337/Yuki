/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#7C6FCD",
          hover: "#9080D8",
          soft: "#2D2550",
        },
        bg: {
          primary: "#09090b",
          secondary: "#18181b",
          card: "#27272a",
          elevated: "#3f3f46",
        },
        border: "#52525b",
        success: "#10B981",
        error: "#EF4444",
        warning: "#F59E0B",
        muted: "#71717a",
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
