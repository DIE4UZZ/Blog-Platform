/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,vue}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        mist: "#f5f6f8",
        slate: "#6b7280",
      },
      boxShadow: {
        soft: "0 24px 60px rgba(15, 23, 42, 0.12)",
      },
    },
  },
  plugins: [],
};
