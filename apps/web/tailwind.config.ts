import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // SplitSmart AI brand palette — dark fintech
        brand: {
          50: "hsl(240, 100%, 98%)",
          100: "hsl(240, 96%, 94%)",
          200: "hsl(242, 87%, 85%)",
          300: "hsl(243, 80%, 75%)",
          400: "hsl(245, 75%, 65%)",
          500: "hsl(245, 70%, 55%)", // Primary indigo
          600: "hsl(247, 65%, 45%)",
          700: "hsl(248, 60%, 38%)",
          800: "hsl(249, 58%, 30%)",
          900: "hsl(250, 55%, 22%)",
        },
        accent: {
          // Vibrant teal for secondary actions
          400: "hsl(174, 72%, 56%)",
          500: "hsl(174, 72%, 44%)",
        },
        gold: {
          // Premium gold for highlights
          400: "hsl(45, 93%, 58%)",
          500: "hsl(38, 92%, 50%)",
        },
        surface: {
          // Dark mode surfaces
          900: "hsl(224, 71%, 4%)",   // Background
          800: "hsl(222, 47%, 8%)",   // Card
          700: "hsl(220, 39%, 12%)",  // Elevated card
          600: "hsl(218, 32%, 18%)",  // Border/separator
          500: "hsl(216, 28%, 24%)",  // Input/subtle
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-hero": "linear-gradient(135deg, hsl(245,70%,55%) 0%, hsl(174,72%,44%) 100%)",
        "gradient-card": "linear-gradient(145deg, hsl(222,47%,10%) 0%, hsl(220,39%,14%) 100%)",
        "gradient-glow": "radial-gradient(circle at 50% 0%, hsl(245,70%,55%,0.15) 0%, transparent 70%)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "slide-in-right": "slideInRight 0.35s ease-out",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "spin-slow": "spin 3s linear infinite",
        "bounce-gentle": "bounceGentle 2s ease-in-out infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        bounceGentle: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        glow: {
          "0%": { boxShadow: "0 0 20px hsl(245,70%,55%,0.3)" },
          "100%": { boxShadow: "0 0 40px hsl(245,70%,55%,0.6), 0 0 80px hsl(174,72%,44%,0.2)" },
        },
      },
      boxShadow: {
        "glow-brand": "0 0 30px hsl(245,70%,55%,0.4)",
        "glow-accent": "0 0 30px hsl(174,72%,44%,0.4)",
        "card": "0 4px 24px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3)",
        "card-hover": "0 8px 40px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
