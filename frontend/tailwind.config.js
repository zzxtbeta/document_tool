/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f9fafb',   // 极浅灰
          100: '#f3f4f6',  // 浅灰
          200: '#e5e7eb',  // 中浅灰
          300: '#d1d5db',  // 灰
          400: '#9ca3af',  // 中灰
          500: '#6b7280',  // 深灰
          600: '#4b5563',  // 较深灰
          700: '#374151',  // 深灰
          800: '#1f2937',  // 极深灰
          900: '#111827',  // 黑
        },
        accent: {
          blue: '#3b82f6',    // 点缀色：蓝
          green: '#10b981',   // 点缀色：绿（成功）
          red: '#ef4444',     // 点缀色：红（错误）
          yellow: '#f59e0b',  // 点缀色：黄（警告）
        }
      },
    },
  },
  plugins: [],
}
