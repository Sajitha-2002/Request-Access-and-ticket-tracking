/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        nila: {
          50:  '#f0eeff',
          100: '#e5e0ff',
          200: '#cec5ff',
          300: '#ac9aff',
          400: '#8b6bff',
          500: '#6c63ff',
          600: '#5a4fe6',
          700: '#4a3ec8',
          800: '#3d35a3',
          900: '#332f85',
          950: '#1e1b52',
        },
        dark: {
          50:  '#f0f0f5',
          100: '#d8d8e8',
          200: '#b0b0cc',
          300: '#8888b0',
          400: '#606090',
          500: '#3d3d6e',
          600: '#2e2e58',
          700: '#1f1f44',
          800: '#141430',
          900: '#0c0c1e',
          950: '#06060f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'wave': 'wave 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(108, 99, 255, 0.4)' },
          '50%': { boxShadow: '0 0 30px rgba(108, 99, 255, 0.8)' },
        },
        wave: {
          '0%': { transform: 'rotate(0deg)' },
          '25%': { transform: 'rotate(20deg)' },
          '50%': { transform: 'rotate(-10deg)' },
          '75%': { transform: 'rotate(15deg)' },
          '100%': { transform: 'rotate(0deg)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
