/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#e8f0fe',
          100: '#c5d5f8',
          500: '#1a4a7a',
          600: '#153d6b',
          700: '#0f2f52',
          800: '#0a2240',
          900: '#061529',
        },
        teal: {
          400: '#2dd4c8',
          500: '#14b8a6',
          600: '#0d9488',
        }
      },
      fontFamily: {
        sans: ['var(--font-outfit)', 'sans-serif'],
        display: ['var(--font-syne)', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
