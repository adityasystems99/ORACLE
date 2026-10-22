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
        cyber: {
          950: "#090d16",
          900: "#0f172a",
          850: "#131d35",
          800: "#1e293b",
          700: "#334155",
          accent: "#38bdf8",
          neon: "#00f0ff",
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 20px -5px rgba(56, 189, 248, 0.25)",
        "glow-rose": "0 0 20px -5px rgba(244, 63, 94, 0.3)",
        "glow-neon": "0 0 25px -5px rgba(0, 240, 255, 0.35)",
      },
    },
  },
  plugins: [],
}
