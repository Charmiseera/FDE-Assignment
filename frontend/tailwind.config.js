/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#EEF1F6",
          100: "#D7DEEA",
          200: "#B0BFD6",
          300: "#8AA0C1",
          400: "#5C7BA5",
          500: "#34547E",
          600: "#263F60",
          700: "#1C2E48",
          800: "#141F32",
          900: "#0D141F",
        },
        signal: {
          50: "#EAF6F4",
          100: "#C9EAE4",
          500: "#1E7F73",
          700: "#114D46",
        },
        paper: {
          50: "#FAF9F7",
          100: "#F2F0EC",
          200: "#E4E1DA",
          300: "#CFCBC1",
          400: "#A7A295",
          500: "#7D786C",
          600: "#5C584E",
          700: "#423F38",
          800: "#2A2824",
          900: "#171614",
        },
        success: { light: "#E7F3EA", base: "#1F7A44", dark: "#14532D" },
        warning: { light: "#FBF0DE", base: "#B4791A", dark: "#7A5211" },
        error: { light: "#F7E7E7", base: "#B23A3A", dark: "#7A2626" },
        info: { light: "#E6EFF8", base: "#2C6FA8", dark: "#1E4E77" },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        serif: ["Source Serif 4", "serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        none: "0",
        sm: "0.25rem",
        base: "0.375rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        full: "9999px",
      },
    },
  },
  plugins: [],
};
