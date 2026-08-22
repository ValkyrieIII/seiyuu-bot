import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { viteMockServe } from 'vite-plugin-mock'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useMock = env.VITE_USE_MOCK === 'true'
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://localhost:8080'

  return {
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
      ...(useMock
        ? [viteMockServe({
            mockPath: 'mock',
            logger: true,
          })]
        : []),
    ],
    server: {
      host: '0.0.0.0',
      proxy: {
        '/admin': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
