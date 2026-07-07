import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f17",
        surface: "#131926",
        "surface-2": "#1b2435",
        border: "#26304a",
        brand: "#6366f1",
        "brand-hover": "#818cf8",
        muted: "#94a3b8",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
