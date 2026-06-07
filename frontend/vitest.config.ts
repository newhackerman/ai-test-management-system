import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    testTimeout: 10000, // 增加测试超时时间到10秒
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})