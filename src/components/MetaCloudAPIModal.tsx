import { Avatar, Button, Form, Input, Modal, Space, Switch, App } from 'antd'
import { CloseCircleOutlined, SaveOutlined } from '@ant-design/icons'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useApi } from '../context/ApiContext'
import { useAuthStore } from '../store/authStore'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

interface Props {
  open: boolean
  initial?: any | null
  onCancel: () => void
  onSaved: () => void
}

export default function MetaCloudAPIModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const api = useApi()
  const { user } = useAuthStore()
  const { message } = App.useApp()
  const [saving, setSaving] = useState(false)
  const [resolving, setResolving] = useState(false)
  const lastEditedRef = useRef<'whatsapp_phone' | 'phone_number_id' | null>(null)
  const lastResolveKeyRef = useRef<string>('')

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
    if (!open) return
    if (initial) {
      form.setFieldsValue({
        perfil: initial.perfil || '',
        base_url: initial.base_url || 'https://graph.facebook.com',
        api_version: initial.api_version || 'v21.0',
        whatsapp_phone: initial.whatsapp_phone || '',
        phone_number_id: initial.phone_number_id || '',
        business_account_id: initial.business_account_id || '',
        app_id: initial.app_id || '',
        configuration_id: initial.configuration_id || '',
        partner_solution_id: initial.partner_solution_id || '',
        redirect_uri: initial.redirect_uri || '',
        validate_signature: initial.validate_signature === true,
        enabled: initial.enabled !== false,
        access_token: '',
        webhook_verify_token: '',
        app_secret: '',
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        base_url: 'https://graph.facebook.com',
        api_version: 'v21.0',
        validate_signature: false,
        enabled: true,
      })
    }
    lastEditedRef.current = null
    lastResolveKeyRef.current = ''
  }, [open, initial, form])

  const maybeResolve = async () => {
    const cfgId = Number(initial?.id || 0)
    const values = form.getFieldsValue()
    const waba = String(values.business_account_id || '').trim()
    const phoneId = String(values.phone_number_id || '').trim()
    const wa = String(values.whatsapp_phone || '').trim()
    const tempToken = String(values.access_token || '').trim()
    const baseUrl = String(values.base_url || '').trim()
    const apiVer = String(values.api_version || '').trim()
    const last = lastEditedRef.current
    if (!last) return

    const key = `${last}|${waba}|${phoneId}|${wa}`
    if (key === lastResolveKeyRef.current) return
    lastResolveKeyRef.current = key

    try {
      setResolving(true)
      if (last === 'whatsapp_phone' && wa) {
        const res = await api.resolveMetaWhatsAppPhone(
          {
            waba_id: waba || undefined,
            whatsapp_phone: wa,
            access_token: tempToken || undefined,
            base_url: baseUrl || undefined,
            api_version: apiVer || undefined,
          },
          cfgId || undefined
        )
        const nextPhoneId = String((res as any)?.phone_number_id || '').trim()
        if (nextPhoneId) {
          form.setFieldValue('phone_number_id', nextPhoneId)
          lastEditedRef.current = null
        }
      }
      if (last === 'phone_number_id' && phoneId) {
        const res = await api.resolveMetaWhatsAppPhone(
          {
            phone_number_id: phoneId,
            access_token: tempToken || undefined,
            base_url: baseUrl || undefined,
            api_version: apiVer || undefined,
          },
          cfgId || undefined
        )
        const nextWa = String((res as any)?.whatsapp_phone || '').trim()
        if (nextWa) {
          form.setFieldValue('whatsapp_phone', nextWa)
          lastEditedRef.current = null
        }
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao sincronizar WhatsApp Phone e PhoneID')
    } finally {
      setResolving(false)
    }
  }

  const whatsappPhoneWatch = Form.useWatch('whatsapp_phone', form)
  const phoneIdWatch = Form.useWatch('phone_number_id', form)
  const wabaWatch = Form.useWatch('business_account_id', form)
  useEffect(() => {
    if (!open) return
    void whatsappPhoneWatch
    void phoneIdWatch
    void wabaWatch
    const id = window.setTimeout(() => { void maybeResolve() }, 650)
    return () => window.clearTimeout(id)
  }, [open, whatsappPhoneWatch, phoneIdWatch, wabaWatch])

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      const payload = {
        perfil: String(values.perfil || '').trim() || undefined,
        base_url: String(values.base_url || '').trim() || undefined,
        api_version: String(values.api_version || '').trim() || undefined,
        whatsapp_phone: String(values.whatsapp_phone || '').trim() || undefined,
        phone_number_id: String(values.phone_number_id || '').trim() || undefined,
        business_account_id: String(values.business_account_id || '').trim() || undefined,
        app_id: String(values.app_id || '').trim() || undefined,
        configuration_id: String(values.configuration_id || '').trim() || undefined,
        partner_solution_id: String(values.partner_solution_id || '').trim() || undefined,
        redirect_uri: String(values.redirect_uri || '').trim() || undefined,
        access_token: String(values.access_token || '').trim() || undefined,
        webhook_verify_token: String(values.webhook_verify_token || '').trim() || undefined,
        app_secret: String(values.app_secret || '').trim() || undefined,
        validate_signature: values.validate_signature === true,
        enabled: values.enabled !== false,
      }
      const cfgId = Number(initial?.id || 0)
      await api.saveMetaWhatsAppConfig(payload, cfgId || undefined)
      message.success('Conexão Meta salva')
      onSaved()
      onCancel()
    } catch (e: any) {
      if (e?.errorFields) return
      message.error(e?.response?.data?.detail || 'Erro ao salvar conexão Meta')
    } finally {
      setSaving(false)
    }
  }

  const titleNode = (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div className="navbar-logo" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <img src={Logo} alt="CAPTAR" style={{ height: 70, backgroundColor: '#ffffff', borderRadius: 8, padding: 6 }} />
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
        <Avatar size={40} />
      </div>
    </div>
  )

  return (
    <Modal
      open={open}
      title={titleNode}
      onCancel={onCancel}
      footer={null}
      destroyOnHidden
      width={980}
      styles={{ header: { paddingTop: 8, paddingBottom: 8 } }}
      closable={false}
      maskClosable={false}
      className="meta-cloudapi-modal"
    >
      <style>{`.meta-cloudapi-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .meta-cloudapi-modal .ant-modal-content{ border-radius: 0 !important; } .meta-cloudapi-modal .ant-form-item{ margin-bottom:6px; }`}</style>

      <Form form={form} layout="vertical">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <Form.Item name="perfil" label="Perfil" rules={[{ required: true, message: 'Informe o Perfil' }]}>
              <Input placeholder="Ex: EMPRESA X" onChange={(e) => form.setFieldValue('perfil', String(e.target.value || '').toUpperCase())} />
            </Form.Item>
            <Form.Item name="base_url" label="Base URL (Graph)">
              <Input placeholder="https://graph.facebook.com" />
            </Form.Item>
            <Form.Item name="api_version" label="API Version">
              <Input placeholder="v21.0" />
            </Form.Item>
            <Form.Item name="whatsapp_phone" label="WhatsApp Phone" rules={[{ required: true, message: 'Informe o WhatsApp Phone' }]}>
              <Input
                placeholder="+5511999999999"
                onChange={(e) => {
                  lastEditedRef.current = 'whatsapp_phone'
                  form.setFieldValue('whatsapp_phone', e.target.value)
                }}
              />
            </Form.Item>
            <Form.Item name="phone_number_id" label="PhoneID" rules={[{ required: true, message: 'Informe o PhoneID' }]}>
              <Input
                placeholder="Ex: 123456789012345"
                onChange={(e) => {
                  lastEditedRef.current = 'phone_number_id'
                  form.setFieldValue('phone_number_id', e.target.value)
                }}
              />
            </Form.Item>
            <Form.Item name="business_account_id" label="WABA ID" rules={[{ required: true, message: 'Informe o WABA ID' }]}>
              <Input placeholder="Ex: 123456789012345" />
            </Form.Item>
            <Form.Item name="enabled" label="Status" valuePropName="checked">
              <Switch checkedChildren="Ativo" unCheckedChildren="Inativo" />
            </Form.Item>
            <Form.Item name="validate_signature" label="Validar assinatura do webhook" valuePropName="checked">
              <Switch checkedChildren="Sim" unCheckedChildren="Não" />
            </Form.Item>
          </div>

          <div>
            <Form.Item name="app_id" label="App ID (opcional)">
              <Input placeholder="Ex: 123456789012345" />
            </Form.Item>
            <Form.Item name="configuration_id" label="Configuration ID (opcional)">
              <Input placeholder="Ex: 123456789012345" />
            </Form.Item>
            <Form.Item name="partner_solution_id" label="Partner Solution ID (opcional)">
              <Input placeholder="Ex: 123456789012345" />
            </Form.Item>
            <Form.Item name="redirect_uri" label="Redirect URI (opcional)">
              <Input placeholder="https://seu-dominio.com/..." />
            </Form.Item>

            <Form.Item label="Access Token (mascarado)">
              <Input value={String(initial?.access_token_masked || (initial?.has_access_token ? '********' : '') || '')} readOnly />
            </Form.Item>
            <Form.Item name="access_token" label="Novo Access Token (opcional)">
              <Input.Password placeholder={initial?.has_access_token ? 'deixe em branco para manter o atual' : 'cole o token'} />
            </Form.Item>

            <Form.Item label="Webhook Verify Token (mascarado)">
              <Input value={String(initial?.webhook_verify_token_masked || (initial?.has_webhook_verify_token ? '********' : '') || '')} readOnly />
            </Form.Item>
            <Form.Item name="webhook_verify_token" label="Novo Webhook Verify Token (opcional)">
              <Input.Password placeholder={initial?.has_webhook_verify_token ? 'deixe em branco para manter o atual' : 'cole o verify token'} />
            </Form.Item>

            <Form.Item label="App Secret (mascarado)">
              <Input value={String(initial?.app_secret_masked || (initial?.has_app_secret ? '********' : '') || '')} readOnly />
            </Form.Item>
            <Form.Item name="app_secret" label="Novo App Secret (opcional)">
              <Input.Password placeholder={initial?.has_app_secret ? 'deixe em branco para manter o atual' : 'cole o app secret'} />
            </Form.Item>
          </div>
        </div>

        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />} disabled={saving}>CANCELAR</Button>
          <Button type="primary" onClick={handleSave} icon={<SaveOutlined />} loading={saving} disabled={resolving}>SALVAR</Button>
        </Space>
        <div style={{ marginTop: 8, textAlign: 'right', fontSize: 12, color: '#666' }}>
          {resolving ? 'Sincronizando WhatsApp Phone ↔ PhoneID...' : ''}
        </div>
      </Form>
    </Modal>
  )
}
