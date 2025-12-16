import { Modal, Form, Input, Button, message, Select, Avatar, Card, Space } from 'antd'
import { UserOutlined, TeamOutlined, SaveOutlined, CloseCircleOutlined } from '@ant-design/icons'
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
  onSaved: () => void
}

export default function AtivistasModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [tenantOptions, setTenantOptions] = useState<{ value: string; label: string; slug?: string }[]>([])
  const api = useApi()
  const { user } = useAuthStore()

  // Header Logic
  const loginDateObj = useMemo(() => {
    const lt = (user as any)?.login_time
    if (!lt) return null as Date | null
    const dIso = parseISO(lt as any)
    if (isValid(dIso)) return dIso
    const d = new Date(lt as any)
    return isNaN(d.getTime()) ? null : d
  }, [user])
  const [connectionText, setConnectionText] = useState('')
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
    const loadTenants = async () => {
      try {
        const res = await api.listTenants()
        const rows = res.rows || []
        const opts = rows.map((t: any) => ({ label: t.Nome ?? t.nome, value: String(t.Nome ?? t.nome), slug: t.Slug ?? t.slug }))
        setTenantOptions(opts)
        
        if (!initial) {
          const slug = localStorage.getItem('tenantSlug') || 'captar'
          const def = opts.find(o => (o.slug || '').toLowerCase() === slug.toLowerCase())
          if (def) form.setFieldValue('TenantLayer', def.value)
        }
      } catch {}
    }

    if (open) {
      loadTenants()
      if (initial) {
        const data = { ...initial }
        if (data.Nome) data.nome = data.Nome
        if (data.TipoApoio) data.tipo_apoio = data.TipoApoio
        if (data.AreaAtuacao) data.area_atuacao = data.AreaAtuacao
        
        form.setFieldsValue(data)
      } else {
        form.resetFields()
      }
    }
  }, [open, initial, form, api])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      const currentTenantName = String(localStorage.getItem('tenantName') || 'CAPTAR')
      const myTenantName = String(values.TenantLayer || currentTenantName)

      try {
        const resTen = await api.listTenants()
        const rowsTen = resTen.rows || []
        const selectedName = String(values.TenantLayer || myTenantName)
        const t = rowsTen.find((r: any) => String(r.Nome ?? r.nome).toUpperCase() === selectedName.toUpperCase())
          || rowsTen.find((r: any) => String(r.Slug ?? r.slug).toUpperCase() === String(localStorage.getItem('tenantSlug') || 'captar').toUpperCase())
        if (t) { 
           delete (values as any).IdTenant 
        }
      } catch {}

      Object.keys(values).forEach(key => values[key] === undefined && delete values[key])

      if (initial?.id || initial?.IdAtivista) {
        const id = initial.id || initial.IdAtivista
        await api.updateAtivista(id, values)
        message.success('Ativista atualizado com sucesso!')
      } else {
        await api.createAtivista(values)
        message.success('Ativista criado com sucesso!')
      }
      onSaved()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Erro ao salvar ativista'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const getUpperFromEvent = (e: any) => {
    const v = e?.target?.value
    return typeof v === 'string' ? v.toUpperCase() : v
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
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={980}
      centered
      footer={null}
      className="ativistas-modal"
      destroyOnHidden
      closable={false}
      maskClosable={false}
    >
      <style>{`.ativistas-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .ativistas-modal .ant-modal-content{ border-radius: 0 !important; } .ativistas-modal .ant-form-item{ margin-bottom:6px; }`}</style>
      
      <Form form={form} layout="vertical">
        <div style={{ display: 'grid', gap: 16 }}>
            <Card title="Dados do Ativista" size="small">
                <Form.Item name="nome" label="Nome" rules={[{ required: true, message: 'Nome é obrigatório' }]} getValueFromEvent={getUpperFromEvent}>
                <Input prefix={<UserOutlined />} placeholder="Nome completo" style={{ borderRadius: 8 }} />
                </Form.Item>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Form.Item name="tipo_apoio" label="Tipo de Apoio">
                    <Select placeholder="Selecione" style={{ borderRadius: 8 }}>
                    <Select.Option value="VOLUNTARIO">Voluntário</Select.Option>
                    <Select.Option value="APOIADOR">Apoiador</Select.Option>
                    <Select.Option value="LIDERANCA">Liderança</Select.Option>
                    <Select.Option value="COORDENADOR">Coordenador</Select.Option>
                    </Select>
                </Form.Item>

                <Form.Item name="area_atuacao" label="Área de Atuação" getValueFromEvent={getUpperFromEvent}>
                    <Input prefix={<TeamOutlined />} placeholder="Ex: Saúde, Educação" style={{ borderRadius: 8 }} />
                </Form.Item>
                </div>
            </Card>

            <Card title="Vinculação" size="small">
                <Form.Item name="TenantLayer" label="Tenant Layer" rules={[{ required: true }]}>
                <Select
                    options={tenantOptions}
                    optionFilterProp="label"
                    showSearch
                    style={{ borderRadius: 8 }}
                    disabled={!!initial}
                />
                </Form.Item>
            </Card>
        </div>

        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
          <Button type="primary" onClick={handleOk} loading={loading} icon={<SaveOutlined />}>SALVAR</Button>
        </Space>
      </Form>
    </Modal>
  )
}
