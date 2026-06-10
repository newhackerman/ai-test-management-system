// @ts-nocheck
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'react-redux'
import { PersistGate } from 'redux-persist/integration/react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { store, persistor } from './store'
// import { Toaster } from 'react-hot-toast' // 绉婚櫎锛屼娇鐢ˋpp.tsx涓殑sonner

import App from './App.tsx'
import './index.css'

// 鍒涘缓 React Query 瀹㈡埛绔?
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5鍒嗛挓
      gcTime: 10 * 60 * 1000, // 10鍒嗛挓 (鍘?cacheTime)
      retry: 3,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Provider store={store}>
    <PersistGate loading={<div>Loading...</div>} persistor={persistor}>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider
          locale={zhCN}
          theme={{
            token: {
              colorPrimary: '#2563eb',
              borderRadius: 6,
              controlHeight: 32,
              fontFamily:
                "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif",
            },
            components: {
              Button: {
                primaryShadow: 'none',
                defaultShadow: 'none',
              },
              Card: {
                paddingLG: 16,
                headerHeight: 44,
              },
              Table: {
                cellPaddingBlock: 9,
                cellPaddingInline: 12,
                headerBg: '#f8fafc',
                headerColor: '#475569',
              },
            },
          }}
        >
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <App />
            {/* Toaster moved to App.tsx using sonner */}
          </BrowserRouter>
        </ConfigProvider>
      </QueryClientProvider>
    </PersistGate>
  </Provider>
)
