import type { Config } from 'tailwindcss';

export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        ink: '#13233f',
        harbor: '#2c6aa6'
      }
    }
  },
  plugins: []
} satisfies Config;
