import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { viteMockServe } from 'vite-plugin-mock'

// https://vite.dev/config/
export default defineConfig({
  // 相对路径 base，方便后续任意路径部署
  base: './',
  plugins: [
    vue(),
    // Element Plus 按需引入：自动导入 API（如 ElMessage）与组件（含对应样式）
    AutoImport({
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
    // 开发期 mock 数据层：拦截 /admin/api/* 返回假数据（仅 serve 模式生效，build 产物不含 mock）
    viteMockServe({
      mockPath: 'mock',
      logger: true,
    }),
  ],
  server: {
    proxy: {
      // 开发代理：/admin 前缀请求转发到后端服务（供 Task 10 真实联调使用）
      '/admin': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
