/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-bg-default)",
        surface: "var(--color-bg-surface)",
        ink: "var(--color-text-default)",
        muted: "var(--color-text-muted)",
        dim: "var(--color-text-dim)",
        border: "var(--color-border-default)",
        primary: "var(--color-accent-primary)",
        danger: "var(--color-status-danger)",
        success: "var(--color-status-success)",
        warning: "var(--color-status-warning)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
        mono: ["Roboto Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
