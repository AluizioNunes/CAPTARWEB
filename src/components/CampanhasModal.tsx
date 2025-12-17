import { Modal, Form, Input, Button, Space, DatePicker, Upload, Radio, message, Card, Avatar, Row, Col, Statistic, Tooltip } from 'antd'
import { UploadOutlined, FileTextOutlined, TeamOutlined, CloudUploadOutlined, ThunderboltOutlined, CloseCircleOutlined, SaveOutlined, SendOutlined, CheckCircleOutlined, SyncOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useEffect, useState, useMemo } from 'react'
import { useApi } from '../context/ApiContext'
import { useAuthStore } from '../store/authStore'
import { format, parseISO, isValid, isWithinInterval } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

interface Props {
  open: boolean
  initial?: any
  onCancel: () => void
  onSaved: () => void
}

export default function CampanhasModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const [destino, setDestino] = useState<'eleitores' | 'arquivo'>('eleitores')
  const [fileList, setFileList] = useState<any[]>([])
  const [imagemList, setImagemList] = useState<any[]>([])
  const [imagemPreview, setImagemPreview] = useState<string | undefined>(undefined)
  const api = useApi()
  const { user } = useAuthStore()

  // Stats State
  const [meta, setMeta] = useState(0)
  const [enviados, setEnviados] = useState(0)
  const [naoEnviados, setNaoEnviados] = useState(0)
  const [positivos, setPositivos] = useState(0)
  const [negativos, setNegativos] = useState(0)
  const [aguardando, setAguardando] = useState(0)

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
    if (open) {
      if (initial) {
        form.setFieldsValue({
          ...initial,
          data_inicio: initial.data_inicio ? parseISO(initial.data_inicio) : undefined,
          data_fim: initial.data_fim ? parseISO(initial.data_fim) : undefined,
        })
        if (initial.AnexoJSON || initial.Anexo) {
            setDestino('arquivo')
        } else {
            setDestino('eleitores')
        }
        
        // Load stats
        setMeta(initial.meta || 0)
        setEnviados(initial.enviados || 0)
        setNaoEnviados(initial.nao_enviados || 0)
        setPositivos(initial.positivos || 0)
        setNegativos(initial.negativos || 0)
        // Aguardando calculation: Enviados - (Pos + Neg) or use DB value if provided
        const calcAguardando = (initial.enviados || 0) - ((initial.positivos || 0) + (initial.negativos || 0))
        setAguardando(initial.aguardando !== undefined ? initial.aguardando : (calcAguardando > 0 ? calcAguardando : 0))

      } else {
        form.resetFields()
        setDestino('eleitores')
        setFileList([])
        setImagemList([])
        setImagemPreview(undefined)
        
        // Reset stats
        setMeta(0)
        setEnviados(0)
        setNaoEnviados(0)
        setPositivos(0)
        setNegativos(0)
        setAguardando(0)
      }
    }
  }, [open, initial])

  // Calculate Meta dynamically based on selection
  useEffect(() => {
    const calculateMeta = async () => {
        if (destino === 'eleitores') {
            try {
                // Fetch total eleitores from dashboard stats or dedicated endpoint
                const stats = await api.getDashboardStats()
                setMeta(stats.totalEleitores || 0)
            } catch (e) {
                console.error('Erro ao buscar total de eleitores', e)
            }
        } else if (destino === 'arquivo' && fileList.length > 0) {
            const file = fileList[0].originFileObj
            if (file) {
                if (file.name.endsWith('.json')) {
                    try {
                        const text = await file.text()
                        const json = JSON.parse(text)
                        if (Array.isArray(json)) {
                            setMeta(json.length)
                            // Validação da chave whatsapp
                            if (json.length > 0) {
                                const keys = Object.keys(json[0]).map(k => k.toLowerCase())
                                if (!keys.includes('whatsapp')) {
                                    message.warning('Atenção: O arquivo JSON não contém a chave "whatsapp".')
                                }
                            }
                        }
                    } catch {}
                } else if (file.name.endsWith('.csv')) {
                    try {
                        const text = await file.text()
                        const lines = text.split('\n').filter((l: string) => l.trim().length > 0)
                        if (lines.length > 0) {
                            // Validação da coluna whatsapp
                            const header = lines[0].toLowerCase()
                            if (!header.includes('whatsapp')) {
                                message.warning('Atenção: O arquivo CSV não contém a coluna "whatsapp".')
                            }
                            setMeta(Math.max(0, lines.length - 1)) // Assume header
                        } else {
                            setMeta(0)
                        }
                    } catch {}
                } else {
                    // XLS/PDF - difficult to count client-side without heavy libs
                    // Keep current meta or set to 0? User asked to show it.
                    // We'll leave it as is or 0 if new file
                }
            }
        }
    }
    calculateMeta()
  }, [destino, fileList, api])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      
      const payload: any = {
        ...values,
        data_inicio: values.data_inicio ? format(values.data_inicio, 'yyyy-MM-dd') : null,
        data_fim: values.data_fim ? format(values.data_fim, 'yyyy-MM-dd') : null,
        meta, // Save calculated meta
        enviados,
        nao_enviados: naoEnviados,
        positivos,
        negativos,
        aguardando
      }

      if (destino === 'arquivo' && fileList.length > 0) {
        const file = fileList[0].originFileObj
        if (file) {
            if (file.name.endsWith('.json')) {
                const text = await file.text()
                try {
                    JSON.parse(text) // Validate JSON
                    payload.AnexoJSON = text
                } catch (e) {
                    message.error('Arquivo JSON inválido')
                    return
                }
            } else {
                payload.AnexoFile = file
            }
        }
      } else if (destino === 'eleitores') {
          payload.UsarEleitores = true
      }

      let savedId: number
      if (initial?.id) {
        await api.updateCampanha(initial.id, payload)
        savedId = initial.id
        message.success('Campanha atualizada')
      } else {
        const res = await api.createCampanha(payload)
        savedId = res.id
        message.success('Campanha criada')
      }

      // Upload Image if present
      if (imagemList.length > 0) {
          const file = imagemList[0].originFileObj
          if (file) {
              await api.uploadCampanhaAnexo(savedId, { file, type: 'imagem' })
          }
      }
      
      // Upload Anexo File if present
      if (destino === 'arquivo' && payload.AnexoFile) {
           await api.uploadCampanhaAnexo(savedId, { file: payload.AnexoFile, type: 'anexo' })
      }

      onSaved()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao salvar campanha')
    }
  }

  const handleEnviarCampanha = async () => {
      // PLACEHOLDER FOR AUTOMATION TRIGGER
      // Replace these values with your actual N8N/EvolutionAPI endpoint and keys
      const AUTOMATION_URL = 'https://n8n.seu-dominio.com/webhook/disparar-campanha'
      const API_KEY = 'sua-api-key'
      
      const campanhaData = {
          id: initial.id,
          nome: form.getFieldValue('nome'),
          mensagem: form.getFieldValue('descricao'),
          origem: destino,
          meta: meta
      }

      message.loading({ content: 'Iniciando automação...', key: 'envio' })
      
      try {
          // Simulation of request
          // await fetch(AUTOMATION_URL, {
          //     method: 'POST',
          //     headers: { 'Content-Type': 'application/json', 'Authorization': API_KEY },
          //     body: JSON.stringify(campanhaData)
          // })
          
          await new Promise(resolve => setTimeout(resolve, 1500)) // Fake delay
          
          message.success({ content: 'Automação iniciada com sucesso!', key: 'envio' })
          
          // Optionally update status to 'EM_ANDAMENTO' locally
          // await api.updateCampanha(initial.id, { status: 'EM_ANDAMENTO' })
          // onSaved()
      } catch (e) {
          message.error({ content: 'Erro ao iniciar automação', key: 'envio' })
      }
  }

  const getUpperFromEvent = (e: any) => {
    const v = e?.target?.value
    return typeof v === 'string' ? v.toUpperCase() : v
  }

  // Check if campaign can be sent
  const canSend = useMemo(() => {
      if (!initial?.id) return false // Must be saved first
      const start = form.getFieldValue('data_inicio')
      const end = form.getFieldValue('data_fim')
      if (!start) return false
      
      const now = new Date()
      // Check if within range
      // Note: date-fns/isWithinInterval requires start <= end
      try {
          const sDate = start.toDate ? start.toDate() : new Date(start)
          const eDate = end ? (end.toDate ? end.toDate() : new Date(end)) : new Date(2100, 0, 1)
          
          // Simple check
          return now >= sDate && now <= eDate
      } catch {
          return false
      }
  }, [initial, form.getFieldValue('data_inicio'), form.getFieldValue('data_fim')])

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
      className="campanhas-modal"
    >
      <style>{`.campanhas-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .campanhas-modal .ant-modal-content{ border-radius: 0 !important; } .campanhas-modal .ant-form-item{ margin-bottom:6px; }`}</style>
      
      {/* STATISTICS CARDS */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
            <Card size="small" style={{ textAlign: 'center', background: '#f0f5ff', borderColor: '#adc6ff' }}>
                <Statistic title="META" value={meta} valueStyle={{ color: '#2f54eb' }} prefix={<TeamOutlined />} />
            </Card>
        </Col>
        <Col span={4}>
            <Card size="small" style={{ textAlign: 'center', background: '#f6ffed', borderColor: '#b7eb8f' }}>
                <Statistic title="ENVIADOS" value={enviados} valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} />
            </Card>
        </Col>
        <Col span={4}>
            <Card size="small" style={{ textAlign: 'center', background: '#fff1f0', borderColor: '#ffa39e' }}>
                <Statistic title="NÃO ENVIADOS" value={naoEnviados} valueStyle={{ color: '#cf1322' }} prefix={<ExclamationCircleOutlined />} />
            </Card>
        </Col>
        <Col span={4}>
            <Card size="small" style={{ textAlign: 'center', background: '#e6f7ff', borderColor: '#91d5ff' }}>
                <Statistic title="POSITIVOS" value={positivos} valueStyle={{ color: '#096dd9' }} />
            </Card>
        </Col>
        <Col span={4}>
            <Card size="small" style={{ textAlign: 'center', background: '#fffbe6', borderColor: '#ffe58f' }}>
                <Statistic title="NEGATIVOS" value={negativos} valueStyle={{ color: '#d48806' }} />
            </Card>
        </Col>
        <Col span={4}>
            <Card size="small" style={{ textAlign: 'center', background: '#f9f0ff', borderColor: '#d3adf7' }}>
                <Statistic title="AGUARDANDO" value={aguardando} valueStyle={{ color: '#722ed1' }} prefix={<SyncOutlined spin={aguardando > 0} />} />
            </Card>
        </Col>
      </Row>

      <Form form={form} layout="vertical">
        <Card title="DADOS DA CAMPANHA" size="small">
          <Form.Item name="nome" label="NOME DA CAMPANHA" rules={[{ required: true, message: 'Informe o nome' }]} getValueFromEvent={getUpperFromEvent}>
            <Input prefix={<ThunderboltOutlined />} placeholder="Ex: CAMPANHA DE DOAÇÃO" />
          </Form.Item>

          <Form.Item name="descricao" label="DESCRIÇÃO / MENSAGEM">
            <Input.TextArea rows={4} placeholder="Texto da mensagem que será enviada" />
          </Form.Item>

          <Space style={{ display: 'flex', marginBottom: 8 }} align="start">
               <Form.Item name="data_inicio" label="DATA INÍCIO" rules={[{ required: true }]}>
                  <DatePicker style={{ width: 150 }} format="DD/MM/YYYY" />
               </Form.Item>
               <Form.Item name="data_fim" label="DATA FIM">
                  <DatePicker style={{ width: 150 }} format="DD/MM/YYYY" />
               </Form.Item>
          </Space>

          <Form.Item label="IMAGEM DA MENSAGEM">
               <Upload
                  listType="picture-card"
                  maxCount={1}
                  fileList={imagemList}
                  onChange={({ fileList }) => setImagemList(fileList)}
                  beforeUpload={() => false}
                  accept="image/*"
               >
                  {imagemList.length < 1 && <div><CloudUploadOutlined /><div style={{ marginTop: 8 }}>Upload</div></div>}
               </Upload>
          </Form.Item>
        </Card>

        <Card title="DESTINATÁRIOS" size="small" style={{ marginTop: 16 }}>
            <Form.Item label="SELECIONE A ORIGEM DOS CONTATOS">
                <Radio.Group value={destino} onChange={e => setDestino(e.target.value)}>
                    <Radio.Button value="eleitores"><TeamOutlined /> BASE DE ELEITORES</Radio.Button>
                    <Radio.Button value="arquivo"><FileTextOutlined /> IMPORTAR ARQUIVO</Radio.Button>
                </Radio.Group>
            </Form.Item>

            {destino === 'arquivo' && (
                <Form.Item label="ARQUIVO DE CONTATOS (JSON, CSV, XLS, PDF)" required>
                    <Upload
                        maxCount={1}
                        fileList={fileList}
                        onChange={({ fileList }) => setFileList(fileList)}
                        beforeUpload={() => false}
                        accept=".json,.csv,.xls,.xlsx,.pdf"
                    >
                        <Button icon={<UploadOutlined />}>Selecionar Arquivo</Button>
                    </Upload>
                    <div style={{ marginTop: 8, color: '#666', fontSize: '12px' }}>
                        JSON: O conteúdo será salvo no banco.<br/>
                        Outros: O arquivo será anexado.
                    </div>
                </Form.Item>
            )}
        </Card>

        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
          <Tooltip title={!initial?.id ? "Salve a campanha antes de enviar" : (!canSend ? "Fora do período de vigência" : "Iniciar automação")}>
              <Button 
                onClick={handleEnviarCampanha} 
                disabled={!canSend}
                icon={<SendOutlined />}
                style={{ background: canSend ? '#52c41a' : undefined, color: canSend ? '#fff' : undefined, borderColor: canSend ? '#52c41a' : undefined }}
              >
                ENVIAR CAMPANHA
              </Button>
          </Tooltip>
          <Button type="primary" onClick={handleOk} icon={<SaveOutlined />}>SALVAR</Button>
        </Space>
      </Form>
    </Modal>
  )
}
