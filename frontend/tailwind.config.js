/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: {
      ink:    "#0b0f17",
      panel:  "#111827",
      line:   "#1f2937",
      accent: "#22d3ee",
      warn:   "#f59e0b",
      danger: "#ef4444",
      ok:     "#10b981",
    }
  }},
  plugins: [],
};
