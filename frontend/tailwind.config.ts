import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#070a12", 900: "#0b101c", 800: "#111827", 700: "#1b2436", 600: "#2a3550" },
        accent: { DEFAULT: "#5eead4", strong: "#2dd4bf", soft: "#134e4a" },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
