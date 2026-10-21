/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0A121E',
          DEFAULT: '#0F1B2D',
          light: '#1B2C47',
        },
        turmeric: {
          DEFAULT: '#F5B700',
          hover: '#E0A600',
          light: '#FFF5D6',
        },
        cream: {
          DEFAULT: '#FFF8EC',
          paper: '#FDF3DF',
          muted: '#F4ECE0',
        },
        khataGreen: {
          DEFAULT: '#2E9E5B',
          light: '#E7F7ED',
        },
        khataRed: {
          DEFAULT: '#D64545',
          light: '#FDECEC',
        },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'serif', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'paper': '0 4px 20px -2px rgba(15, 27, 45, 0.08), 0 2px 6px -1px rgba(15, 27, 45, 0.04)',
        'paper-lg': '0 10px 30px -4px rgba(15, 27, 45, 0.12), 0 4px 12px -2px rgba(15, 27, 45, 0.06)',
        'turmeric-glow': '0 0 25px rgba(245, 183, 0, 0.45)',
      }
    },
  },
  plugins: [],
}
