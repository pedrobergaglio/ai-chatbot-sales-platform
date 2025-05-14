/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./templates/partials/*.html",
    "./templates/*.html",
  ],
  theme: {
    extend: {
      colors: {
          primary: '#0B5394',
          secondary: '#2D2D2D',
          dark: '#1E1E1E',
      }
    },
  },
  plugins: [],
} 