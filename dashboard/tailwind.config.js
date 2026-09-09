/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0d1117",
        surface: "#161b22",
        "surface-border": "#30363d",
        "surface-hover": "#21262d",
        primary: "#58a6ff",
        success: "#2ea043",
        warning: "#d29922",
        danger: "#f85149",
        baseline: "#f85149",
        icm: "#2ea043",
      },
    },
  },
  plugins: [],
}
