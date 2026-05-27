import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './hooks/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
    './simulation/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0a0e1a',
          panel: '#1a2035',
          card: '#0f1628',
          hover: '#202840',
        },
        accent: {
          blue: '#00d4ff',
          danger: '#ff4444',
          success: '#44ff88',
          warning: '#ffaa00',
          purple: '#cc44ff',
          teal: '#00ffcc',
          orange: '#ff8800',
        },
        border: {
          dim: '#2a3555',
          bright: '#3a4a7a',
        },
        text: {
          primary: '#e8f0ff',
          secondary: '#8899bb',
          dim: '#4a5a7a',
        },
      },
      fontFamily: {
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'pulse-fast': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'edge-flash': {
          '0%, 100%': { boxShadow: 'inset 0 0 0px rgba(255,68,68,0)' },
          '50%': { boxShadow: 'inset 0 0 80px rgba(255,68,68,0.4)' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.7', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.02)' },
        },
      },
      animation: {
        pulse: 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'pulse-fast': 'pulse-fast 0.8s ease-in-out infinite',
        shimmer: 'shimmer 2s linear infinite',
        'edge-flash': 'edge-flash 1s ease-in-out infinite',
        breathe: 'breathe 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
