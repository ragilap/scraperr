/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,css,ico}",  // Include the app directory
    "./public/**/*.{js,ts,jsx,tsx,css,ico}"  // If you're using any static HTML files
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}