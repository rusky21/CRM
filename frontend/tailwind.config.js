/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'tg-list': '#0e1621',
        'tg-chat': '#0f141c',
        'tg-header': '#17212b',
        'tg-border': '#232e3c',
        'tg-incoming': '#182533',
        'tg-outgoing': '#2b5278',
        'tg-accent': '#3390ec',
        'tg-accent-hover': '#4faeef',
        'tg-muted': '#708499',
        'tg-meta': '#74a7d6',
      },
    },
  },
  plugins: [],
};
