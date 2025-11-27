import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme, App as AntdApp } from 'antd'
import { ApiProvider } from './context/ApiContext'
import ptBR from 'antd/locale/pt_BR'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={ptBR}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#667eea',
          borderRadius: 10,
          fontSize: 15,
          colorBgContainer: '#ffffff',
        },
        components: {
          Table: {
            headerBg: '#f5f7fa',
            headerColor: '#1f1f1f',
            borderRadius: 8,
            rowHoverBg: '#e6f4ff',
          },
          Card: {
            borderRadiusLG: 14,
          },
          Button: {
            borderRadius: 10,
          },
        },
      }}
    >
      <AntdApp>
        <ApiProvider>
          <App />
        </ApiProvider>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
