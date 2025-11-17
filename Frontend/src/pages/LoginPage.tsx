import { useState } from 'react'
import { Form, Input, Button, Card, message, Divider } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import apiService from '../services/api'
import './LoginPage.css'

interface LoginFormValues {
  usuario: string
  senha: string
  acesso_direto?: boolean
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const onFinish = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      // Modo desenvolvedor - acesso direto
      if (values.acesso_direto) {
        const userData = {
          id: 9999,
          nome: 'USUÁRIO TEMPORÁRIO',
          funcao: 'ADMINISTRADOR',
          usuario: 'admin',
          email: 'admin@example.com',
          cpf: '000.000.000-00',
          perfil: 'ADMINISTRADOR',
          login_time: new Date().toLocaleString('pt-BR'),
        }
        login(userData, 'temp-token-dev')
        message.success('Acesso direto ativado!')
        navigate('/')
        return
      }

      // Autenticação normal contra a API
      const response = await apiService.login({
        usuario: values.usuario,
        senha: values.senha,
      })

      // Adicionar informações de login
      const userData = {
        ...response.user,
        login_time: new Date().toLocaleString('pt-BR'),
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

  return (
    <div className="login-container">
      <div className="login-wrapper">
        <Card className="login-card">
          <div className="login-header">
            <h1 className="login-title">CAPTAR</h1>
            <p className="login-subtitle">Sistema de Gestão Eleitoral v2.0</p>
          </div>

          <Form
            form={form}
            onFinish={onFinish}
            layout="vertical"
            className="login-form"
          >
            <Form.Item
              name="usuario"
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
        </Card>
      </div>
    </div>
  )
}
