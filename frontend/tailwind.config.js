/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        aerospace: {
          950: '#070b14',
          900: '#0b1329',
          850: '#0f1c3d',
          800: '#15244d',
          700: '#1d3269',
          600: '#27438c',
          500: '#3559b3',
          400: '#4f75d9',
          300: '#7597ed',
          200: '#a3bcf5',
          100: '#d1defa',
        },
        cyan: {
          glow: '#00f0ff',
        },
        amber: {
          hazard: '#f59e0b',
        },
        crimson: {
          alert: '#ef4444',
        },
        radar: {
          emerald: '#10b981',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
