/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces (telemetry dark slate scale)
        background: "#0B0D11",
        foreground: "#F1F5F9",
        surface: "#11151D",
        "surface-border": "#232B3B",
        "surface-hover": "#1D2433",
        card: "#161B26",
        "card-foreground": "#F1F5F9",
        popover: "#161B26",
        "popover-foreground": "#F1F5F9",
        elevated: "#1D2433",

        // Primary: Governed/ICM indigo
        primary: "#6366F1",
        "primary-light": "#818CF8",
        "primary-foreground": "#ffffff",
        secondary: "#1D2433",
        "secondary-foreground": "#CBD5E1",
        muted: "#1D2433",
        // Lightened from #64748B/#8b949e to pass WCAG AA (>=4.5:1) on bg/surface
        "muted-foreground": "#94A3B8",
        accent: "#1D2433",
        "accent-foreground": "#F1F5F9",
        destructive: "#F87171",
        "destructive-foreground": "#ffffff",
        border: "#232B3B",
        input: "#2D3748",
        ring: "#6366F1",

        // Metric accents
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#F87171",
        baseline: "#E06C54",
        icm: "#6366F1",
        sage: {
          DEFAULT: "#10B981",
          light: "#34D399",
        },
        terracotta: "#E06C54",
        steel: {
          400: "#94A3B8",
          500: "#75859C",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
