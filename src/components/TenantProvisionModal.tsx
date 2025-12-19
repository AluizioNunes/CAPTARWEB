import { Modal, Form, Input, Button, Space, Avatar, App } from 'antd'
import { SaveOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useApi } from '../context/ApiContext'
import { useEffect, useMemo, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

interface Props {
  open: boolean
  initial?: { nome?: string; slug?: string; db_name?: string; db_host?: string; db_port?: string; db_user?: string; db_password?: string }
  onCancel: () => void
  onSaved: (res: { idTenant: number; dsn: string }) => void
}

export default function TenantProvisionModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const api = useApi()
  const { user } = useAuthStore()
  const { message } = App.useApp()
  const [connectionText, setConnectionText] = useState('')
  const loginDateObj = useMemo(() => {
    const lt = (user as any)?.login_time
    if (!lt) return null as Date | null
    const dIso = parseISO(lt as any)
    if (isValid(dIso)) return dIso
    const d = new Date(lt as any)
    return isNaN(d.getTime()) ? null : d
  }, [user])
  const loginText = loginDateObj ? format(loginDateObj, 'dd/MM/yyyy HH:mm', { locale: ptBR }) : ''
  const currentTenantSlug = String(localStorage.getItem('tenantSlug') || 'captar')
  const currentTenantName = String(localStorage.getItem('tenantName') || 'CAPTAR')

  useEffect(() => {
    if (open) {
      if (initial) form.setFieldsValue(initial)
      else form.resetFields()
    }
  }, [open, initial])

  useEffect(() => {
    const update = () => {
      if (!loginDateObj) { setConnectionText(''); return }
      const diff = Date.now() - loginDateObj.getTime()
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      const hh = String(h).padStart(2, '0')
      const mm = String(m).padStart(2, '0')
      const ss = String(s).padStart(2, '0')
      setConnectionText(`${hh}:${mm}:${ss}`)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [loginDateObj])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      const res = await api.provisionTenant(values)
      message.success(`Banco provisionado: ${res.dsn}`)
      onSaved({ idTenant: res.idTenant, dsn: res.dsn })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao provisionar banco')
    }
  }

  return (
    <Modal
      open={open}
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="navbar-logo" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src={Logo} alt="CAPTAR" style={{ height: 110, backgroundColor: '#ffffff', borderRadius: 8, padding: 6 }} />
            <div style={{ fontSize: 12 }}>
              TENANT: <strong style={{ color: '#333' }}>{String(currentTenantName || currentTenantSlug).toUpperCase()}</strong>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: 700 }}>
                {(user as any)?.usuario ? String((user as any)?.usuario).toUpperCase() : String((user as any)?.nome || '').toUpperCase() || 'USUÁRIO'}
              </div>
              <div style={{ fontSize: 12 }}>
                {`FUNÇÃO: ${String((user as any)?.funcao || '').toUpperCase()} | PERFIL: ${String((user as any)?.perfil || '').toUpperCase()}`}
              </div>
              <div style={{ fontSize: 12 }}>
                {`LOGIN: ${loginText || '--'} | TEMPO CONECTADO: ${connectionText || '--:--:--'}`}
              </div>
            </div>
            <Avatar size="large" />
          </div>
        </div>
      }
      onCancel={onCancel}
      footer={null}
      destroyOnHidden
      width={800}
      closable={false}
      maskClosable={false}
      className="tenants-modal"
    >
      <style>{`.tenants-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .tenants-modal .ant-modal-content{ border-radius: 0 !important; } .tenants-modal .ant-form-item{ margin-bottom:6px; }`}</style>
      <Form form={form} layout="vertical">
        <Form.Item name="nome" label="Nome" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="slug" label="Slug" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="db_name" label="Nome do Banco" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="db_host" label="Host" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="db_port" label="Porta" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="db_user" label="Usuário" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="db_password" label="Senha" rules={[{ required: true }]}> 
          <Input.Password />
        </Form.Item>
        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
          <Button type="primary" onClick={handleOk} icon={<SaveOutlined />}>SALVAR</Button>
        </Space>
      </Form>
    </Modal>
  )
}

