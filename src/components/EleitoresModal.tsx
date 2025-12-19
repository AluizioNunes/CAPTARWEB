import { Modal, Form, Input, Button, Select, DatePicker, Avatar, Card, App } from 'antd'
import { UserOutlined, IdcardOutlined, PhoneOutlined, EnvironmentOutlined, NumberOutlined } from '@ant-design/icons'
import { useEffect, useMemo, useState } from 'react'
import { useApi } from '../context/ApiContext'
import { useAuthStore } from '../store/authStore'
import dayjs from 'dayjs'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

interface Props {
  open: boolean
  initial?: any
  onCancel: () => void
  onSaved: () => void
}

export default function EleitoresModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [tenantOptions, setTenantOptions] = useState<{ value: string; label: string; slug?: string }[]>([])
  const api = useApi()
  const { user } = useAuthStore()
  const { message } = App.useApp()

  // Header Logic (Login time, etc)
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
        
        // Se não estiver editando, seta o tenant atual
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
        // Mapear campos se necessário (se o initial vier com chaves diferentes ou precisar de formatação)
        const data = { ...initial }
        // Garantir que datas sejam objetos dayjs para o DatePicker do Antd
        if (data.DataNascimento || data.data_nascimento) {
           const d = data.DataNascimento || data.data_nascimento
           data.data_nascimento = dayjs(d)
        }
        // Ajustar chaves se vierem do backend Capitalized mas o form usar lowercase
        if (data.Nome) data.nome = data.Nome
        if (data.CPF) data.cpf = data.CPF
        if (data.Celular) data.celular = data.Celular
        if (data.Bairro) data.bairro = data.Bairro
        if (data.ZonaEleitoral) data.zona_eleitoral = data.ZonaEleitoral

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
      
      // Formatações para envio
      if (values.data_nascimento) values.data_nascimento = values.data_nascimento.format('YYYY-MM-DD')
      if (typeof values.celular === 'string') {
        const c = String(values.celular)
        values.celular = c.length > 15 ? c.slice(0, 15) : c
      }

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

      // Limpar campos undefined
      Object.keys(values).forEach(key => values[key] === undefined && delete values[key])

      if (initial?.id || initial?.IdEleitor) {
        const id = initial.id || initial.IdEleitor
        await api.updateEleitor(id, values)
        message.success('Eleitor atualizado com sucesso!')
      } else {
        await api.createEleitor(values)
        message.success('Eleitor criado com sucesso!')
      }
      onSaved()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Erro ao salvar eleitor'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const formatCelular = (v: string) => {
    const d = (v || '').replace(/\D/g, '').slice(0, 11)
    if (d.length <= 2) return `(${d}`
    const area = d.slice(0, 2)
    const rest = d.slice(2)
    const restWith9 = rest[0] === '9' ? rest : ('9' + rest)
    const first = restWith9.slice(0, 5)
    const second = restWith9.slice(5, 9)
    if (!first) return `(${area})`
    if (!second) return `(${area}) ${first}`
    return `(${area}) ${first}-${second}`
  }

  const formatCpf = (v: string) => {
    const d = (v || '').replace(/\D/g, '').slice(0, 11)
    const p1 = d.slice(0, 3)
    const p2 = d.slice(3, 6)
    const p3 = d.slice(6, 9)
    const p4 = d.slice(9, 11)
    let out = p1
    if (p2) out += `.${p2}`
    if (p3) out += `.${p3}`
    if (p4) out += `-${p4}`
    return out
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
      className="eleitores-modal"
      destroyOnHidden
      closable={false}
      maskClosable={false}
    >
      <style>{`.eleitores-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .eleitores-modal .ant-modal-content{ border-radius: 0 !important; } .eleitores-modal .ant-form-item{ margin-bottom:6px; }`}</style>
      
      <Form form={form} layout="vertical">
        <div style={{ display: 'grid', gap: 16 }}>
            <Card title="Dados do Eleitor" size="small">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Form.Item name="nome" label="Nome" rules={[{ required: true, message: 'Nome é obrigatório' }]} getValueFromEvent={getUpperFromEvent}>
                    <Input prefix={<UserOutlined />} placeholder="Nome completo" style={{ borderRadius: 8 }} />
                </Form.Item>
                
                <Form.Item name="cpf" label="CPF">
                    <Input 
                    prefix={<IdcardOutlined />} 
                    placeholder="000.000.000-00" 
                    maxLength={14}
                    style={{ borderRadius: 8 }}
                    onChange={(e) => {
                        const masked = formatCpf(e.target.value)
                        form.setFieldsValue({ cpf: masked })
                    }}
                    />
                </Form.Item>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Form.Item name="celular" label="Celular">
                    <Input 
                    prefix={<PhoneOutlined />} 
                    placeholder="(00) 00000-0000" 
                    maxLength={15}
                    style={{ borderRadius: 8 }}
                    onChange={(e) => {
                        const masked = formatCelular(e.target.value)
                        form.setFieldsValue({ celular: masked })
                    }}
                    />
                </Form.Item>

                <Form.Item name="data_nascimento" label="Data de Nascimento">
                    <DatePicker format="DD/MM/YYYY" style={{ width: '100%', borderRadius: 8 }} />
                </Form.Item>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Form.Item name="bairro" label="Bairro" getValueFromEvent={getUpperFromEvent}>
                    <Input prefix={<EnvironmentOutlined />} placeholder="Bairro" style={{ borderRadius: 8 }} />
                </Form.Item>

                <Form.Item name="zona_eleitoral" label="Zona Eleitoral" getValueFromEvent={getUpperFromEvent}>
                    <Input prefix={<NumberOutlined />} placeholder="Zona" style={{ borderRadius: 8 }} />
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

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <Button onClick={onCancel} icon={<UserOutlined rotate={180} /> /* Using a placeholder icon, close usually just text or specific icon */}>
            Cancelar
          </Button>
          <Button type="primary" onClick={handleOk} loading={loading} icon={<UserOutlined /> /* Save icon usually */}>
            Salvar
          </Button>
        </div>
      </Form>
    </Modal>
  )
}
