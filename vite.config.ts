import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = env.VITE_API_URL || 'http://localhost:8000/api'
  let proxyTarget = apiUrl.replace(/\/api\/?$/, '')

  // Fix for when VITE_API_URL is relative (e.g. /api)
  if (!proxyTarget || proxyTarget.startsWith('/')) {
    const backendPort = env.FASTAPI_HOST_PORT || '8001'
    proxyTarget = `http://localhost:${backendPort}`
  }

  return {
    plugins: [react()],
    server: {
      port: 5500,
      host: '0.0.0.0',
      strictPort: false,
      open: false,
      cors: true,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false
        }
      },
      // HMR sem porta fixa para sincronizar com a porta ativa
      hmr: {
        protocol: 'ws'
      }
    },
    preview: {
      port: 5500,
      host: '0.0.0.0',
      strictPort: false
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      minify: 'terser',
      target: 'ES2020',
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'ui-vendor': ['antd', '@ant-design/icons'],
            'utils': ['axios', 'zustand', 'date-fns', 'framer-motion'],
            'charts-vendor': ['echarts']
          }
        }
      }
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-router-dom', 'antd', 'axios', 'zustand']
    }
  }
})
