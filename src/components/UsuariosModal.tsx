import { Modal, Form, Input, Checkbox, Button, Space, InputNumber, DatePicker, Select, Card, Avatar, Switch, App } from 'antd'
import { UserOutlined, IdcardOutlined, CrownOutlined, TagOutlined, PhoneOutlined, MailOutlined, UserSwitchOutlined, LockOutlined, SaveOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useEffect, useMemo, useRef, useState } from 'react'
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

export default function UsuariosModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const [schema, setSchema] = useState<{ name: string; type: string; nullable: boolean; maxLength?: number }[]>([])
  const [schemaBaseNames, setSchemaBaseNames] = useState<string[]>([])
  const [perfilOptions, setPerfilOptions] = useState<{ value: string; label: string }[]>([])
  const [funcaoOptions, setFuncaoOptions] = useState<{ value: string; label: string }[]>([])
  const [perfilMap, setPerfilMap] = useState<Record<string, number>>({})
  const [funcaoMap, setFuncaoMap] = useState<Record<string, number>>({})
  const [coordenadores, setCoordenadores] = useState<{ value: string; label: string }[]>([])
  const [supervisores, setSupervisores] = useState<{ value: string; label: string }[]>([])
  const [coordTenantMap, setCoordTenantMap] = useState<Record<string, string>>({})
  const [superTenantMap, setSuperTenantMap] = useState<Record<string, string>>({})
  const [tenantOptions, setTenantOptions] = useState<{ value: string; label: string; slug?: string }[]>([])
  const api = useApi()
  
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [webcamStream, setWebcamStream] = useState<MediaStream | null>(null)
  const [imagemPreview, setImagemPreview] = useState<string | undefined>(undefined)
  const { user } = useAuthStore()
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

  const fileToDataUrl = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = (e) => reject(e)
      reader.readAsDataURL(file)
    })
  }

  const convertDataUrlToJpeg = (dataUrl: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = img.width || 640
        canvas.height = img.height || 480
        const ctx = canvas.getContext('2d')
        if (!ctx) { resolve(dataUrl); return }
        ctx.drawImage(img, 0, 0)
        try {
          const out = canvas.toDataURL('image/jpeg', 0.92)
          resolve(out)
        } catch (e) {
          resolve(dataUrl)
        }
      }
      img.onerror = (e) => reject(e)
      img.src = dataUrl
    })
  }

  const getUpperFromEvent = (e: any) => {
    const v = e?.target?.value
    return typeof v === 'string' ? v.toUpperCase() : v
  }

  const getLowerFromEvent = (e: any) => {
    const v = e?.target?.value
    return typeof v === 'string' ? v.toLowerCase() : v
  }

  useEffect(() => {
    const loadSchema = async () => {
      try {
        const s = await api.getUsuariosSchema()
        const base = s.columns || []
        const names = new Set(base.map((c: any) => c.name))
        const extras = ['Coordenador','Supervisor','Ativista']
          .filter(n => !names.has(n))
          .map(n => ({ name: n, type: 'varchar', nullable: true }))
        setSchema([...base, ...extras])
        setSchemaBaseNames(base.map((c: any) => c.name))
      } catch {}
    }
    const loadPerfis = async () => {
      try {
        const res = await api.listPerfil()
        const rows = res.rows || []
        const opts = rows.map((r: any) => ({ label: r.Perfil ?? r.perfil, value: String(r.Perfil ?? r.perfil) }))
        const idx: Record<string, number> = {}
        for (const r of rows) {
          const label = r.Perfil ?? r.perfil
          const id = r.IdPerfil ?? r.id ?? r.Id ?? r.ID
          if (label !== undefined && id !== undefined) idx[String(label)] = Number(id)
        }
        setPerfilOptions(opts)
        setPerfilMap(idx)
      } catch {}
    }
    const loadFuncoes = async () => {
      try {
        const res = await api.listFuncoes()
        const rows = res.rows || []
        const opts = rows.map((r: any) => ({ label: r.Funcao ?? r.Descricao ?? '', value: String(r.Funcao ?? r.Descricao ?? '') }))
        const idx: Record<string, number> = {}
        for (const r of rows) {
          const label = r.Funcao ?? r.Descricao ?? ''
          const id = r.IdFuncao ?? r.id ?? r.Id ?? r.ID
          if (label !== undefined && id !== undefined) idx[String(label)] = Number(id)
        }
        setFuncaoOptions(opts)
        setFuncaoMap(idx)
      } catch {}
    }
    const loadCoordenadores = async () => {
      try {
        const res = await api.listCoordenadores()
        const rows = res.rows || []
        setCoordenadores(rows.map((r: any) => ({ label: r.Nome ?? r.nome, value: String(r.Nome ?? r.nome) })))
        const map: Record<string, string> = {}
        for (const r of rows) {
          const label = r.Nome ?? r.nome
          const nameTenant = String(r.TenantLayer ?? r.NomeTenant ?? r.nomeTenant ?? 'CAPTAR')
          if (label !== undefined) map[String(label)] = nameTenant
        }
        setCoordTenantMap(map)
      } catch {}
    }
    const loadTenants = async () => {
      try {
        const res = await api.listTenants()
        const rows = res.rows || []
        const opts = rows.map((t: any) => ({ label: t.Nome ?? t.nome, value: String(t.Nome ?? t.nome), slug: t.Slug ?? t.slug }))
        setTenantOptions(opts)
        const slug = localStorage.getItem('tenantSlug') || 'captar'
        const def = opts.find(o => (o.slug || '').toLowerCase() === slug.toLowerCase())
        if (def && !initial) form.setFieldValue('TenantLayer', def.value)
      } catch {}
    }
    if (open) {
      loadSchema()
      loadPerfis()
      loadFuncoes()
      loadCoordenadores()
      loadTenants()
      if (initial) form.setFieldsValue(initial)
      else form.resetFields()
      try {
        const durl = (form as any).getFieldValue('ImagemUploadDataUrl') as string | undefined
        setImagemPreview(durl || (initial?.Imagem as string | undefined))
      } catch {}
    }
  }, [open, initial])

  const funcaoWatch = Form.useWatch('Funcao', form)
  const coordWatch = Form.useWatch('Coordenador', form)
  const tenantWatch = Form.useWatch('TenantLayer', form)
  useEffect(() => {
    const f = String(funcaoWatch || '').toUpperCase().trim()
    if (f === 'ADMINISTRADOR' || f === 'COORDENADOR') {
      form.setFieldValue('Coordenador', form.getFieldValue('Nome'))
      form.setFieldValue('Supervisor', 'NAO SE APLICA')
      form.setFieldValue('Ativista', 'NAO SE APLICA')
    } else if (f === 'SUPERVISOR') {
      form.setFieldValue('Supervisor', form.getFieldValue('Nome'))
      form.setFieldValue('Ativista', 'NAO SE APLICA')
    }
  }, [funcaoWatch])

  useEffect(() => {
    const f = String(funcaoWatch || '').toUpperCase().trim()
    if ((f === 'SUPERVISOR' || f === 'ATIVISTA') && coordWatch) {
      ;(async () => {
        try {
          const res = await api.listSupervisores(String(coordWatch))
        const rows = res.rows || []
        setSupervisores(rows.map((r: any) => ({ label: r.Nome ?? r.nome, value: String(r.Nome ?? r.nome) })))
        const map: Record<string, string> = {}
        for (const r of rows) {
          const label = r.Nome ?? r.nome
          const nameTenant = String(r.TenantLayer ?? r.NomeTenant ?? r.nomeTenant ?? 'CAPTAR')
          if (label !== undefined) map[String(label)] = nameTenant
        }
        setSuperTenantMap(map)
        } catch {}
      })()
    } else {
      setSupervisores([])
    }
  }, [coordWatch, funcaoWatch])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if (values.Perfil && !values.IdPerfil) {
        const idp = perfilMap[String(values.Perfil)]
        if (idp !== undefined) values.IdPerfil = idp
      }
      if (values.Funcao) {
        const label = String(values.Funcao)
        const idf = funcaoMap[label]
        if (idf !== undefined) values.IdFuncao = idf
        values.Funcao = label
      }
      if (values.IdPerfil) delete (values as any).Perfil
      if (values.IdFuncao) delete (values as any).Funcao
      const fname = String(values.Nome || '').trim()
      const ffunc = String(values.Funcao || '').toUpperCase().trim()
      if (ffunc === 'ADMINISTRADOR' || ffunc === 'COORDENADOR') {
        values.Coordenador = fname
        values.Supervisor = 'NAO SE APLICA'
        values.Ativista = 'NAO SE APLICA'
      } else if (ffunc === 'SUPERVISOR') {
        if (!String(values.Coordenador || '').trim()) throw new Error('Coordenador é obrigatório')
        values.Supervisor = fname
        values.Ativista = 'NAO SE APLICA'
      } else if (ffunc === 'ATIVISTA') {
        if (!String(values.Coordenador || '').trim()) throw new Error('Coordenador é obrigatório')
        if (!String(values.Supervisor || '').trim()) throw new Error('Supervisor é obrigatório')
        values.Ativista = fname
      }
      if (typeof values.Celular === 'string') {
        const c = String(values.Celular)
        values.Celular = c.length > 15 ? c.slice(0, 15) : c
      }
      const trySave = async (): Promise<number> => {
        const allowed = new Set([...schemaBaseNames, 'IdPerfil', 'IdFuncao'])
        allowed.delete('IdTenant')
        const payload: any = {}
        for (const k of Object.keys(values)) {
          if (allowed.has(k)) payload[k] = (values as any)[k]
        }
        if (payload.IdPerfil) delete payload.Perfil
        if (payload.IdFuncao) delete payload.Funcao
        if (initial?.IdUsuario) {
          const r = await api.updateUsuario(initial.IdUsuario, payload)
          message.success('Usuário atualizado')
          return r.id
        } else {
          const r = await api.createUsuario(payload)
          message.success('Usuário criado')
          return r.id
        }
      }
      const currentTenantName = String(localStorage.getItem('tenantName') || 'CAPTAR')
      const myTenantName = String(values.TenantLayer || currentTenantName)
      if (String(currentTenantName).toUpperCase() === 'CAPTAR') {
        const coord = String(values.Coordenador || '').trim()
        const sup = String(values.Supervisor || '').trim()
        if (coord) {
          const ct = String(coordTenantMap[coord] || myTenantName)
          if (ct && myTenantName && ct.toUpperCase() !== myTenantName.toUpperCase()) { message.error('Não é possível vincular: Tenants diferentes'); return }
        }
        if (sup) {
          const st = String(superTenantMap[sup] || myTenantName)
          if (st && myTenantName && st.toUpperCase() !== myTenantName.toUpperCase()) { message.error('Não é possível vincular: Tenants diferentes'); return }
        }
      }
      try {
        const resTen = await api.listTenants()
        const rowsTen = resTen.rows || []
        const selectedName = String(values.TenantLayer || myTenantName)
        const t = rowsTen.find((r: any) => String(r.Nome ?? r.nome).toUpperCase() === selectedName.toUpperCase())
          || rowsTen.find((r: any) => String(r.Slug ?? r.slug).toUpperCase() === String(localStorage.getItem('tenantSlug') || 'captar').toUpperCase())
        if (t) { delete (values as any).IdTenant }
      } catch {}
      try {
        const savedId = await trySave()
        if ((form as any).getFieldValue('ImagemUploadFile') || (form as any).getFieldValue('ImagemUploadDataUrl')) {
          const f = (form as any).getFieldValue('ImagemUploadFile') as File | undefined
          const d = (form as any).getFieldValue('ImagemUploadDataUrl') as string | undefined
          try {
            await api.uploadUsuarioFoto(savedId, { file: f, data_url: d })
            if (d) setImagemPreview(d)
          } catch {
            try {
              const isWebp = (f && f.type === 'image/webp') || (d && String(d).startsWith('data:image/webp'))
              if (isWebp) {
                const src = d || (f ? await fileToDataUrl(f) : undefined)
                if (src) {
                  const jpeg = await convertDataUrlToJpeg(src)
                  await api.uploadUsuarioFoto(savedId, { data_url: jpeg })
                  setImagemPreview(jpeg)
                }
              }
            } catch {}
          }
        }
      } catch (e: any) {
        const msg = e?.response?.data?.detail || ''
        if (values.Celular && typeof values.Celular === 'string' && msg.includes('character varying(15)')) {
          values.Celular = values.Celular.replace(' ', '')
          await trySave()
          message.warning('Celular ajustado para caber no limite atual do banco')
        } else {
          const err = e?.response?.data?.detail || e?.message || 'Falha ao salvar usuário'
          message.error(err)
          throw e
        }
      }
      onSaved()
    } catch {}
  }

  const renderField = (col: { name: string; type: string; nullable: boolean; maxLength?: number }) => {
    const auto = new Set(['DataCadastro','Cadastrante','DataUpdate','TipoUpdate','CadastranteUpdate','UltimoAcesso','TokenRecuperacao','TokenExpiracao','Candidato','UsuarioUpdate','IdTenant'])
    if (col.name === 'IdUsuario') return null
    if (col.name === 'IdPerfil') return null
    if (col.name === 'IdTenant') return null
    if (auto.has(col.name)) return null
    const required = !col.nullable
    const type = col.type.toLowerCase()
    if (col.name === 'Perfil') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <Select options={perfilOptions} optionFilterProp="label" showSearch style={{ borderRadius: 8 }} suffixIcon={<TagOutlined />} />
        </Form.Item>
      )
    }
    if (col.name === 'TenantLayer') {
      const isEditing = !!initial?.IdUsuario
      const disabled = !isEditing
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required: true }]}> 
          <Select
            options={tenantOptions}
            optionFilterProp="label"
            showSearch
            style={{ borderRadius: 8 }}
            disabled={disabled}
          />
        </Form.Item>
      )
    }
    if (col.name === 'Funcao') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <Select
            options={funcaoOptions}
            optionFilterProp="label"
            showSearch
            style={{ borderRadius: 8 }}
            suffixIcon={<CrownOutlined />}
          />
        </Form.Item>
      )
    }
    if (col.name === 'Coordenador') {
      const f = String(funcaoWatch || '').toUpperCase().trim()
      const disabled = f === 'ADMINISTRADOR' || f === 'COORDENADOR'
      const tn = String(tenantWatch || '').trim()
      const opts = tn && tn.toUpperCase() !== 'CAPTAR'
        ? coordenadores.filter(o => String(coordTenantMap[o.value] || '').toUpperCase() === tn.toUpperCase())
        : coordenadores
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required: f !== 'ADMINISTRADOR' && f !== 'COORDENADOR' }]}> 
          <Select options={opts} optionFilterProp="label" showSearch style={{ borderRadius: 8 }} disabled={disabled} />
        </Form.Item>
      )
    }
    if (col.name === 'Supervisor') {
      const f = String(funcaoWatch || '').toUpperCase().trim()
      const disabled = f === 'ADMINISTRADOR' || f === 'COORDENADOR'
      const require = f === 'ATIVISTA'
      const tn = String(tenantWatch || '').trim()
      const opts = tn && tn.toUpperCase() !== 'CAPTAR'
        ? supervisores.filter(o => String(superTenantMap[o.value] || '').toUpperCase() === tn.toUpperCase())
        : supervisores
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required: require }]}> 
          <Select options={opts} optionFilterProp="label" showSearch style={{ borderRadius: 8 }} disabled={disabled} />
        </Form.Item>
      )
    }
    if (col.name === 'Ativista') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name}> 
          <Input style={{ borderRadius: 8 }} disabled />
        </Form.Item>
      )
    }
    if (col.name === 'Senha') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <Input.Password style={{ borderRadius: 8 }} prefix={<LockOutlined />} />
        </Form.Item>
      )
    }
    if (type.includes('boolean')) {
      return (
        <Form.Item key={col.name} name={col.name} valuePropName="checked" label={col.name}>
          <Checkbox />
        </Form.Item>
      )
    }
    if (type.includes('date')) {
      const showTime = type.includes('timestamp')
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <DatePicker style={{ width: '100%', borderRadius: 8 }} showTime={showTime} />
        </Form.Item>
      )
    }
    if (type.includes('int') || type.includes('numeric')) {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <InputNumber style={{ width: '100%', borderRadius: 8 }} />
        </Form.Item>
      )
    }
    if (col.name === 'Celular') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <Input style={{ borderRadius: 8 }} prefix={<PhoneOutlined />} maxLength={15} onChange={(e) => {
            const masked = formatCelular(e.target.value)
            form.setFieldsValue({ [col.name]: masked })
          }} />
        </Form.Item>
      )
    }
    if (col.name === 'Nome') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]} getValueFromEvent={getUpperFromEvent}> 
          <Input style={{ borderRadius: 8 }} prefix={<UserOutlined />} maxLength={typeof col.maxLength === 'number' ? col.maxLength : undefined} />
        </Form.Item>
      )
    }
    if (col.name === 'CPF') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}> 
          <Input style={{ borderRadius: 8 }} prefix={<IdcardOutlined />} maxLength={typeof col.maxLength === 'number' ? col.maxLength : 14} onChange={(e) => {
            const masked = formatCpf(e.target.value)
            form.setFieldsValue({ [col.name]: masked })
          }} />
        </Form.Item>
      )
    }
    if (col.name === 'Email') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]} getValueFromEvent={getLowerFromEvent}> 
          <Input style={{ borderRadius: 8 }} prefix={<MailOutlined />} maxLength={typeof col.maxLength === 'number' ? col.maxLength : undefined} />
        </Form.Item>
      )
    }
    if (col.name === 'Usuario') {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]} getValueFromEvent={getUpperFromEvent}> 
          <Input style={{ borderRadius: 8 }} prefix={<UserSwitchOutlined />} maxLength={typeof col.maxLength === 'number' ? col.maxLength : undefined} />
        </Form.Item>
      )
    }
    if (col.name === 'Imagem') return null
    return (
      <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]} getValueFromEvent={getUpperFromEvent}> 
        <Input style={{ borderRadius: 8 }} maxLength={typeof col.maxLength === 'number' ? col.maxLength : undefined} />
      </Form.Item>
    )
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
      width={980}
      closable={false}
      maskClosable={false}
      className="usuarios-modal"
    >
      <style>{`.usuarios-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .usuarios-modal .ant-modal-content{ border-radius: 0 !important; } .usuarios-modal .ant-form-item{ margin-bottom:6px; }`}</style>
      <Form form={form} layout="vertical">
        <div style={{ display: 'grid', gap: 16 }}>
          {(() => {
            const byName: Record<string, { name: string; type: string; nullable: boolean; maxLength?: number }> = {}
            for (const c of schema) byName[c.name] = c as any
            
            const groupAccess = ['Funcao','Perfil','Usuario','Senha','Coordenador','Supervisor','Ativista'].filter(n => byName[n])
            
            return (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
                  <Card title="Identificação" size="small">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px', gap: 6, alignItems: 'end' }}>
                      {byName['CPF'] && (
                        <div style={{ width: '50%' }}>{renderField(byName['CPF'])}</div>
                      )}
                      {byName['Ativo'] && (
                        <Form.Item name="Ativo" label="Ativo" valuePropName="checked" style={{ marginBottom: 0 }}>
                          <Switch />
                        </Form.Item>
                      )}
                      {byName['Nome'] && (
                        <div style={{ gridColumn: '1 / span 2' }}>{renderField(byName['Nome'])}</div>
                      )}
                      {byName['Celular'] && (
                        <div style={{ width: '50%' }}>{renderField(byName['Celular'])}</div>
                      )}
                      {byName['Email'] && (
                        <div style={{ gridColumn: '1 / span 2' }}>{renderField(byName['Email'])}</div>
                      )}
                    </div>
                  </Card>
                  <Card title="Foto" size="small">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <Button onClick={async () => {
                          try {
                            const s = await navigator.mediaDevices.getUserMedia({ video: true })
                            setWebcamStream(s)
                            if (videoRef.current) {
                              videoRef.current.srcObject = s
                              await videoRef.current.play()
                            }
                          } catch {}
                        }}>Usar Webcam</Button>
                        <Button onClick={() => {
                          const v = videoRef.current
                          if (v) {
                            const canvas = document.createElement('canvas')
                            canvas.width = v.videoWidth || 640
                            canvas.height = v.videoHeight || 480
                            const ctx = canvas.getContext('2d')
                            if (ctx) {
                              ctx.drawImage(v, 0, 0, canvas.width, canvas.height)
                              const d = canvas.toDataURL('image/jpeg', 0.92)
                              ;(form as any).setFieldsValue({ ImagemUploadDataUrl: d })
                              setImagemPreview(d)
                            }
                          }
                        }}>Capturar</Button>
                        <Button onClick={() => {
                          if (webcamStream) webcamStream.getTracks().forEach(t => t.stop())
                          setWebcamStream(null)
                        }}>Encerrar</Button>
                      </div>
                      <div>
                        <input type="file" accept="image/*,.webp" onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) {
                            ;(form as any).setFieldsValue({ ImagemUploadFile: file })
                            const reader = new FileReader()
                            reader.onload = () => {
                              const d = reader.result as string
                              ;(form as any).setFieldsValue({ ImagemUploadDataUrl: d })
                              setImagemPreview(d)
                            }
                            reader.readAsDataURL(file)
                          }
                        }} />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'center' }}>
                        {webcamStream ? (
                          <video ref={videoRef} style={{ width: '100%', maxWidth: 360, borderRadius: 8 }} />
                        ) : (
                          imagemPreview ? <img src={imagemPreview} alt="Preview" style={{ width: '100%', maxWidth: 360, borderRadius: 8, background: '#f5f5f5' }} /> : <div style={{ width: 360, height: 240, background: '#fafafa', border: '1px dashed #ddd', borderRadius: 8 }} />
                        )}
                      </div>
                    </div>
                  </Card>
                </div>
                <Card title="Acesso" size="small">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                    {groupAccess.map(n => renderField(byName[n]))}
                  </div>
                </Card>
                
              </>
            )
          })()}
        </div>
        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
          <Button type="primary" onClick={handleOk} icon={<SaveOutlined />}>SALVAR</Button>
        </Space>
      </Form>
    </Modal>
  )
}
  const { message } = App.useApp()
