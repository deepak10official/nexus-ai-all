/** @type {import('tailwindcss').Config} */
// Union of the MOD03 (Trend Radar) and MOD02 (Persona Panel) design tokens.
// Both palettes are kept so neither view's classes break. `ink` is shared —
// MOD03's slightly darker values win, since both are near-black.
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Space Grotesk'", "ui-sans-serif", "system-ui", "sans-serif"],
        body: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // shared shell
        ink: { 900: "#05070D", 800: "#0A0E18", 700: "#111726" },
        // MOD03 — Trend Radar
        saffron: "#FF9A3C",
        signal: "#35E0D8",
        violet: "#A78BFA",
        chalk: "#E9EDF5",
        muted: "#7E8AA0",
        // MOD02 — Persona Panel
        neon: {
          amber: "#f59e0b",
          orange: "#f97316",
          pink: "#ec4899",
          teal: "#2dd4bf",
          emerald: "#34d399",
          rose: "#fb7185",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.06), 0 20px 60px -20px rgba(0,0,0,0.8)",
        "glow-amber": "0 0 32px -8px rgba(249,115,22,0.55)",
        "glow-emerald": "0 0 30px -8px rgba(52,211,153,0.5)",
        "glow-rose": "0 0 30px -8px rgba(251,113,133,0.5)",
      },
      backgroundImage: {
        "grad-accent": "linear-gradient(90deg,#f59e0b 0%,#f97316 45%,#ec4899 100%)",
      },
      keyframes: {
        sweep: { to: { transform: "rotate(360deg)" } },
        pulseRing: {
          "0%": { transform: "scale(0.9)", opacity: "0.7" },
          "100%": { transform: "scale(1.6)", opacity: "0" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
      animation: {
        sweep: "sweep 4s linear infinite",
        pulseRing: "pulseRing 2.4s ease-out infinite",
        "fade-up": "fade-up 0.5s ease-out both",
        shimmer: "shimmer 3s linear infinite",
        "pulse-soft": "pulse-soft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
