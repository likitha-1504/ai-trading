/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        root: "#0B0E14",
        surface: {
          DEFAULT: "#151A23",
          elevated: "#1C2331",
        },
        border: {
          subtle: "#222938",
          highlight: "#334155",
        },
        bullish: "#10B981",
        bearish: "#EF4444",
        fact: {
          badge: "#0284C7",
          border: "#0369A1",
        },
        ai: {
          badge: "#8B5CF6",
          border: "#6D28D9",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
      },
    },
  },
  plugins: [],
}
