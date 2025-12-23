import { Avatar, Button, Card, DatePicker, Form, Input, InputNumber, Modal, Radio, Select, Space, Upload, message } from 'antd'
import { CloseCircleOutlined, CloudUploadOutlined, FileTextOutlined, SaveOutlined, TeamOutlined, ThunderboltOutlined, UploadOutlined } from '@ant-design/icons'
import { useEffect, useState, useMemo } from 'react'
import { useApi } from '../context/ApiContext'
import { useAuthStore } from '../store/authStore'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import * as dayjsNs from 'dayjs'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

const dayjs = (dayjsNs as any).default ?? (dayjsNs as any)

interface Props {
  open: boolean
  initial?: any
  onCancel: () => void
  onSaved: () => void
}

export default function CampanhasModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const [messageApi, contextHolder] = message.useMessage()
  const [destino, setDestino] = useState<'eleitores' | 'arquivo'>('eleitores')
  const [fileList, setFileList] = useState<any[]>([])
  const [imagemList, setImagemList] = useState<any[]>([])
  const [posicaoImagem, setPosicaoImagem] = useState<'top' | 'bottom'>('bottom')
  const [modoResposta, setModoResposta] = useState<'nenhum' | 'sim_nao'>('nenhum')
  const [perguntaSimNao, setPerguntaSimNao] = useState('')
  const [recorrenciaAtiva, setRecorrenciaAtiva] = useState(false)
  const [evolutionApis, setEvolutionApis] = useState<any[]>([])
  const [evolutionApiIds, setEvolutionApiIds] = useState<string[]>([])
  
  const api = useApi()
  const { user } = useAuthStore()

  // Stats State
  const [meta, setMeta] = useState(0)
  const [enviados, setEnviados] = useState(0)
  const [naoEnviados, setNaoEnviados] = useState(0)
  const [positivos, setPositivos] = useState(0)
  const [negativos, setNegativos] = useState(0)
  const [aguardando, setAguardando] = useState(0)
  const [arquivoResumo, setArquivoResumo] = useState({
    registros: 0,
    duplicados_distintos: 0,
    excluidos: 0,
    validos: 0,
  })
  const blocosPorDiaWatch = Form.useWatch('blocos_por_dia', form)

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

  const resolveImageSrc = (img: any) => {
    const s = String(img || '').trim()
    if (!s) return ''
    if (/^data:image\//i.test(s) && /;base64,/i.test(s)) {
      const rest = s.split(/;base64,/i)[1]?.trim() || ''
      if (rest.startsWith('/') || rest.startsWith('http://') || rest.startsWith('https://') || rest.startsWith('static/')) {
        return rest.startsWith('static/') ? `/${rest}` : rest
      }
      return s
    }
    if (s.startsWith('data:')) return s
    if (s.startsWith('http://') || s.startsWith('https://') || s.startsWith('/static/')) return s
    if (s.startsWith('static/')) return `/${s}`
    if (s.startsWith('/')) return s
    if (/\.(png|jpg|jpeg|bmp|gif|webp)$/i.test(s)) return `/static/campanhas/${s}`
    if (s.includes('/') && !s.startsWith('/')) return `/${s}`
    return `data:image/png;base64,${s}`
  }

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
      ;(async () => {
        try {
          const list = await api.listEvolutionApis()
          setEvolutionApis(list || [])
        } catch {
          setEvolutionApis([])
        }
      })()
      if (initial) {
        form.setFieldsValue({
          ...initial,
          data_inicio: initial.data_inicio ? dayjs(initial.data_inicio) : undefined,
          data_fim: initial.data_fim ? dayjs(initial.data_fim) : undefined,
        })
        setRecorrenciaAtiva(!!initial.recorrencia_ativa)

        if (initial?.imagem) {
          setImagemList([{
            uid: '-1',
            name: 'imagem',
            status: 'done',
            url: resolveImageSrc(initial.imagem),
          }])
        } else {
          setImagemList([])
        }
        
        const rawAnexo = (initial as any)?.conteudo_arquivo || (initial as any)?.AnexoJSON
        let parsedAnexo: any = null
        if (rawAnexo) {
          try {
            parsedAnexo = typeof rawAnexo === 'string' ? JSON.parse(rawAnexo) : rawAnexo
            if (!Array.isArray(parsedAnexo) && parsedAnexo?.config) {
              setPosicaoImagem(parsedAnexo.config.text_position || 'bottom')
              setModoResposta(parsedAnexo.config.response_mode === 'SIM_NAO' ? 'sim_nao' : 'nenhum')
              setPerguntaSimNao(String(parsedAnexo.config.question || ''))
              const cfg = parsedAnexo.config || {}
              const idsRaw = (cfg.evolution_api_ids ?? cfg.evolution_api_id) as any
              const arr = Array.isArray(idsRaw) ? idsRaw : (idsRaw !== undefined && idsRaw !== null ? [idsRaw] : [])
              const parsedIds = arr
                .map((x: any) => String(x ?? '').trim())
                .filter((s: any) => !!s)
              setEvolutionApiIds(parsedIds)
            }
          } catch {}
        }

        const isEleitores =
          !!parsedAnexo &&
          !Array.isArray(parsedAnexo) &&
          (parsedAnexo?.usar_eleitores === true || String(parsedAnexo?.source || '').toLowerCase() === 'eleitores')

        if (isEleitores) setDestino('eleitores')
        else if (rawAnexo) setDestino('arquivo')
        else setDestino('eleitores')
        
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
        form.setFieldsValue({
          recorrencia_ativa: false,
          total_blocos: 5,
          mensagens_por_bloco: 500,
          blocos_por_dia: 1,
          intervalo_min_seg: 5,
          intervalo_max_seg: 120,
          bloco_atual: 0,
        })
        setDestino('eleitores')
        setFileList([])
        setImagemList([])
        setPosicaoImagem('bottom')
        setModoResposta('nenhum')
        setPerguntaSimNao('')
        setRecorrenciaAtiva(false)
        setEvolutionApiIds([])
        
        // Reset stats
        setMeta(0)
        setEnviados(0)
        setNaoEnviados(0)
        setPositivos(0)
        setNegativos(0)
        setAguardando(0)
        setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
      }
    }
  }, [open, initial])

  // Calculate Meta dynamically based on selection
  useEffect(() => {
    const calculateMeta = async () => {
        const digitsOnly = (v: any) => String(v ?? '').replace(/\D/g, '')
        const calcResumoFromRows = (rows: any[]) => {
          const freq = new Map<string, number>()
          for (const row of rows) {
            if (!row || typeof row !== 'object') continue
            const keys = Object.keys(row)
            const whatsappKey =
              keys.find(k => String(k).trim().toLowerCase() === 'whatsapp')
              || keys.find(k => String(k).trim().toLowerCase().includes('whatsapp'))
              || keys.find(k => ['celular', 'telefone', 'phone', 'mobile', 'tel'].includes(String(k).trim().toLowerCase()))
            const raw = whatsappKey ? (row as any)[whatsappKey] : ''
            const d = digitsOnly(raw)
            if (!d) continue
            freq.set(d, (freq.get(d) || 0) + 1)
          }
          let duplicadosDistintos = 0
          let excluidos = 0
          for (const c of freq.values()) {
            if (c > 1) {
              duplicadosDistintos++
              excluidos += (c - 1)
            }
          }
          const validos = freq.size
          return { duplicados_distintos: duplicadosDistintos, excluidos, validos }
        }
        const detectDelimiter = (headerLine: string) => {
          const candidates = [',', ';', '\t', '|']
          let best = ','
          let bestCount = -1
          for (const c of candidates) {
            const cnt = headerLine.split(c).length - 1
            if (cnt > bestCount) {
              bestCount = cnt
              best = c
            }
          }
          return best
        }

        if (destino === 'eleitores') {
            try {
                // Fetch total eleitores from dashboard stats or dedicated endpoint
                const stats = await api.getDashboardStats()
                setMeta(stats.totalEleitores || 0)
                setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
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
                            const resumo = calcResumoFromRows(json)
                            setArquivoResumo({
                              registros: json.length,
                              duplicados_distintos: resumo.duplicados_distintos,
                              excluidos: resumo.excluidos,
                              validos: resumo.validos,
                            })
                            setMeta(resumo.validos)
                            if (json.length > 0) {
                                const keys = Object.keys(json[0]).map(k => k.toLowerCase())
                                if (!keys.includes('whatsapp')) {
                                    messageApi.warning('Atenção: O arquivo JSON não contém a chave "whatsapp".')
                                }
                            }
                        }
                    } catch {}
                } else if (file.name.endsWith('.csv')) {
                    try {
                        const text = await file.text()
                        const lines = text.split(/\r?\n/).filter((l: string) => l.trim().length > 0)
                        if (lines.length > 0) {
                            const headerLine = lines[0]
                            const delim = detectDelimiter(headerLine)
                            const headers = headerLine.split(delim).map((h: string) => String(h ?? '').trim().replace(/^"|"$/g, '').toLowerCase())
                            const idxWhatsapp = headers.findIndex((h: string) => h === 'whatsapp' || h.includes('whatsapp'))
                            if (idxWhatsapp < 0) {
                                messageApi.warning('Atenção: O arquivo CSV não contém a coluna "whatsapp".')
                            }
                            const rows: any[] = []
                            for (let i = 1; i < lines.length; i++) {
                              const parts = lines[i].split(delim)
                              const val = idxWhatsapp >= 0 ? parts[idxWhatsapp] : ''
                              rows.push({ whatsapp: String(val ?? '').trim().replace(/^"|"$/g, '') })
                            }
                            const resumo = calcResumoFromRows(rows)
                            const registros = Math.max(0, lines.length - 1)
                            setArquivoResumo({
                              registros,
                              duplicados_distintos: resumo.duplicados_distintos,
                              excluidos: resumo.excluidos,
                              validos: resumo.validos,
                            })
                            setMeta(resumo.validos)
                        } else {
                            setMeta(0)
                            setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
                        }
                    } catch {}
                } else {
                    setMeta(0)
                    setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
                }
            }
        }
    }
    calculateMeta()
  }, [destino, fileList, api])

  useEffect(() => {
    if (!open) return
    const perDayRaw = Number(blocosPorDiaWatch ?? form.getFieldValue('blocos_por_dia') ?? 1)
    const perDay = Math.max(1, Math.min(24, Math.floor(perDayRaw || 1)))
    const validRaw = Math.floor(Number(meta ?? 0))
    const valid = Math.max(0, Number.isFinite(validRaw) ? validRaw : 0)
    const total = Math.max(1, Math.min(perDay, valid || 1))
    const mpb = Math.max(1, Math.ceil((valid || 1) / total))
    const curTotal = Number(form.getFieldValue('total_blocos') ?? 0)
    const curMpb = Number(form.getFieldValue('mensagens_por_bloco') ?? 0)
    if (curTotal !== total || curMpb !== mpb) {
      form.setFieldsValue({ total_blocos: total, mensagens_por_bloco: mpb })
    }
  }, [open, meta, blocosPorDiaWatch, form])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if (modoResposta === 'sim_nao' && !String(perguntaSimNao || '').trim()) {
        messageApi.error('Informe a pergunta (SIM/NÃO)')
        return
      }
      {
        const min = Number(values.intervalo_min_seg)
        const max = Number(values.intervalo_max_seg)
        if (!Number.isFinite(min) || !Number.isFinite(max) || min <= 0 || max <= 0) {
          messageApi.error('Informe os intervalos mínimo e máximo em segundos')
          return
        }
        if (min > max) {
          messageApi.error('Intervalo mínimo não pode ser maior que o máximo')
          return
        }
      }
      
      // Helper to convert file to base64
      const toBase64 = (file: File) => new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.readAsDataURL(file);
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = error => reject(error);
      });

      const payload: any = {
        ...values,
        data_inicio: values.data_inicio ? values.data_inicio.format('YYYY-MM-DD') : null,
        data_fim: values.data_fim ? values.data_fim.format('YYYY-MM-DD') : null,
        meta, // Save calculated meta
        enviados,
        nao_enviados: naoEnviados,
        positivos,
        negativos,
        aguardando,
      }

      if (imagemList.length > 0) {
        const file = imagemList[0].originFileObj
        if (file) {
          payload.imagem = await toBase64(file as File)
        }
      } else if (initial?.imagem) {
        payload.imagem = null
      }

      // Process AnexoJSON to include config
      let finalAnexoJSON: any = null
      const configToSave: any = {
        text_position: posicaoImagem,
      }
      if (modoResposta === 'sim_nao') {
        configToSave.response_mode = 'SIM_NAO'
        configToSave.question = String(perguntaSimNao || '').trim()
      }
      if (evolutionApiIds.length) {
        configToSave.evolution_api_ids = evolutionApiIds
      }
      
      if (destino === 'arquivo' && fileList.length > 0) {
        const file = fileList[0].originFileObj
        if (file) {
            // Sempre enviar como arquivo para processamento no backend (pandas)
            payload.AnexoFile = file

            payload.anexo_json = JSON.stringify({ contacts: [], config: configToSave })
            
            // Handle JSON directly if it is JSON
            if (file.name.endsWith('.json')) {
                const text = await file.text()
                try {
                   const jsonContent = JSON.parse(text)
                   const digitsOnly = (v: any) => String(v ?? '').replace(/\D/g, '')
                   const dedupByWhatsapp = (rows: any[]) => {
                      const out: any[] = []
                      const seen = new Set<string>()
                      for (const row of rows) {
                        if (!row || typeof row !== 'object') continue
                        const keys = Object.keys(row)
                        const whatsappKey =
                          keys.find(k => String(k).trim().toLowerCase() === 'whatsapp')
                          || keys.find(k => String(k).trim().toLowerCase().includes('whatsapp'))
                          || keys.find(k => ['celular', 'telefone', 'phone', 'mobile', 'tel'].includes(String(k).trim().toLowerCase()))
                        const raw = whatsappKey ? (row as any)[whatsappKey] : ''
                        const d = digitsOnly(raw)
                        if (!d) continue
                        if (seen.has(d)) continue
                        seen.add(d)
                        if (whatsappKey) (row as any)[whatsappKey] = d
                        out.push(row)
                      }
                      return out
                   }
                   // We wrap it
                   finalAnexoJSON = {
                       contacts: Array.isArray(jsonContent) ? dedupByWhatsapp(jsonContent) : [],
                       config: configToSave
                   }
                   // We need to pass this as string to AnexoJSON field?
                   // The API might expect 'anexo_json' field in payload.
                   // Wait, payload spread values from form.
                   // If we send 'anexo_json', backend uses it.
                   // But wait, if file is sent as 'AnexoFile', backend processes it.
                   // If we want to override the JSON content, we should set anexo_json.
                   // Let's set it.
                   payload.anexo_json = JSON.stringify(finalAnexoJSON)
                } catch (e) {
                    messageApi.error('Arquivo JSON inválido')
                    return
                }
            } else {
                // CSV/XLS: Backend processes file and saves to AnexoJSON?
                // If so, we can't easily inject config unless we do it after upload?
                // Or we send config as separate field?
                // Backend 'create_campanha' doesn't seem to merge config.
                // For now, support only for JSON or if we can update it later.
                // Actually, if we use 'eleitores', we can also set anexo_json with config.
                // If CSV, we might lose this config if backend overwrites AnexoJSON.
                // Let's assume for CSV/XLS we can't support this yet without backend changes to 'uploadCampanhaAnexo'.
                // BUT, if we send 'anexo_json' string here, backend might use it.
                // If 'AnexoFile' is present, backend usually processes it and updates AnexoJSON.
                // Let's stick to JSON support or 'eleitores' for now.
                // Or better: We send it for 'eleitores' too.
            }
        }
      } else if (destino === 'eleitores') {
          payload.usar_eleitores = true
          finalAnexoJSON = {
            source: 'eleitores',
            usar_eleitores: true,
            contacts: [],
            config: configToSave,
          }
          payload.anexo_json = JSON.stringify(finalAnexoJSON)
      }

      let savedId: number
      if (initial?.id) {
        await api.updateCampanha(initial.id, payload)
        savedId = initial.id
        messageApi.success('Campanha atualizada')
      } else {
        const res = await api.createCampanha(payload)
        savedId = res.id
        messageApi.success('Campanha criada')
      }

      // Upload Anexo File if present (Still separate for big files/pandas processing if needed, 
      // but user asked for AnexoJSON to be JSONB. 
      // The backend 'campanhas_create' handles AnexoJSON from payload. 
      // The 'uploadCampanhaAnexo' endpoint handles file upload and likely processing.
      // We keep file upload for the data file (csv/xls/json contacts), but Image is now in payload.
      if (destino === 'arquivo' && payload.AnexoFile) {
           await api.uploadCampanhaAnexo(savedId, { file: payload.AnexoFile, type: 'anexo' })
      }

      onSaved()
    } catch (e: any) {
      messageApi.error(e?.response?.data?.detail || 'Erro ao salvar campanha')
    }
  }

  const getUpperFromEvent = (e: any) => {
    const v = e?.target?.value
    return typeof v === 'string' ? v.toUpperCase() : v
  }

  return (
    <>
    {contextHolder}
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
      
      <Form form={form} layout="vertical">
        <Card title="DADOS DA CAMPANHA" size="small">
          <Form.Item name="nome" label="NOME DA CAMPANHA" rules={[{ required: true, message: 'Informe o nome' }]} getValueFromEvent={getUpperFromEvent}>
            <Input prefix={<ThunderboltOutlined />} placeholder="Ex: CAMPANHA DE DOAÇÃO" />
          </Form.Item>

          <Form.Item label="TIPO DE ENVIO">
            <Radio.Group value={modoResposta} onChange={(e) => setModoResposta(e.target.value)}>
              <Radio.Button value="nenhum">MENSAGEM</Radio.Button>
              <Radio.Button value="sim_nao">PERGUNTA SIM / NÃO</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {modoResposta === 'sim_nao' && (
            <Form.Item label="PERGUNTA (SIM/NÃO)">
              <Input
                value={perguntaSimNao}
                onChange={(e: any) => setPerguntaSimNao(String(e?.target?.value || '').toUpperCase())}
                placeholder="Ex: VOCÊ APOIA NOSSO PROJETO?"
              />
            </Form.Item>
          )}

          <Form.Item
            name="descricao"
            label="DESCRIÇÃO / MENSAGEM"
            rules={[{ whitespace: true, message: 'Mensagem inválida' }]}
            extra={
              <div style={{ fontSize: 10, color: '#666' }}>
                Dica: Use <strong>(NOME)</strong> ou <strong>{'{NOME}'}</strong> para substituir pelo nome do contato.<br/>
                Certifique-se que seu arquivo contém uma coluna chamada "Nome", "Name", "Cliente" ou "Full Name".
              </div>
            }
          >
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

          <Form.Item label="EVOLUTION API (INSTÂNCIAS)">
            <Select
              mode="multiple"
              allowClear
              value={evolutionApiIds}
              placeholder={evolutionApis.length ? 'Selecione uma ou mais instâncias' : 'Nenhuma instância encontrada'}
              options={(evolutionApis || [])
                .map((x: any) => ({
                  value: String(x.id ?? '').trim(),
                  label: `${String(x.name || x.nome || x.instance_name || x.id)}${x.number ? ` - ${String(x.number)}` : ''}${x.connectionStatus ? ` (${String(x.connectionStatus)})` : ''}`,
                }))}
              onChange={(vals) => {
                const arr = Array.isArray(vals) ? vals : []
                setEvolutionApiIds(arr.map(v => String(v ?? '').trim()).filter((s: any) => !!s))
              }}
            />
          </Form.Item>

          <Form.Item label="IMAGEM DA MENSAGEM">
               <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
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
                   
                   {imagemList.length > 0 && (
                       <Form.Item label="POSIÇÃO DO TEXTO EM RELAÇÃO À IMAGEM" style={{ marginBottom: 0 }}>
                           <Radio.Group value={posicaoImagem} onChange={e => setPosicaoImagem(e.target.value)}>
                               <Radio.Button value="top">TEXTO ANTES (MENSAGEM SEPARADA)</Radio.Button>
                               <Radio.Button value="bottom">TEXTO DEPOIS (LEGENDA)</Radio.Button>
                           </Radio.Group>
                           <div style={{ fontSize: 10, color: '#999', marginTop: 4 }}>
                               {posicaoImagem === 'top' ? 'Envia texto primeiro, depois imagem.' : 'Envia imagem com o texto como legenda.'}
                           </div>
                       </Form.Item>
                   )}
               </div>
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

        <Card title="RECORRÊNCIA / BLOCOS" size="small" style={{ marginTop: 16 }}>
          {destino === 'arquivo' && fileList.length > 0 ? (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
              <div style={{ background: '#fafafa', border: '1px solid #eee', padding: '6px 10px' }}>
                REGISTROS NO ARQUIVO: <strong>{arquivoResumo.registros}</strong>
              </div>
              <div style={{ background: '#fafafa', border: '1px solid #eee', padding: '6px 10px' }}>
                NÚMEROS REPETIDOS: <strong>{arquivoResumo.duplicados_distintos}</strong>
              </div>
              <div style={{ background: '#fafafa', border: '1px solid #eee', padding: '6px 10px' }}>
                NÃO VÃO ENTRAR: <strong>{arquivoResumo.excluidos}</strong>
              </div>
              <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', padding: '6px 10px' }}>
                CONTATOS VÁLIDOS PARA ENVIO: <strong>{arquivoResumo.validos}</strong>
              </div>
            </div>
          ) : null}
          <Form.Item name="recorrencia_ativa" label="ATIVAR RECORRÊNCIA" initialValue={false}>
            <Radio.Group
              value={recorrenciaAtiva}
              onChange={(e) => {
                setRecorrenciaAtiva(!!e.target.value)
                form.setFieldsValue({ recorrencia_ativa: !!e.target.value })
              }}
            >
              <Radio.Button value={false}>NÃO</Radio.Button>
              <Radio.Button value={true}>SIM</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Space style={{ display: 'flex', marginBottom: 8 }} align="start" wrap>
            <Form.Item name="total_blocos" label="TOTAL DE BLOCOS" rules={recorrenciaAtiva ? [{ required: true }] : undefined}>
              <InputNumber min={1} max={999} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="mensagens_por_bloco" label="MENSAGENS POR BLOCO" rules={recorrenciaAtiva ? [{ required: true }] : undefined}>
              <InputNumber min={1} max={5000} style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="blocos_por_dia" label="BLOCOS POR DIA" rules={recorrenciaAtiva ? [{ required: true }] : undefined}>
              <InputNumber min={1} max={24} style={{ width: 160 }} />
            </Form.Item>
          </Space>

          <Space style={{ display: 'flex', marginBottom: 8 }} align="start" wrap>
            <Form.Item name="intervalo_min_seg" label="INTERVALO MÍNIMO (SEG)" rules={[{ required: true }]}>
              <InputNumber min={1} max={3600} style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="intervalo_max_seg" label="INTERVALO MÁXIMO (SEG)" rules={[{ required: true }]}>
              <InputNumber min={1} max={3600} style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="bloco_atual" label="BLOCO ATUAL">
              <InputNumber min={0} max={999} style={{ width: 160 }} />
            </Form.Item>
          </Space>
        </Card>

        <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
          <Button type="primary" onClick={handleOk} icon={<SaveOutlined />}>SALVAR</Button>
        </Space>
      </Form>
    </Modal>
    </>
  )
}
