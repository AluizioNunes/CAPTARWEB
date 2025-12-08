import { Modal, Form, Input, Select, Button, Space, Avatar } from 'antd'
import { SaveOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useEffect, useMemo, useState } from 'react'
import { useApi } from '../context/ApiContext'
import { useAuthStore } from '../store/authStore'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

interface Props {
  open: boolean
  initial?: any
  onCancel: () => void
  onSaved: (row: any) => void
}

export default function TenantsModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const api = useApi()
  const { user } = useAuthStore()
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

  useEffect(() => {
    if (open) {
      if (initial) form.setFieldsValue({ Nome: initial.Nome, Slug: initial.Slug, Status: initial.Status, Plano: initial.Plano })
      else form.resetFields()
    }
  }, [open, initial])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if (initial?.IdTenant) {
        await api.updateTenant(initial.IdTenant, values)
        const row = { ...initial, ...values }
        onSaved(row)
      } else {
        const res = await api.createTenant(values)
        const row = { IdTenant: res.id, Nome: values.Nome, Slug: values.Slug, Status: values.Status ?? 'ATIVO', Plano: values.Plano ?? 'PADRAO' }
        onSaved(row)
      }
    } catch {}
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
        <div style={{ display: 'grid', gap: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <Form.Item name="Nome" label="Nome" rules={[{ required: true }]}> 
                <Input />
              </Form.Item>
              <Form.Item name="Slug" label="Slug" rules={[{ required: true }]}> 
                <Input />
              </Form.Item>
            </div>
            <div>
              <Form.Item name="Status" label="Status"> 
                <Select options={[{ value: 'ATIVO', label: 'ATIVO' }, { value: 'INATIVO', label: 'INATIVO' }]} />
              </Form.Item>
              <Form.Item name="Plano" label="Plano"> 
                <Select options={[{ value: 'PADRAO', label: 'PADRÃO' }, { value: 'PRO', label: 'PRO' }]} />
              </Form.Item>
            </div>
          </div>
        </div>
        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
          <Button type="primary" onClick={handleOk} icon={<SaveOutlined />}>SALVAR</Button>
        </Space>
      </Form>
    </Modal>
  )
}

