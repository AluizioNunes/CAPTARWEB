import { Avatar, Button, Card, DatePicker, Form, Input, InputNumber, List, Modal, Radio, Select, Space, Tabs, Upload, App } from 'antd'
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
  const [destino, setDestino] = useState<'eleitores' | 'arquivo'>('eleitores')
  const [fileList, setFileList] = useState<any[]>([])
  const [imagemList, setImagemList] = useState<any[]>([])
  const [posicaoImagem, setPosicaoImagem] = useState<'top' | 'bottom'>('bottom')
  const [modoResposta, setModoResposta] = useState<'nenhum' | 'sim_nao'>('nenhum')
  const [perguntaSimNao, setPerguntaSimNao] = useState('')
  const [recorrenciaAtiva, setRecorrenciaAtiva] = useState(false)
  const [evolutionApis, setEvolutionApis] = useState<any[]>([])
  const [evolutionApiIds, setEvolutionApiIds] = useState<string[]>([])
  const [provedorEnvio, setProvedorEnvio] = useState<'evolution' | 'twilio' | 'meta'>('evolution')
  
  const api = useApi()
  const { user } = useAuthStore()
  const { message } = App.useApp()

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
  const [previewContacts, setPreviewContacts] = useState<{ nome?: string; whatsapp?: string }[]>([])
  const blocosPorDiaWatch = Form.useWatch('blocos_por_dia', form)
  const descricaoWatch = Form.useWatch('descricao', form)
  const metaTemplateNameWatch = Form.useWatch('meta_template_name', form)
  const metaTemplateLangWatch = Form.useWatch('meta_template_lang', form)
  const metaTemplatePreviewTextWatch = Form.useWatch('meta_template_preview_text', form)
  const metaP1Watch = Form.useWatch('meta_p1', form)
  const metaP2Watch = Form.useWatch('meta_p2', form)
  const metaP3Watch = Form.useWatch('meta_p3', form)
  const metaP4Watch = Form.useWatch('meta_p4', form)
  const metaP5Watch = Form.useWatch('meta_p5', form)

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

  const sampleContact = useMemo(() => ({ nome: 'FULANO', whatsapp: '5511999999999' }), [])

  const applyContactTokens = (text: any, contact: any) => {
    let out = String(text ?? '')
    const nameToUse = String(contact?.nome || '')
    const waToUse = String(contact?.whatsapp || '')
    out = out
      .replace(/\(NOME\)/gi, nameToUse)
      .replace(/\{NOME\}/gi, nameToUse)
      .replace(/\(NAME\)/gi, nameToUse)
      .replace(/\{NAME\}/gi, nameToUse)
      .replace(/\(WHATSAPP\)/gi, waToUse)
      .replace(/\{WHATSAPP\}/gi, waToUse)
      .replace(/\(PHONE\)/gi, waToUse)
      .replace(/\{PHONE\}/gi, waToUse)
    return out
  }

  const resolvedImagePreviewSrc = useMemo(() => {
    const first = imagemList[0]
    const raw = String(first?.url || first?.thumbUrl || '').trim()
    if (raw) return raw
    const f = first?.originFileObj as File | undefined
    const URLApi = (typeof globalThis !== 'undefined' ? (globalThis as any).URL : undefined) as any
    if (f && URLApi && typeof URLApi.createObjectURL === 'function') {
      try {
        return URLApi.createObjectURL(f)
      } catch {
        return ''
      }
    }
    return ''
  }, [imagemList])

  const computedPreviewText = useMemo(() => {
    const provider = provedorEnvio
    if (provider === 'meta') {
      const base = String(metaTemplatePreviewTextWatch || '').trim()
      const name = String(metaTemplateNameWatch || '').trim()
      const parts = [
        String(metaP1Watch || '').trim(),
        String(metaP2Watch || '').trim(),
        String(metaP3Watch || '').trim(),
        String(metaP4Watch || '').trim(),
        String(metaP5Watch || '').trim(),
      ]
      const replaced = (base || (name ? `TEMPLATE: ${name}` : '') || 'Sem template')
        .replace(/\{\{\s*1\s*\}\}/g, applyContactTokens(parts[0] || '', sampleContact))
        .replace(/\{\{\s*2\s*\}\}/g, applyContactTokens(parts[1] || '', sampleContact))
        .replace(/\{\{\s*3\s*\}\}/g, applyContactTokens(parts[2] || '', sampleContact))
        .replace(/\{\{\s*4\s*\}\}/g, applyContactTokens(parts[3] || '', sampleContact))
        .replace(/\{\{\s*5\s*\}\}/g, applyContactTokens(parts[4] || '', sampleContact))
      return replaced.trim()
    }

    let msg = String(descricaoWatch || '')
    msg = applyContactTokens(msg, sampleContact)
    if (modoResposta === 'sim_nao') {
      const q = String(perguntaSimNao || '').trim()
      const blocks = [msg.trim()]
      if (q) blocks.push(q)
      blocks.push('RESPONDA:\n1 - SIM\n2 - NÃO')
      msg = blocks.filter(Boolean).join('\n\n')
    }
    return msg.trim() || 'Sem texto'
  }, [
    provedorEnvio,
    descricaoWatch,
    modoResposta,
    perguntaSimNao,
    metaTemplateNameWatch,
    metaTemplatePreviewTextWatch,
    metaP1Watch,
    metaP2Watch,
    metaP3Watch,
    metaP4Watch,
    metaP5Watch,
    sampleContact,
  ])

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

  const parseContactsJsonLoose = (text: string) => {
    const raw = String(text || '').trim()
    if (!raw) return null
    try {
      return JSON.parse(raw)
    } catch {
      const sanitized = raw.replace(/("whatsapp"\s*:\s*)(?!")([+]?[\d-]+)/gi, '$1"$2"')
      return JSON.parse(sanitized)
    }
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
              const prov = String(parsedAnexo?.config?.provider || '').trim().toLowerCase()
              setProvedorEnvio(prov === 'twilio' ? 'twilio' : (prov === 'meta' ? 'meta' : 'evolution'))
              const cfg = parsedAnexo.config || {}
              const mtName = String(cfg.meta_template_name || '').trim()
              const mtLang = String(cfg.meta_template_lang || '').trim() || 'pt_BR'
              const mtPreview = String(cfg.meta_template_preview_text || '').trim()
              const mtParamsRaw = (cfg.meta_template_params ?? []) as any
              const mtParams = Array.isArray(mtParamsRaw) ? mtParamsRaw.map((x: any) => String(x ?? '').trim()) : []
              form.setFieldsValue({
                meta_template_name: mtName,
                meta_template_lang: mtLang,
                meta_template_preview_text: mtPreview,
                meta_p1: mtParams[0] || '',
                meta_p2: mtParams[1] || '',
                meta_p3: mtParams[2] || '',
                meta_p4: mtParams[3] || '',
                meta_p5: mtParams[4] || '',
              })
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
          meta_template_name: '',
          meta_template_lang: 'pt_BR',
          meta_template_preview_text: '',
          meta_p1: '{NOME}',
          meta_p2: '',
          meta_p3: '',
          meta_p4: '',
          meta_p5: '',
        })
        setDestino('eleitores')
        setFileList([])
        setImagemList([])
        setPosicaoImagem('bottom')
        setModoResposta('nenhum')
        setPerguntaSimNao('')
        setRecorrenciaAtiva(false)
        setEvolutionApiIds([])
        setProvedorEnvio('evolution')
        
        // Reset stats
        setMeta(0)
        setEnviados(0)
        setNaoEnviados(0)
        setPositivos(0)
        setNegativos(0)
        setAguardando(0)
        setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
        setPreviewContacts([])
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
        const pickKey = (row: any, candidates: string[]) => {
          if (!row || typeof row !== 'object') return ''
          const keys = Object.keys(row)
          for (const c of candidates) {
            const k = keys.find(k => String(k).trim().toLowerCase() === c)
            if (k) return k
          }
          for (const c of candidates) {
            const k = keys.find(k => String(k).trim().toLowerCase().includes(c))
            if (k) return k
          }
          return ''
        }
        const mapPreview = (rows: any[]) => {
          const out: { nome?: string; whatsapp?: string }[] = []
          const seen = new Set<string>()
          for (const r of rows || []) {
            if (!r || typeof r !== 'object') continue
            const kWhats = pickKey(r, ['whatsapp', 'celular', 'telefone', 'phone', 'mobile', 'tel'])
            const kNome = pickKey(r, ['nome', 'name', 'cliente', 'full name'])
            const rawWa = kWhats ? (r as any)[kWhats] : ''
            const d = digitsOnly(rawWa)
            if (!d) continue
            if (seen.has(d)) continue
            seen.add(d)
            out.push({
              nome: kNome ? String((r as any)[kNome] ?? '').trim() : '',
              whatsapp: d,
            })
            if (out.length >= 8) break
          }
          return out
        }

        if (destino === 'eleitores') {
            try {
                // Fetch total eleitores from dashboard stats or dedicated endpoint
                const stats = await api.getDashboardStats()
                setMeta(stats.totalEleitores || 0)
                setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
                setPreviewContacts([])
            } catch (e) {
                console.error('Erro ao buscar total de eleitores', e)
            }
        } else if (destino === 'arquivo' && fileList.length > 0) {
            const file = fileList[0].originFileObj
            if (file) {
                if (file.name.endsWith('.json')) {
                    try {
                        const text = await file.text()
                        const json = parseContactsJsonLoose(text)
                        if (Array.isArray(json)) {
                            const resumo = calcResumoFromRows(json)
                            setArquivoResumo({
                              registros: json.length,
                              duplicados_distintos: resumo.duplicados_distintos,
                              excluidos: resumo.excluidos,
                              validos: resumo.validos,
                            })
                            setMeta(resumo.validos)
                            setPreviewContacts(mapPreview(json))
                            if (json.length > 0) {
                                const keys = Object.keys(json[0]).map(k => k.toLowerCase())
                                if (!keys.includes('whatsapp')) {
                                    message.warning('Atenção: O arquivo JSON não contém a chave "whatsapp".')
                                }
                            }
                        } else {
                            setPreviewContacts([])
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
                            const idxNome = headers.findIndex((h: string) => h === 'nome' || h.includes('nome') || h === 'name' || h.includes('name'))
                            if (idxWhatsapp < 0) {
                                message.warning('Atenção: O arquivo CSV não contém a coluna "whatsapp".')
                            }
                            const rows: any[] = []
                            for (let i = 1; i < lines.length; i++) {
                              const parts = lines[i].split(delim)
                              const val = idxWhatsapp >= 0 ? parts[idxWhatsapp] : ''
                              const nm = idxNome >= 0 ? parts[idxNome] : ''
                              rows.push({ whatsapp: String(val ?? '').trim().replace(/^"|"$/g, ''), nome: String(nm ?? '').trim().replace(/^"|"$/g, '') })
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
                            setPreviewContacts(mapPreview(rows))
                        } else {
                            setMeta(0)
                            setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
                            setPreviewContacts([])
                        }
                    } catch {}
                } else {
                    setMeta(0)
                    setArquivoResumo({ registros: 0, duplicados_distintos: 0, excluidos: 0, validos: 0 })
                    setPreviewContacts([])
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
        message.error('Informe a pergunta (SIM/NÃO)')
        return
      }
      if (provedorEnvio !== 'meta') {
        const min = Number(values.intervalo_min_seg)
        const max = Number(values.intervalo_max_seg)
        if (!Number.isFinite(min) || !Number.isFinite(max) || min <= 0 || max <= 0) {
          message.error('Informe os intervalos mínimo e máximo em segundos')
          return
        }
        if (min > max) {
          message.error('Intervalo mínimo não pode ser maior que o máximo')
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

      delete payload.meta_template_name
      delete payload.meta_template_lang
      delete payload.meta_template_preview_text
      delete payload.meta_p1
      delete payload.meta_p2
      delete payload.meta_p3
      delete payload.meta_p4
      delete payload.meta_p5

      if (provedorEnvio === 'meta') {
        payload.recorrencia_ativa = false
        payload.total_blocos = 5
        payload.mensagens_por_bloco = 500
        payload.blocos_por_dia = 1
        payload.bloco_atual = 0
        payload.intervalo_min_seg = 5
        payload.intervalo_max_seg = 120
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
        provider: provedorEnvio,
      }
      if (modoResposta === 'sim_nao') {
        configToSave.response_mode = 'SIM_NAO'
        configToSave.question = String(perguntaSimNao || '').trim()
      }
      if (provedorEnvio === 'evolution' && evolutionApiIds.length) {
        configToSave.evolution_api_ids = evolutionApiIds
      }
      if (provedorEnvio === 'meta') {
        const mtName = String(values.meta_template_name || '').trim()
        const mtLang = String(values.meta_template_lang || '').trim() || 'pt_BR'
        const mtPreview = String(values.meta_template_preview_text || '').trim()
        const params = [
          String(values.meta_p1 || '').trim(),
          String(values.meta_p2 || '').trim(),
          String(values.meta_p3 || '').trim(),
          String(values.meta_p4 || '').trim(),
          String(values.meta_p5 || '').trim(),
        ]
        let trimmedLen = params.length
        while (trimmedLen > 0 && !params[trimmedLen - 1]) trimmedLen--
        configToSave.meta_template_name = mtName
        configToSave.meta_template_lang = mtLang
        configToSave.meta_template_preview_text = mtPreview
        configToSave.meta_template_params = params.slice(0, trimmedLen)
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
                   const jsonContent = parseContactsJsonLoose(text)
                   if (!jsonContent) throw new Error('empty')
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
                    message.error('Arquivo JSON inválido. Garanta que o campo WHATSAPP esteja entre aspas.')
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
        message.success('Campanha atualizada')
      } else {
        const res = await api.createCampanha(payload)
        savedId = res.id
        message.success('Campanha criada')
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
      message.error(e?.response?.data?.detail || 'Erro ao salvar campanha')
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
      }
      onCancel={onCancel}
      footer={null}
      destroyOnHidden
      width="96vw"
      style={{ maxWidth: 1960, top: 12 }}
      styles={{
        body: { overflowY: 'visible' },
        header: { paddingTop: 8, paddingBottom: 8 },
      }}
      closable={false}
      maskClosable={false}
      className="campanhas-modal"
    >
      <style>{`.campanhas-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .campanhas-modal .ant-modal-content{ border-radius: 0 !important; } .campanhas-modal .ant-form-item{ margin-bottom:6px; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper{ width:100%; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload{ width:100% !important; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload.ant-upload-select{ width:100% !important; height:120px !important; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload-list{ width:100%; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload-list-item-container{ width:100% !important; height:auto !important; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload-list-item{ width:100% !important; height:auto !important; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload-list-item-thumbnail img{ width:100% !important; height:auto !important; object-fit:contain; } .campanhas-modal .campanhas-meta-image-upload.ant-upload-wrapper.ant-upload-picture-card-wrapper .ant-upload-list-item-image{ width:100% !important; height:auto !important; object-fit:contain; }`}</style>
      
      <Form form={form} layout="vertical">
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 0.9fr) minmax(0, 1.45fr)', gap: 16, alignItems: 'start' }}>
              <Card title="DADOS DA CAMPANHA" size="small">
                <Form.Item name="nome" label="NOME DA CAMPANHA" rules={[{ required: true, message: 'Informe o nome' }]} getValueFromEvent={getUpperFromEvent}>
                  <Input prefix={<ThunderboltOutlined />} placeholder="Ex: CAMPANHA DE DOAÇÃO" />
                </Form.Item>

                <Space style={{ display: 'flex', marginBottom: 8 }} align="start">
                    <Form.Item name="data_inicio" label="DATA INÍCIO" rules={[{ required: true }]}>
                        <DatePicker style={{ width: 150 }} format="DD/MM/YYYY" />
                    </Form.Item>
                    <Form.Item name="data_fim" label="DATA FIM">
                        <DatePicker style={{ width: 150 }} format="DD/MM/YYYY" />
                    </Form.Item>
                </Space>
              </Card>

              <Card title="DESTINATÁRIOS" size="small">
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 420px', gap: 12, alignItems: 'start' }}>
                  <div style={{ minWidth: 0 }}>
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
                  </div>

                  {destino === 'arquivo' ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
                      <div style={{ background: '#e6f7ff', border: '1px solid #91d5ff', padding: '14px 12px', borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)', minHeight: 86, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                        <div style={{ fontSize: 30, fontWeight: 900, color: '#1890ff', lineHeight: 1.05 }}>{arquivoResumo.registros}</div>
                        <div style={{ fontSize: 12, fontWeight: 800, color: '#096dd9', whiteSpace: 'nowrap', lineHeight: 1.2 }}>REGISTROS NO ARQUIVO</div>
                      </div>
                      <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', padding: '14px 12px', borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)', minHeight: 86, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                        <div style={{ fontSize: 30, fontWeight: 900, color: '#faad14', lineHeight: 1.05 }}>{arquivoResumo.duplicados_distintos}</div>
                        <div style={{ fontSize: 12, fontWeight: 800, color: '#ad6800', whiteSpace: 'nowrap', lineHeight: 1.2 }}>NÚMEROS REPETIDOS</div>
                      </div>
                      <div style={{ background: '#fff1f0', border: '1px solid #ffa39e', padding: '14px 12px', borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)', minHeight: 86, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                        <div style={{ fontSize: 30, fontWeight: 900, color: '#cf1322', lineHeight: 1.05 }}>{arquivoResumo.excluidos}</div>
                        <div style={{ fontSize: 12, fontWeight: 800, color: '#a8071a', whiteSpace: 'nowrap', lineHeight: 1.2 }}>NÃO VÃO ENTRAR</div>
                      </div>
                      <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', padding: '14px 12px', borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)', minHeight: 86, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                        <div style={{ fontSize: 30, fontWeight: 900, color: '#3f8600', lineHeight: 1.05 }}>{arquivoResumo.validos}</div>
                        <div style={{ fontSize: 12, fontWeight: 800, color: '#237804', whiteSpace: 'nowrap', lineHeight: 1.2 }}>CONTATOS VÁLIDOS</div>
                      </div>
                    </div>
                  ) : null}
                </div>
              </Card>
            </div>

            <div style={{ borderTop: '1px solid #e8e8e8', margin: '16px 0' }} />

            <Card title="CONFIGURAÇÕES DE ENVIO" size="small">
              <Tabs
                activeKey={provedorEnvio}
                onChange={(k) => setProvedorEnvio((k as any) || 'evolution')}
                items={[
                  {
                    key: 'meta',
                    label: 'META OFICIAL API',
                    children: (
                      <div style={{ display: 'grid', gap: 16 }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
                          <Card title="TEMPLATE" size="small">
                            <Form.Item name="meta_template_name" label="NOME DO TEMPLATE (APROVADO)" rules={[{ required: true, message: 'Informe o nome do template' }]} getValueFromEvent={getUpperFromEvent}>
                              <Input placeholder="Ex: CAMPANHA_APRESENTACAO_01" />
                            </Form.Item>

                            <Space style={{ display: 'flex', marginBottom: 8 }} align="start" wrap>
                              <Form.Item name="meta_template_lang" label="IDIOMA" initialValue="pt_BR" rules={[{ required: true }]}>
                                <Select
                                  style={{ width: 200 }}
                                  options={[
                                    { value: 'pt_BR', label: 'pt_BR' },
                                    { value: 'en_US', label: 'en_US' },
                                    { value: 'es', label: 'es' },
                                  ]}
                                />
                              </Form.Item>

                              <Form.Item label="TIPO DE ENVIO">
                                <Radio.Group value={modoResposta} onChange={(e) => setModoResposta(e.target.value)}>
                                  <Radio.Button value="nenhum">TEMPLATE</Radio.Button>
                                  <Radio.Button value="sim_nao">TEMPLATE + SIM/NÃO</Radio.Button>
                                </Radio.Group>
                              </Form.Item>
                            </Space>

                            {modoResposta === 'sim_nao' && (
                              <Form.Item label="PERGUNTA (SIM/NÃO)">
                                <Input
                                  value={perguntaSimNao}
                                  onChange={(e: any) => setPerguntaSimNao(String(e?.target?.value || '').toUpperCase())}
                                  placeholder="Ex: VOCÊ APOIA NOSSO PROJETO?"
                                />
                              </Form.Item>
                            )}
                          </Card>

                          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 240px', gap: 16, alignItems: 'start' }}>
                            <Card title="VARIÁVEIS DO BODY" size="small">
                              <Space style={{ display: 'flex' }} align="start" wrap>
                                <Form.Item name="meta_p1" label="VAR 1" initialValue="{NOME}" rules={[{ whitespace: true }]}>
                                  <Input placeholder="Ex: {NOME}" />
                                </Form.Item>
                                <Form.Item name="meta_p2" label="VAR 2" rules={[{ whitespace: true }]}>
                                  <Input placeholder="Opcional" />
                                </Form.Item>
                                <Form.Item name="meta_p3" label="VAR 3" rules={[{ whitespace: true }]}>
                                  <Input placeholder="Opcional" />
                                </Form.Item>
                                <Form.Item name="meta_p4" label="VAR 4" rules={[{ whitespace: true }]}>
                                  <Input placeholder="Opcional" />
                                </Form.Item>
                                <Form.Item name="meta_p5" label="VAR 5" rules={[{ whitespace: true }]}>
                                  <Input placeholder="Opcional" />
                                </Form.Item>
                              </Space>
                            </Card>

                            <Card title="IMAGEM (OPCIONAL)" size="small">
                              <Upload
                                className="campanhas-meta-image-upload"
                                listType="picture-card"
                                maxCount={1}
                                fileList={imagemList}
                                onChange={({ fileList }) => setImagemList(fileList)}
                                beforeUpload={() => false}
                                accept="image/*"
                                style={{ width: '100%' }}
                              >
                                {imagemList.length < 1 && <div><CloudUploadOutlined /><div style={{ marginTop: 8 }}>Upload</div></div>}
                              </Upload>
                            </Card>
                          </div>
                        </div>

                        <Form.Item
                          name="meta_template_preview_text"
                          label="TEXTO DO TEMPLATE (APENAS PREVIEW)"
                          rules={[{ whitespace: true, message: 'Texto inválido' }]}
                          extra={<div style={{ fontSize: 10, color: '#666' }}>Use {'{{1}}'}..{'{{5}}'} para visualizar variáveis.</div>}
                        >
                          <Input.TextArea rows={4} placeholder="Cole aqui o texto do template aprovado para visualizar." />
                        </Form.Item>
                      </div>
                    ),
                  },
                  {
                    key: 'evolution',
                    label: 'EVOLUTIONAPI',
                    children: (
                      <div>
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
                      </div>
                    ),
                  },
                  {
                    key: 'twilio',
                    label: 'TWILIO',
                    children: (
                      <div>
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
                          </div>
                        </Form.Item>
                      </div>
                    ),
                  },
                ]}
              />
            </Card>

            {provedorEnvio !== 'meta' ? (
              <Card title="RECORRÊNCIA / BLOCOS" size="small" style={{ marginTop: 16 }}>
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
            ) : null}

            <Space style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
              <Button onClick={onCancel} icon={<CloseCircleOutlined />}>CANCELAR</Button>
              <Button type="primary" onClick={handleOk} icon={<SaveOutlined />}>SALVAR</Button>
            </Space>
          </div>

          <div style={{ width: 372, flex: 'none', position: 'sticky', top: 8, display: 'grid', gap: 16 }}>
            <Card title="PREVIEW" size="small">
              <div style={{ width: 312, margin: '0 auto' }}>
                <div style={{ background: '#111', borderRadius: 26, padding: 10 }}>
                  <div style={{ background: '#f5f5f5', borderRadius: 20, overflow: 'hidden' }}>
                    <div style={{ background: '#eaeaea', padding: '10px 12px', fontSize: 12, fontWeight: 700 }}>
                      WhatsApp
                    </div>
                    <div style={{ padding: 12, minHeight: 420, background: '#f0f2f5' }}>
                      <div style={{ maxWidth: 250, background: '#fff', borderRadius: 12, padding: 10, boxShadow: '0 1px 2px rgba(0,0,0,0.08)' }}>
                        {resolvedImagePreviewSrc ? (
                          <img src={resolvedImagePreviewSrc} style={{ width: '100%', borderRadius: 10, marginBottom: 8 }} />
                        ) : null}
                        <div style={{ fontSize: 13, lineHeight: 1.35, whiteSpace: 'pre-wrap', color: '#1f1f1f' }}>
                          {computedPreviewText}
                        </div>
                        <div style={{ fontSize: 10, color: '#999', marginTop: 6, textAlign: 'right' }}>
                          {String(metaTemplateLangWatch || 'pt_BR').trim() || 'pt_BR'}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>

            <Card title="LISTA" size="small">
              {destino === 'arquivo' ? (
                previewContacts.length > 0 ? (
                  <List
                    size="small"
                    dataSource={previewContacts}
                    renderItem={(item, idx) => {
                      const nm = String(item?.nome || '').trim()
                      const wa = String(item?.whatsapp || '').trim()
                      return (
                        <List.Item key={`${wa}-${idx}`} style={{ padding: '6px 0', borderBottom: '2px solid #b7eb8f' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', gap: 10 }}>
                            <div style={{ minWidth: 0, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {nm || 'SEM NOME'}
                            </div>
                            <div style={{ fontFamily: 'monospace', color: '#3f8600', flex: 'none' }}>
                              {wa ? `+${wa}` : '--'}
                            </div>
                          </div>
                        </List.Item>
                      )
                    }}
                  />
                ) : (
                  <div style={{ color: '#999', fontSize: 12 }}>Selecione um arquivo (JSON/CSV) para visualizar contatos.</div>
                )
              ) : (
                <div style={{ color: '#999', fontSize: 12 }}>Prévia disponível ao importar arquivo de contatos.</div>
              )}
            </Card>
          </div>
        </div>

      </Form>
    </Modal>
  )
}
