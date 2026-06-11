/** Donna — editorial, memory-native. Colors are CSS variables so Morning/Night
 *  swap with a single class. Rust is the only accent and is used sparingly. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--bg) / <alpha-value>)',
        'bg-deep': 'rgb(var(--bg-deep) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        'surface-warm': 'rgb(var(--surface-warm) / <alpha-value>)',
        ink: 'rgb(var(--ink) / <alpha-value>)',
        soft: 'rgb(var(--soft) / <alpha-value>)',
        faint: 'rgb(var(--faint) / <alpha-value>)',
        rust: 'rgb(var(--rust) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)',
        line: 'rgb(var(--line) / <alpha-value>)',
        espresso: '#251D16',
        cream: '#F3EBE1',
        copper: '#C99A7E',
        green: '#3D7A4E',
        amber: '#B07A3E',
      },
      fontFamily: {
        serif: ['"EB Garamond"', 'Georgia', 'serif'],
        sans: ['"Red Hat Text"', '-apple-system', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        label: '0.16em',
      },
    },
  },
  plugins: [],
}
