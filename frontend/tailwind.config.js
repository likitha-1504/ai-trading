/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      /* Extra alpha steps so fine-grained glass tints are available to
         colour opacity modifiers (e.g. bg-sky-500/8). */
      opacity: {
        2: "0.02",
        3: "0.03",
        4: "0.04",
        6: "0.06",
        8: "0.08",
        12: "0.12",
        15: "0.15",
        18: "0.18",
        22: "0.22",
        35: "0.35",
        45: "0.45",
        55: "0.55",
        65: "0.65",
        85: "0.85",
      },
      colors: {
        /* Deep space backgrounds */
        space: {
          void: "#050814",
          deep: "#070C1A",
          panel: "#0B1124",
          navy: "#0B132B",
        },
        /* Neon accents */
        "neon-cyan": "#00F0FF",
        "neon-blue": "#38BDF8",
        "neon-emerald": "#00E676",
        "neon-crimson": "#F43F5E",
        "ai-purple": "#8B5CF6",
        "ai-indigo": "#6366F1",
        /* Legacy semantic aliases (kept for existing screens) */
        root: "#050814",
        surface: {
          DEFAULT: "#0B1124",
          elevated: "#0B132B",
        },
        border: {
          subtle: "rgba(56, 189, 248, 0.14)",
          highlight: "rgba(56, 189, 248, 0.35)",
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
        display: ["'Orbitron'", "'Space Grotesk'", "sans-serif"],
        sans: [
          "'Space Grotesk'",
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
      },
      boxShadow: {
        "glow-cyan": "0 0 15px rgba(0,240,255,0.2)",
        "glow-blue": "0 0 20px rgba(56,189,248,0.15)",
        "glow-emerald": "0 0 18px rgba(16,185,129,0.22)",
        "glow-crimson": "0 0 22px rgba(239,68,68,0.35)",
        "glow-purple": "0 0 20px rgba(139,92,246,0.3)",
        "panel": "0 8px 32px -12px rgba(0,0,0,0.75)",
      },
      backgroundImage: {
        "neon-gradient":
          "linear-gradient(135deg, #00F0FF 0%, #38BDF8 45%, #8B5CF6 100%)",
        "hero-gradient":
          "linear-gradient(135deg, rgba(0,240,255,0.16) 0%, rgba(99,102,241,0.16) 50%, rgba(139,92,246,0.16) 100%)",
      },
      keyframes: {
        "orbit-spin": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.85)", opacity: "0.85" },
          "70%": { transform: "scale(1.35)", opacity: "0" },
          "100%": { transform: "scale(1.35)", opacity: "0" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        "twinkle": {
          "0%, 100%": { opacity: "0.15" },
          "50%": { opacity: "0.8" },
        },
        "float-up": {
          "0%": { transform: "translateY(0px)" },
          "100%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "orbit-slow": "orbit-spin 14s linear infinite",
        "orbit-rev": "orbit-spin 22s linear infinite reverse",
        "pulse-ring": "pulse-ring 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "pulse-glow": "pulse-glow 2.6s ease-in-out infinite",
        twinkle: "twinkle 4s ease-in-out infinite",
        "float-up": "float-up 3.2s ease-in-out infinite",
      },
      backgroundSize: {
        "50%": "50% 50%",
      },
    },
  },
  plugins: [],
}
