import { useState, useEffect } from 'react'
import { Form, Input, Button, Divider, Tag, Space, Modal, App as AntdApp } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useApi } from '../context/ApiContext'
import LoginLogo from '../images/CAPTAR LOGIN.png'

interface LoginFormValues {
  usuario: string
  senha: string
  acesso_direto?: boolean
}

export default function Login() {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [dbOk, setDbOk] = useState<null | boolean>(null)
  const [form] = Form.useForm()
  const api = useApi()
  const [loginLogoSrc, setLoginLogoSrc] = useState<string | null>(null)

  const onFinish = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      // Modo desenvolvedor - acesso direto
      if (values.acesso_direto) {
        try { localStorage.setItem('tenantSlug', 'captar') } catch {}
        const userData = {
          id: 9999,
          nome: 'USUÁRIO TEMPORÁRIO',
          funcao: 'ADMINISTRADOR',
          usuario: 'admin',
          email: 'admin@example.com',
          cpf: '000.000.000-00',
          perfil: 'ADMINISTRADOR',
          login_time: new Date().toISOString(),
        }
        login(userData, 'temp-token-dev')
        message.success('Acesso direto ativado!')
        navigate('/')
        return
      }

      // Autenticação normal contra a API
      const response = await api.login({
        usuario: values.usuario,
        senha: values.senha,
      })

      // Adicionar informações de login
      const userData = {
        ...response.user,
        login_time: new Date().toISOString(),
      }

      login(userData, response.token)
      message.success('Login realizado com sucesso!')
      navigate('/')
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Usuário ou senha inválidos')
    } finally {
      setLoading(false)
    }
  }

  const checkDb = async () => {
    try {
      const res = await api.healthDb()
      setDbOk(!!res?.ok)
      if (res?.ok) message.success('Conexão com banco OK')
    } catch (e: any) {
      setDbOk(false)
      message.error(e?.response?.data?.detail || 'Falha ao conectar no banco')
    }
  }

  useEffect(() => {
    const src = LoginLogo as unknown as string
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const w = img.naturalWidth || 512
      const h = img.naturalHeight || 512
      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) { setLoginLogoSrc(src); return }
      ctx.drawImage(img, 0, 0, w, h)
      const imageData = ctx.getImageData(0, 0, w, h)
      const data = imageData.data
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]
        const max = Math.max(r, g, b)
        const min = Math.min(r, g, b)
        if (max > 230 && min > 210) data[i + 3] = 0
      }
      ctx.putImageData(imageData, 0, 0)
      setLoginLogoSrc(canvas.toDataURL('image/png'))
    }
    img.src = src
  }, [])

  return (
    <div style={{ minHeight: '100vh' }}>

      <Modal open centered footer={null} closable={false} maskClosable={false} width={520} destroyOnHidden className="login-modal">
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <style>{`.login-modal .ant-modal-content{ border-radius:0 !important; box-shadow:none !important; border:none !important; } .login-modal .ant-modal-header{ border-bottom:none !important; }`}</style>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <img src={loginLogoSrc || LoginLogo} alt="CAPTAR" style={{ width: 400, height: 'auto', maxWidth: '90%' }} />
          </div>
          <Form
            form={form}
            onFinish={onFinish}
            layout="vertical"
            className="login-form"
            style={{ width: '100%' }}
          >
            <Form.Item
              name="usuario"
              getValueFromEvent={(e) => (e?.target?.value || '').toUpperCase()}
              rules={[
                { required: true, message: 'Por favor, insira seu usuário' },
                { min: 3, message: 'Usuário deve ter pelo menos 3 caracteres' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Usuário"
                size="large"
                autoComplete="username"
                style={{ textTransform: 'uppercase' }}
              />
            </Form.Item>

            <Form.Item
              name="senha"
              rules={[
                { required: true, message: 'Por favor, insira sua senha' },
                { min: 3, message: 'Senha deve ter pelo menos 3 caracteres' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Senha"
                size="large"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                loading={loading}
                className="login-button"
              >
                ENTRAR
              </Button>
            </Form.Item>
          </Form>

          <Space style={{ width: '100%', justifyContent: 'space-between', marginTop: 8 }}>
            <div>
              <span>Status BD: </span>
              {dbOk === null && <Tag>?</Tag>}
              {dbOk === true && <Tag color="green">OK</Tag>}
              {dbOk === false && <Tag color="red">FALHA</Tag>}
            </div>
            <Button size="small" onClick={checkDb}>Testar conexão</Button>
          </Space>

          <Divider>OU</Divider>

          <Button
            type="dashed"
            size="large"
            block
            loading={loading}
            className="dev-button"
            onClick={() => {
              onFinish({ usuario: '', senha: '', acesso_direto: true })
            }}
          >
            🔧 Acesso Direto (Desenvolvedor)
          </Button>

          <div className="login-footer">
            <p>CAPTAR © 2025 - Sistema de Captação Eleitoral</p>
            <p className="version">v2.0 - React + TypeScript + Vite</p>
          </div>
        </div>
      </Modal>
    </div>
  )
}
