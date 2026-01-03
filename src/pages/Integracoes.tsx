import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { Card, Row, Col, Form, Input, Select, Button, Space, Tag, Divider, Switch, Checkbox, Upload, Table, Tabs, InputNumber, App } from 'antd'
import { useApi } from '../context/ApiContext'
import axios from 'axios'
import ChartComponent from '../components/ChartComponent'
import MetaCloudAPIModal from '../components/MetaCloudAPIModal'

declare global {
  interface Window {
    FB?: any
    fbAsyncInit?: any
  }
}

export default function Integracoes() {
  const [formTse] = Form.useForm()
  const [formWebhook] = Form.useForm()
  const [formTokens] = Form.useForm()
  const [formTwilio] = Form.useForm()
  const [formTwilioSend] = Form.useForm()
  const [formTwilioOptin] = Form.useForm()
  // formMeta removed, replaced by state
  const [formMetaSend] = Form.useForm()
  const [formMetaWebhook] = Form.useForm()
  const [formMetaTemplate] = Form.useForm()
  const [formMetaTemplateList] = Form.useForm()
  const [formYCloud] = Form.useForm()
  const [formDialog360] = Form.useForm()
  const [formWANotifier] = Form.useForm()
  const [statusConexao, setStatusConexao] = useState<'CONECTADO'|'DESCONECTADO'|'TESTANDO'>('DESCONECTADO')
  const [municipios, setMunicipios] = useState<{ id: number; nome: string }[]>([])
  const [recursos, setRecursos] = useState<{ id: string; name: string; format: string; url: string }[]>([])
  const [previewCols, setPreviewCols] = useState<string[]>([])
  const [previewRows, setPreviewRows] = useState<any[]>([])
  const [selectedResourceIndex, setSelectedResourceIndex] = useState<number>(0)
  const [evoKeyMasked, setEvoKeyMasked] = useState<string>('')
  const [evoStatus, setEvoStatus] = useState<'CONECTADO'|'DESCONECTADO'|'TESTANDO'>('DESCONECTADO')
  const [evoInstances, setEvoInstances] = useState<any[]>([])
  const [twilioStatus, setTwilioStatus] = useState<'CONECTADO'|'DESCONECTADO'|'TESTANDO'>('DESCONECTADO')
  const [twilioTokenMasked, setTwilioTokenMasked] = useState<string>('')
  const [twilioHasToken, setTwilioHasToken] = useState<boolean>(false)
  const [twilioApiKeySecretMasked, setTwilioApiKeySecretMasked] = useState<string>('')
  const [twilioHasApiKeySecret, setTwilioHasApiKeySecret] = useState<boolean>(false)
  const [twilioMessagingServices, setTwilioMessagingServices] = useState<any[]>([])
  const [twilioMessagingServicesLoading, setTwilioMessagingServicesLoading] = useState<boolean>(false)
  const [twilioMessagingServiceSearch, setTwilioMessagingServiceSearch] = useState<string>('')
  const [twilioOptinLoading, setTwilioOptinLoading] = useState<boolean>(false)
  const [twilioOptinItems, setTwilioOptinItems] = useState<{ number: string; status: string; opted_in: boolean }[]>([])
  const [ycloudHasApiKey, setYcloudHasApiKey] = useState<boolean>(false)
  const [ycloudApiKeyMasked, setYcloudApiKeyMasked] = useState<string>('')
  const [ycloudHasVerifyToken, setYcloudHasVerifyToken] = useState<boolean>(false)
  const [ycloudVerifyTokenMasked, setYcloudVerifyTokenMasked] = useState<string>('')
  const [dialog360HasApiKey, setDialog360HasApiKey] = useState<boolean>(false)
  const [dialog360ApiKeyMasked, setDialog360ApiKeyMasked] = useState<string>('')
  const [dialog360HasVerifyToken, setDialog360HasVerifyToken] = useState<boolean>(false)
  const [dialog360VerifyTokenMasked, setDialog360VerifyTokenMasked] = useState<string>('')
  const [wanotifierHasApiKey, setWanotifierHasApiKey] = useState<boolean>(false)
  const [wanotifierApiKeyMasked, setWanotifierApiKeyMasked] = useState<string>('')
  const [wanotifierHasVerifyToken, setWanotifierHasVerifyToken] = useState<boolean>(false)
  const [wanotifierVerifyTokenMasked, setWanotifierVerifyTokenMasked] = useState<string>('')
  const [metaStatus, setMetaStatus] = useState<'CONECTADO'|'DESCONECTADO'|'TESTANDO'>('DESCONECTADO')
  const [metaStatsDays, setMetaStatsDays] = useState<number>(14)
  const [metaStatsLoading, setMetaStatsLoading] = useState<boolean>(false)
  const [metaStatsRows, setMetaStatsRows] = useState<any[]>([])
  const [metaStatsMetric, setMetaStatsMetric] = useState<'total' | 'sent' | 'delivered' | 'read' | 'failed'>('total')
  const [metaWebhookLoading, setMetaWebhookLoading] = useState<boolean>(false)
  const [metaWebhookStatusText, setMetaWebhookStatusText] = useState<string>('')
  const [metaWebhookSubscribedText, setMetaWebhookSubscribedText] = useState<string>('')
  const [metaConfigId, setMetaConfigId] = useState<number>(() => {
    try {
      const raw = String(localStorage.getItem('metaConfigId') || '').trim()
      const n = parseInt(raw, 10)
      if (Number.isFinite(n) && n > 0) return n
      return 0
    } catch {
      return 0
    }
  })
  const [metaProfilesLoading, setMetaProfilesLoading] = useState<boolean>(false)
  const [metaProfiles, setMetaProfiles] = useState<any[]>([])
  const [metaModalOpen, setMetaModalOpen] = useState(false)
  const [metaModalInitial, setMetaModalInitial] = useState<any | null>(null)
  const [metaEmbeddedLoading, setMetaEmbeddedLoading] = useState<boolean>(false)
  const [metaEmbeddedCode, setMetaEmbeddedCode] = useState<string>('')
  const [metaEmbeddedSessionText, setMetaEmbeddedSessionText] = useState<string>('')
  const [metaEmbeddedResultText, setMetaEmbeddedResultText] = useState<string>('')
  const [metaTemplatesLoading, setMetaTemplatesLoading] = useState<boolean>(false)
  const [metaTemplatesText, setMetaTemplatesText] = useState<string>('')
  const [metaFbLoaded, setMetaFbLoaded] = useState<boolean>(false)
  
  // State for active tab to control form population
  const [activeTab, setActiveTab] = useState<string>('tse')
  const [twilioConfig, setTwilioConfig] = useState<any>(null)
  const [ycloudConfig, setYCloudConfig] = useState<any>(null)
  const [dialog360Config, setDialog360Config] = useState<any>(null)
  const [wanotifierConfig, setWanotifierConfig] = useState<any>(null)
  const [metaConfigData, setMetaConfigData] = useState<any>(null)

  const api = useApi()
  const { message, modal } = App.useApp()
  const baseUrl = (typeof window !== 'undefined' && window.location) ? `${window.location.protocol}//${window.location.host}` : ''
  const isLocalhost = (() => {
    try {
      const h = (typeof window !== 'undefined' && window.location) ? String(window.location.hostname || '') : ''
      return h === 'localhost' || h === '127.0.0.1'
    } catch {
      return false
    }
  })()
  const isLocalUrl = (url: string) => {
    try {
      const s = String(url || '').trim().toLowerCase()
      return s.includes('://localhost') || s.includes('://127.0.0.1')
    } catch {
      return false
    }
  }
  const tenantSlug = (() => {
    try {
      return String(localStorage.getItem('tenantSlug') || 'captar').trim().toLowerCase() || 'captar'
    } catch {
      return 'captar'
    }
  })()
  const defaultTwilioInboundWebhookUrl = (!isLocalhost && baseUrl) ? `${baseUrl}/api/integracoes/twilio/webhook/inbound?tenant=${encodeURIComponent(tenantSlug)}` : ''
  const defaultTwilioStatusCallbackUrl = (!isLocalhost && baseUrl) ? `${baseUrl}/api/integracoes/twilio/webhook/status?tenant=${encodeURIComponent(tenantSlug)}` : ''
  const defaultMetaWebhookUrl = (() => {
    const host = isLocalhost ? 'http://itfact.com.br' : baseUrl
    const cfg = Number(metaConfigId || 0)
    if (!host || !cfg) return ''
    return `${host}/api/integracoes/meta/webhook?tenant=${encodeURIComponent(tenantSlug)}&config_id=${encodeURIComponent(String(cfg))}`
  })()

  const loadTwilioMessagingServices = async () => {
    try {
      setTwilioMessagingServicesLoading(true)
      const res = await api.listTwilioMessagingServices()
      setTwilioMessagingServices((res as any)?.services || [])
    } catch {
      setTwilioMessagingServices([])
    } finally {
      setTwilioMessagingServicesLoading(false)
    }
  }

  const parseTwilioOptinNumbers = (raw: string): string[] => {
    const s = String(raw || '').trim()
    if (!s) return []
    const parts = s.split(/[\s,;]+/g).map((x) => String(x || '').trim()).filter(Boolean)
    const out: string[] = []
    for (const p of parts) {
      const v = String(p || '').trim()
      if (v && !out.includes(v)) out.push(v)
    }
    return out
  }

  const registrarTwilioOptin = async (optedIn: boolean) => {
    try {
      setTwilioOptinLoading(true)
      const v = formTwilioOptin.getFieldsValue()
      const numbers = parseTwilioOptinNumbers(String(v?.numbers || ''))
      const source = String(v?.source || '').trim() || undefined
      if (!numbers.length) {
        message.error('Informe ao menos um número')
        return
      }
      await api.upsertTwilioOptIn({ numbers, opted_in: optedIn, source })
      const status = await api.getTwilioOptInStatus({ numbers })
      setTwilioOptinItems(status.items || [])
      message.success(optedIn ? 'Opt-in registrado' : 'Opt-out registrado')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao atualizar opt-in')
    } finally {
      setTwilioOptinLoading(false)
    }
  }

  const consultarTwilioOptin = async () => {
    try {
      setTwilioOptinLoading(true)
      const v = formTwilioOptin.getFieldsValue()
      const numbers = parseTwilioOptinNumbers(String(v?.numbers || ''))
      if (!numbers.length) {
        setTwilioOptinItems([])
        message.error('Informe ao menos um número')
        return
      }
      const status = await api.getTwilioOptInStatus({ numbers })
      setTwilioOptinItems(status.items || [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao consultar opt-in')
    } finally {
      setTwilioOptinLoading(false)
    }
  }

  const loadMunicipios = async () => {
    try {
      const cached = localStorage.getItem('municipios_AM')
      if (cached) {
        const list = JSON.parse(cached)
        if (Array.isArray(list) && list.length) {
          setMunicipios(list)
        }
      }
      const resp = await api.listarMunicipios('AM')
      setMunicipios(resp.municipios)
      localStorage.setItem('municipios_AM', JSON.stringify(resp.municipios))
    } catch (e) {
      try {
        const resp = await axios.get('https://servicodados.ibge.gov.br/api/v1/localidades/estados/13/municipios')
        const municipios = (resp.data || []).map((m: any) => ({ id: m.id, nome: m.nome }))
        setMunicipios(municipios)
        localStorage.setItem('municipios_AM', JSON.stringify(municipios))
      } catch {
        // silencioso
      }
    }
  }

  const loadRecursos = async () => {
    try {
      const { dataset, uf } = formTse.getFieldsValue()
      const resp = await api.listarRecursosCkan(dataset, uf)
      setRecursos(resp.resources || [])
      setSelectedResourceIndex(0)
    } catch (e) {
      try {
        const { dataset, uf } = formTse.getFieldsValue()
        const queryUrl = `https://dadosabertos.tse.jus.br/api/3/action/package_search?q=${encodeURIComponent(dataset)}`
        const res = await axios.get(queryUrl)
        const arr: { id: string; name: string; format: string; url: string }[] = []
        for (const pkg of res.data?.result?.results || []) {
          for (const r of pkg.resources || []) {
            arr.push({ id: r.id, name: r.name, format: r.format, url: r.url || r.download_url })
          }
        }
        let out = (uf === 'AM') ? arr.filter(r => (r.name || '').toUpperCase().includes('AMAZONAS') || (r.name || '').toUpperCase().endsWith('AM')) : arr
        if (!out.length) {
          const altQueries = ['resultados', 'prestacao', 'eleicoes', 'candidatos']
          for (const q of altQueries) {
            const altUrl = `https://dadosabertos.tse.jus.br/api/3/action/package_search?q=${encodeURIComponent(q)}`
            const altRes = await axios.get(altUrl)
            for (const pkg of altRes.data?.result?.results || []) {
              for (const r of pkg.resources || []) {
                const item = { id: r.id, name: r.name, format: r.format, url: r.url || r.download_url }
                if (!out.find(x => x.id === item.id)) out.push(item)
              }
            }
            if (out.length) break
          }
          if (uf === 'AM') out = out.filter(r => (r.name || '').toUpperCase().includes('AMAZONAS') || (r.name || '').toUpperCase().endsWith('AM'))
        }
        setRecursos(out)
        setSelectedResourceIndex(0)
      } catch {
        // silencioso
      }
    }
  }

  const previewRecurso = async () => {
    try {
      const recurso = recursos[selectedResourceIndex] || recursos[0]
      if (!recurso?.url) {
        message.info('Nenhum recurso disponível para prévia')
        return
      }
      const result = await api.previewRecursoCkan(recurso.url, 15)
      setPreviewCols(result.columns)
      setPreviewRows(result.rows)
    } catch (e: any) {
      try {
        const recurso = recursos[selectedResourceIndex] || recursos[0]
        const resp = await axios.get(recurso.url)
        const text: string = typeof resp.data === 'string' ? resp.data : resp.request?.responseText
        if (!text) throw new Error('Sem dados')
        const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0)
        if (lines.length < 2) throw new Error('CSV vazio')
        const sep = (lines[0].includes(';')) ? ';' : ','
        const headers = lines[0].split(sep).map(h => h.trim())
        const rows = lines.slice(1, Math.min(lines.length, 16)).map(l => {
          const parts = l.split(sep)
          const obj: any = {}
          headers.forEach((h, i) => { obj[h] = (parts[i] ?? '').trim() })
          return obj
        })
        setPreviewCols(headers)
        setPreviewRows(rows)
      } catch (err: any) {
        message.error(err?.message || 'Erro ao carregar prévia')
      }
    }
  }

  // carregar ao abrir
  useEffect(() => {
    ;(async () => {
      await loadMunicipios()
      await loadRecursos()
      await previewRecurso()
      try {
        const k = await api.getEvolutionApiKeyMasked()
        setEvoKeyMasked(k.keyMasked || '')
      } catch {}
      try {
        const insts = await api.listEvolutionInstances()
        setEvoInstances((insts as any)?.rows || [])
      } catch {}
      try {
        const cfg = await api.getTwilioConfig()
        setTwilioHasToken(!!cfg.has_auth_token)
        setTwilioTokenMasked(cfg.auth_token_masked || '')
        setTwilioHasApiKeySecret(!!cfg.has_api_key_secret)
        setTwilioApiKeySecretMasked(cfg.api_key_secret_masked || '')
        setTwilioConfig(cfg)
        await loadTwilioMessagingServices()
      } catch {}
      try {
        const cfg = await api.getYCloudConfig()
        setYcloudHasApiKey(!!cfg.has_api_key)
        setYcloudApiKeyMasked(cfg.api_key_masked || '')
        setYcloudHasVerifyToken(!!cfg.has_webhook_verify_token)
        setYcloudVerifyTokenMasked(cfg.webhook_verify_token_masked || '')
        setYCloudConfig(cfg)
      } catch {}
      try {
        const cfg = await api.getDialog360Config()
        setDialog360HasApiKey(!!cfg.has_api_key)
        setDialog360ApiKeyMasked(cfg.api_key_masked || '')
        setDialog360HasVerifyToken(!!cfg.has_webhook_verify_token)
        setDialog360VerifyTokenMasked(cfg.webhook_verify_token_masked || '')
        setDialog360Config(cfg)
      } catch {}
      try {
        const cfg = await api.getWANotifierConfig()
        setWanotifierHasApiKey(!!cfg.has_api_key)
        setWanotifierApiKeyMasked(cfg.api_key_masked || '')
        setWanotifierHasVerifyToken(!!cfg.has_webhook_verify_token)
        setWanotifierVerifyTokenMasked(cfg.webhook_verify_token_masked || '')
        setWanotifierConfig(cfg)
      } catch {}
      try {
        await carregarListaMetaPerfis()
      } catch {}
    })()
  }, [])

  // Sync forms when tab is active and config is available
  useEffect(() => {
    if (activeTab === 'twilio' && twilioConfig) {
      formTwilio.setFieldsValue({
        account_sid: twilioConfig.account_sid || '',
        api_key_sid: twilioConfig.api_key_sid || '',
        messaging_service_sid: twilioConfig.messaging_service_sid || '',
        enabled_channels: Array.isArray((twilioConfig as any).enabled_channels) ? (twilioConfig as any).enabled_channels : ['sms', 'whatsapp', 'mms'],
        whatsapp_from: twilioConfig.whatsapp_from || 'whatsapp:+14155238886',
        sms_from: twilioConfig.sms_from || '',
        status_callback_url: (isLocalhost && isLocalUrl(twilioConfig.status_callback_url || '')) ? '' : (twilioConfig.status_callback_url || defaultTwilioStatusCallbackUrl),
        inbound_webhook_url: (isLocalhost && isLocalUrl(twilioConfig.inbound_webhook_url || '')) ? '' : (twilioConfig.inbound_webhook_url || defaultTwilioInboundWebhookUrl),
        validate_signature: twilioConfig.validate_signature === true,
        enabled: twilioConfig.enabled !== false,
      })
    }
  }, [activeTab, twilioConfig])

  useEffect(() => {
    if (activeTab === 'ycloud' && ycloudConfig) {
      formYCloud.setFieldsValue({
        base_url: ycloudConfig.base_url || '',
        phone_number_id: ycloudConfig.phone_number_id || '',
        business_account_id: ycloudConfig.business_account_id || '',
        enabled: ycloudConfig.enabled !== false,
      })
    }
  }, [activeTab, ycloudConfig])

  useEffect(() => {
    if (activeTab === 'dialog360' && dialog360Config) {
      formDialog360.setFieldsValue({
        base_url: dialog360Config.base_url || '',
        phone_number_id: dialog360Config.phone_number_id || '',
        business_account_id: dialog360Config.business_account_id || '',
        enabled: dialog360Config.enabled !== false,
      })
    }
  }, [activeTab, dialog360Config])

  useEffect(() => {
    if (activeTab === 'wanotifier' && wanotifierConfig) {
      formWANotifier.setFieldsValue({
        base_url: wanotifierConfig.base_url || '',
        phone_number_id: wanotifierConfig.phone_number_id || '',
        business_account_id: wanotifierConfig.business_account_id || '',
        enabled: wanotifierConfig.enabled !== false,
      })
    }
  }, [activeTab, wanotifierConfig])

  useEffect(() => {
    if (activeTab === 'meta' && metaConfigData) {
      formMetaWebhook.setFieldsValue({
        phone_number_id: metaConfigData.phone_number_id || '',
        waba_id: metaConfigData.business_account_id || '',
        override_callback_uri: defaultMetaWebhookUrl || '',
        verify_token: '',
      })
    }
  }, [activeTab, metaConfigData, defaultMetaWebhookUrl])

  useEffect(() => {
    try {
      if (metaConfigId) localStorage.setItem('metaConfigId', String(metaConfigId))
      else localStorage.removeItem('metaConfigId')
    } catch {}
    ;(async () => {
      try {
        await carregarMetaConfig(metaConfigId || undefined)
      } catch {}
    })()
  }, [metaConfigId])

  useEffect(() => {
    try {
      if (typeof window === 'undefined') return
      if (window.FB) {
        setMetaFbLoaded(true)
        return
      }
      const existing = document.getElementById('facebook-jssdk')
      if (existing) return
      const script = document.createElement('script')
      script.id = 'facebook-jssdk'
      script.src = 'https://connect.facebook.net/pt_BR/sdk.js'
      script.async = true
      script.defer = true
      script.onload = () => setMetaFbLoaded(true)
      document.body.appendChild(script)
    } catch {}
  }, [])
  
  const testarEvolution = async () => {
    try {
      setEvoStatus('TESTANDO')
      const res = await api.testEvolutionApi()
      const ok = !!res.ok
      setEvoStatus(ok ? 'CONECTADO' : 'DESCONECTADO')
      message[ok ? 'success' : 'error'](ok ? `Evolution API conectada${res.version ? ` (v${res.version})` : ''}` : `Falha na Evolution API (HTTP ${res.status_code})`)
    } catch (e: any) {
      setEvoStatus('DESCONECTADO')
      message.error(e?.response?.data?.detail || 'Erro ao testar Evolution API')
    }
  }

  const salvarTwilio = async () => {
    try {
      const v = formTwilio.getFieldsValue()
      const payload = {
        account_sid: String(v.account_sid || '').trim(),
        auth_token: String(v.auth_token || '').trim(),
        api_key_sid: String(v.api_key_sid || '').trim() || undefined,
        api_key_secret: String(v.api_key_secret || '').trim() || undefined,
        messaging_service_sid: String(v.messaging_service_sid || '').trim() || undefined,
        whatsapp_from: String(v.whatsapp_from || '').trim() || undefined,
        sms_from: String(v.sms_from || '').trim() || undefined,
        enabled_channels: Array.isArray(v.enabled_channels) ? v.enabled_channels : undefined,
        status_callback_url: String(v.status_callback_url || '').trim() || undefined,
        inbound_webhook_url: String(v.inbound_webhook_url || '').trim() || undefined,
        validate_signature: v.validate_signature === true,
        enabled: v.enabled !== false,
      }
      await api.saveTwilioConfig(payload)
      message.success('Configuração Twilio salva')
      try {
        const cfg = await api.getTwilioConfig()
        setTwilioHasToken(!!cfg.has_auth_token)
        setTwilioTokenMasked(cfg.auth_token_masked || '')
        setTwilioHasApiKeySecret(!!cfg.has_api_key_secret)
        setTwilioApiKeySecretMasked(cfg.api_key_secret_masked || '')
      } catch {}
      formTwilio.setFieldsValue({ auth_token: '', api_key_secret: '' })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao salvar configuração Twilio')
    }
  }

  const testarTwilio = async () => {
    try {
      setTwilioStatus('TESTANDO')
      const res = await api.testTwilio()
      const ok = !!res.ok
      setTwilioStatus(ok ? 'CONECTADO' : 'DESCONECTADO')
      message[ok ? 'success' : 'error'](
        ok ? 'Twilio conectada com sucesso' : `Falha na Twilio (HTTP ${res.status_code})`
      )
    } catch (e: any) {
      setTwilioStatus('DESCONECTADO')
      message.error(e?.response?.data?.detail || 'Erro ao testar Twilio')
    }
  }

  const carregarListaMetaPerfis = async () => {
    try {
      setMetaProfilesLoading(true)
      const res = await api.listMetaWhatsAppConfigs()
      setMetaProfiles((res as any)?.rows || [])
    } catch {
      setMetaProfiles([])
    } finally {
      setMetaProfilesLoading(false)
    }
  }

  const abrirNovoPerfilMeta = () => {
    setMetaModalInitial(null)
    setMetaModalOpen(true)
  }

  const abrirEdicaoPerfilMeta = async (configId: number) => {
    try {
      const cfg = await api.getMetaWhatsAppConfig(configId)
      setMetaModalInitial(cfg as any)
      setMetaModalOpen(true)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar perfil Meta')
    }
  }

  const excluirPerfilMeta = async (configId: number) => {
    modal.confirm({
      title: 'Excluir conexão Meta',
      content: 'Tem certeza que deseja excluir este perfil?',
      okText: 'Excluir',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await api.deleteMetaWhatsAppConfig(configId)
          message.success('Perfil Meta excluído')
          await carregarListaMetaPerfis()
          if (Number(metaConfigId || 0) === Number(configId || 0)) {
            try {
              const next = (metaProfiles || []).find((p: any) => Number(p?.id || 0) !== Number(configId || 0))
              if (next?.id) setMetaConfigId(Number(next.id))
            } catch {}
          }
        } catch (e: any) {
          message.error(e?.response?.data?.detail || 'Erro ao excluir perfil Meta')
        }
      },
    })
  }

  const testarMeta = async () => {
    try {
      if (!metaConfigId) {
        message.error('Selecione um perfil Meta')
        return
      }
      setMetaStatus('TESTANDO')
      const res = await api.testMetaWhatsApp(metaConfigId)
      const ok = !!res.ok
      setMetaStatus(ok ? 'CONECTADO' : 'DESCONECTADO')
      message[ok ? 'success' : 'error'](
        ok ? 'Meta Cloud API conectada com sucesso' : `Falha na Meta (HTTP ${res.status_code})`
      )
    } catch (e: any) {
      setMetaStatus('DESCONECTADO')
      message.error(e?.response?.data?.detail || 'Erro ao testar Meta')
    }
  }

  const metaWebhookApplyWaba = async (override: boolean) => {
    try {
      if (!metaConfigId) {
        message.error('Selecione um perfil Meta')
        return
      }
      setMetaWebhookLoading(true)
      const vCfg = metaConfigData || {}
      const v = formMetaWebhook.getFieldsValue()
      const wabaId = String(v.waba_id || vCfg.business_account_id || '').trim()
      const overrideUrl = override ? String(v.override_callback_uri || '').trim() : ''
      const verifyToken = String(v.verify_token || '').trim()
      const res = await api.setMetaWebhookOverrideWaba({ waba_id: wabaId || undefined, override_callback_uri: overrideUrl || undefined, verify_token: verifyToken || undefined }, metaConfigId)
      setMetaWebhookSubscribedText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res as any) }
      })
      message.success(override ? 'Override aplicado no WABA' : 'WABA voltou para callback padrão do app')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao aplicar override no WABA')
    } finally {
      setMetaWebhookLoading(false)
    }
  }

  const metaWebhookApplyPhone = async (override: boolean) => {
    try {
      if (!metaConfigId) {
        message.error('Selecione um perfil Meta')
        return
      }
      setMetaWebhookLoading(true)
      const vCfg = metaConfigData || {}
      const v = formMetaWebhook.getFieldsValue()
      const phoneId = String(v.phone_number_id || vCfg.phone_number_id || '').trim()
      const overrideUrl = override ? String(v.override_callback_uri || '').trim() : ''
      const verifyToken = String(v.verify_token || '').trim()
      const res = await api.setMetaWebhookOverridePhone({ phone_number_id: phoneId || undefined, override_callback_uri: overrideUrl, verify_token: verifyToken || undefined }, metaConfigId)
      setMetaWebhookStatusText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res as any) }
      })
      message.success(override ? 'Override aplicado no Phone Number' : 'Override removido do Phone Number')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao aplicar override no Phone Number')
    } finally {
      setMetaWebhookLoading(false)
    }
  }

  const metaWebhookLoadStatus = async () => {
    try {
      if (!metaConfigId) {
        message.error('Selecione um perfil Meta')
        return
      }
      setMetaWebhookLoading(true)
      const vCfg = metaConfigData || {}
      const v = formMetaWebhook.getFieldsValue()
      const phoneId = String(v.phone_number_id || vCfg.phone_number_id || '').trim()
      const res = await api.getMetaWebhookOverrideStatus({ phone_number_id: phoneId || undefined }, metaConfigId)
      setMetaWebhookStatusText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res as any) }
      })
      message.success('Status do webhook carregado')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao consultar status do webhook')
    } finally {
      setMetaWebhookLoading(false)
    }
  }

  const metaWebhookLoadSubscribedApps = async () => {
    try {
      if (!metaConfigId) {
        message.error('Selecione um perfil Meta')
        return
      }
      setMetaWebhookLoading(true)
      const vCfg = metaConfigData || {}
      const v = formMetaWebhook.getFieldsValue()
      const wabaId = String(v.waba_id || vCfg.business_account_id || '').trim()
      const res = await api.getMetaWebhookSubscribedApps({ waba_id: wabaId || undefined }, metaConfigId)
      setMetaWebhookSubscribedText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res as any) }
      })
      message.success('Subscribed apps carregado')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao consultar subscribed_apps')
    } finally {
      setMetaWebhookLoading(false)
    }
  }

  const metaUploadRequest = async (options: any) => {
    const { file, onSuccess, onError } = options || {}
    try {
      if (!metaConfigId) throw new Error('Selecione um perfil Meta')
      const res = await api.uploadMetaWhatsAppMedia(file as File, metaConfigId)
      try {
        ;(file as any).response = res
        ;(file as any).meta_media_id = res.id
      } catch {}
      if (onSuccess) onSuccess(res, file)
    } catch (e: any) {
      if (onError) onError(e)
    }
  }

  const enviarMetaTeste = async () => {
    try {
      if (!metaConfigId) {
        message.error('Selecione um perfil Meta')
        return
      }
      const v = formMetaSend.getFieldsValue()
      const to = String(v.to || '').trim()
      const body = String(v.body || '').trim()
      const templateName = String(v.template_name || '').trim()
      const templateLang = String(v.template_lang || '').trim()
      const templateComponentsRaw = String(v.template_components || '').trim()
      let templateComponents: any[] | undefined = undefined
      if (templateComponentsRaw) {
        try {
          const parsed = JSON.parse(templateComponentsRaw)
          if (Array.isArray(parsed)) templateComponents = parsed as any[]
        } catch {}
      }
      const textPosition = (String(v.text_position || '').trim().toLowerCase() === 'top') ? 'top' : 'bottom'
      const rawMediaUrl = String(v.media_url || '').trim()
      const files = Array.isArray(v.attachments) ? v.attachments : []
      const mediaId = String((files[0]?.response?.id || files[0]?.meta_media_id || '')).trim()
      if (!to) {
        message.error('Informe o destino')
        return
      }
      if (!templateName && !body && !mediaId && !rawMediaUrl) {
        message.error('Informe uma mensagem ou um anexo')
        return
      }
      const res = await api.sendMetaWhatsApp({
        to,
        body: templateName ? undefined : (body || undefined),
        media_id: templateName ? undefined : (mediaId || undefined),
        media_url: templateName ? undefined : ((!mediaId && rawMediaUrl) ? rawMediaUrl : undefined),
        media_type: templateName ? undefined : ((mediaId || rawMediaUrl) ? 'image' : undefined),
        text_position: templateName ? undefined : (textPosition as any),
        template_name: templateName || undefined,
        template_lang: templateName ? (templateLang || 'pt_BR') : undefined,
        template_components: templateName ? templateComponents : undefined,
      }, metaConfigId)
      const msgId = String((res as any)?.message_id || ((res as any)?.message_ids || [])[0] || '').trim()
      message.success(msgId ? `Mensagem enviada (${msgId})` : 'Mensagem enviada')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao enviar mensagem')
    }
  }

  const carregarMetaConfig = async (configId?: number) => {
    const id = Number(configId || 0)
    if (!id) {
      setMetaConfigData({
        base_url: 'https://graph.facebook.com',
        api_version: 'v21.0',
        phone_number_id: '',
        business_account_id: '',
        app_id: '',
        configuration_id: '',
        partner_solution_id: '',
        redirect_uri: '',
        validate_signature: false,
        enabled: true,
      })
      // formMetaWebhook sync handled by useEffect
      return
    }
    const cfg = await api.getMetaWhatsAppConfig(id)
    setMetaConfigData(cfg)
    // formMetaWebhook sync handled by useEffect
  }

  const initMetaFacebookSdk = () => {
    const appId = String(metaConfigData?.app_id || '').trim()
    if (!appId) throw new Error('Informe App ID')
    if (!window.FB) throw new Error('Facebook SDK não carregado')
    const ver = String(metaConfigData?.api_version || 'v22.0').trim() || 'v22.0'
    const sdkVer = ver.startsWith('v') ? ver : `v${ver}`
    window.FB.init({ appId, cookie: true, xfbml: false, version: sdkVer })
  }

  const iniciarEmbeddedSignup = async () => {
    try {
      setMetaEmbeddedLoading(true)
      setMetaEmbeddedSessionText('')
      setMetaEmbeddedResultText('')

      initMetaFacebookSdk()
      const configurationId = String(metaConfigData?.configuration_id || '').trim()
      const solutionId = String(metaConfigData?.partner_solution_id || '').trim()
      const redirectUri = String(metaConfigData?.redirect_uri || '').trim()
      const appId = String(metaConfigData?.app_id || '').trim()

      if (!configurationId) throw new Error('Informe Configuration ID')
      if (!solutionId) throw new Error('Informe Partner Solution ID')

      const resp: any = await new Promise((resolve, reject) => {
        window.FB.login(
          (r: any) => {
            if (!r) return reject(new Error('Resposta vazia do Facebook'))
            if (r.status !== 'connected' || !r.authResponse) return reject(new Error('Login não autorizado'))
            resolve(r)
          },
          {
            config_id: configurationId,
            response_type: 'code',
            override_default_response_type: true,
            scope: 'business_management,whatsapp_business_management,whatsapp_business_messaging',
            extras: {
              setup: { solutionID: solutionId },
              sessionInfoVersion: '3',
            },
          }
        )
      })

      setMetaEmbeddedSessionText(() => {
        try { return JSON.stringify(resp, null, 2) } catch { return String(resp) }
      })

      const code = String(resp?.authResponse?.code || '').trim()
      setMetaEmbeddedCode(code)
      if (!code) throw new Error('Code não retornou no login')

      const res = await api.exchangeMetaEmbeddedSignup(
        {
          code,
          redirect_uri: redirectUri || undefined,
          app_id: appId || undefined,
          configuration_id: configurationId || undefined,
          partner_solution_id: solutionId || undefined,
        },
        metaConfigId
      )

      setMetaEmbeddedResultText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res) }
      })
      await carregarMetaConfig(metaConfigId)
      message.success('Embedded Signup concluído')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || 'Erro no Embedded Signup')
    } finally {
      setMetaEmbeddedLoading(false)
    }
  }

  const trocarCodePorToken = async () => {
    try {
      setMetaEmbeddedLoading(true)
      const code = String(metaEmbeddedCode || '').trim()
      if (!code) {
        message.error('Informe o code')
        return
      }
      const configurationId = String(metaConfigData?.configuration_id || '').trim()
      const solutionId = String(metaConfigData?.partner_solution_id || '').trim()
      const redirectUri = String(metaConfigData?.redirect_uri || '').trim()
      const appId = String(metaConfigData?.app_id || '').trim()
      const res = await api.exchangeMetaEmbeddedSignup(
        {
          code,
          redirect_uri: redirectUri || undefined,
          app_id: appId || undefined,
          configuration_id: configurationId || undefined,
          partner_solution_id: solutionId || undefined,
        },
        metaConfigId
      )
      setMetaEmbeddedResultText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res) }
      })
      await carregarMetaConfig(metaConfigId)
      message.success('Troca realizada')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao trocar code por token')
    } finally {
      setMetaEmbeddedLoading(false)
    }
  }

  const criarMetaTemplate = async () => {
    try {
      setMetaTemplatesLoading(true)
      const v = formMetaTemplate.getFieldsValue()
      const payload = {
        template_name: String(v.template_name || '').trim(),
        language: String(v.language || '').trim() || undefined,
        category: String(v.category || '').trim() || undefined,
        body_text: String(v.body_text || '').trim(),
      }
      if (!payload.template_name || !payload.body_text) {
        message.error('Informe Template Name e Body Text')
        return
      }
      const res = await api.createMetaTemplate(payload as any, metaConfigId)
      setMetaTemplatesText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res) }
      })
      message.success('Template enviado para criação')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao criar template')
    } finally {
      setMetaTemplatesLoading(false)
    }
  }

  const listarMetaTemplates = async () => {
    try {
      setMetaTemplatesLoading(true)
      const v = formMetaTemplateList.getFieldsValue()
      const payload = {
        waba_id: String(v.waba_id || '').trim() || undefined,
        name: String(v.name || '').trim() || undefined,
        status: String(v.status || '').trim() || undefined,
        limit: typeof v.limit === 'number' ? v.limit : undefined,
      }
      const res = await api.listMetaTemplates(payload as any, metaConfigId)
      setMetaTemplatesText(() => {
        try { return JSON.stringify(res, null, 2) } catch { return String(res) }
      })
      message.success('Templates carregados')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao listar templates')
    } finally {
      setMetaTemplatesLoading(false)
    }
  }

  const carregarMetaStats = async (days?: number) => {
    try {
      setMetaStatsLoading(true)
      const d = typeof days === 'number' ? days : metaStatsDays
      const res = await api.getMetaWhatsAppStats(d)
      setMetaStatsRows((res as any)?.rows || [])
      if (typeof (res as any)?.days === 'number') setMetaStatsDays((res as any).days)
    } catch (e: any) {
      setMetaStatsRows([])
      message.error(e?.response?.data?.detail || 'Erro ao carregar estatísticas')
    } finally {
      setMetaStatsLoading(false)
    }
  }

  const salvarYCloud = async () => {
    try {
      const v = formYCloud.getFieldsValue()
      await api.saveYCloudConfig({
        base_url: String(v.base_url || '').trim() || undefined,
        api_key: String(v.api_key || '').trim() || undefined,
        phone_number_id: String(v.phone_number_id || '').trim() || undefined,
        business_account_id: String(v.business_account_id || '').trim() || undefined,
        webhook_verify_token: String(v.webhook_verify_token || '').trim() || undefined,
        enabled: v.enabled !== false,
      })
      message.success('Configuração YCloud salva')
      try {
        const cfg = await api.getYCloudConfig()
        setYcloudHasApiKey(!!cfg.has_api_key)
        setYcloudApiKeyMasked(cfg.api_key_masked || '')
        setYcloudHasVerifyToken(!!cfg.has_webhook_verify_token)
        setYcloudVerifyTokenMasked(cfg.webhook_verify_token_masked || '')
      } catch {}
      formYCloud.setFieldsValue({ api_key: '', webhook_verify_token: '' })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao salvar configuração YCloud')
    }
  }

  const salvarDialog360 = async () => {
    try {
      const v = formDialog360.getFieldsValue()
      await api.saveDialog360Config({
        base_url: String(v.base_url || '').trim() || undefined,
        api_key: String(v.api_key || '').trim() || undefined,
        phone_number_id: String(v.phone_number_id || '').trim() || undefined,
        business_account_id: String(v.business_account_id || '').trim() || undefined,
        webhook_verify_token: String(v.webhook_verify_token || '').trim() || undefined,
        enabled: v.enabled !== false,
      })
      message.success('Configuração 360dialog salva')
      try {
        const cfg = await api.getDialog360Config()
        setDialog360HasApiKey(!!cfg.has_api_key)
        setDialog360ApiKeyMasked(cfg.api_key_masked || '')
        setDialog360HasVerifyToken(!!cfg.has_webhook_verify_token)
        setDialog360VerifyTokenMasked(cfg.webhook_verify_token_masked || '')
      } catch {}
      formDialog360.setFieldsValue({ api_key: '', webhook_verify_token: '' })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao salvar configuração 360dialog')
    }
  }

  const salvarWANotifier = async () => {
    try {
      const v = formWANotifier.getFieldsValue()
      await api.saveWANotifierConfig({
        base_url: String(v.base_url || '').trim() || undefined,
        api_key: String(v.api_key || '').trim() || undefined,
        phone_number_id: String(v.phone_number_id || '').trim() || undefined,
        business_account_id: String(v.business_account_id || '').trim() || undefined,
        webhook_verify_token: String(v.webhook_verify_token || '').trim() || undefined,
        enabled: v.enabled !== false,
      })
      message.success('Configuração WANotifier salva')
      try {
        const cfg = await api.getWANotifierConfig()
        setWanotifierHasApiKey(!!cfg.has_api_key)
        setWanotifierApiKeyMasked(cfg.api_key_masked || '')
        setWanotifierHasVerifyToken(!!cfg.has_webhook_verify_token)
        setWanotifierVerifyTokenMasked(cfg.webhook_verify_token_masked || '')
      } catch {}
      formWANotifier.setFieldsValue({ api_key: '', webhook_verify_token: '' })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao salvar configuração WANotifier')
    }
  }

  const enviarTwilioTeste = async () => {
    try {
      const v = formTwilioSend.getFieldsValue()
      const channel = String(v.channel || 'sms').trim().toLowerCase()
      let to = String(v.to || '').trim()
      if (channel === 'whatsapp') {
        if (to && !to.toLowerCase().startsWith('whatsapp:')) to = `whatsapp:${to}`
      } else {
        if (to.toLowerCase().startsWith('whatsapp:')) to = to.slice('whatsapp:'.length)
      }
      const body = String(v.body || '').trim()
      const contentSid = String(v.content_sid || '').trim()
      const contentVarsText = String(v.content_variables || '').trim()
      let contentVariables: any = undefined
      if (contentSid && contentVarsText) {
        try {
          contentVariables = JSON.parse(contentVarsText)
        } catch {
          contentVariables = contentVarsText
        }
      }
      const fromOverride = String(v.from_override || '').trim()
      const statusCallbackUrl = String(v.status_callback_url_override || '').trim()
      const rawMedia = String(v.media_urls || '').trim()
      const manualMediaUrls = rawMedia
        ? rawMedia.split(/[\n,]+/).map((s: string) => s.trim()).filter(Boolean)
        : undefined
      const files = Array.isArray(v.attachments) ? v.attachments : []
      const uploadedUrls = files
        .map((f: any) => String(f?.url || f?.response?.url || '').trim())
        .filter(Boolean)

      const combined = [...(manualMediaUrls || []), ...uploadedUrls].filter(Boolean)
      const uniqueMediaUrls = Array.from(new Set(combined))

      if (channel === 'sms' && uniqueMediaUrls.length) {
        message.error('SMS não suporta anexos. Use MMS ou WhatsApp.')
        return
      }

      if (!body && !contentSid) {
        message.error("Informe uma 'Mensagem' ou um 'Content SID'")
        return
      }

      const res = await api.sendTwilio({
        to,
        channel,
        body: body || undefined,
        content_sid: contentSid || undefined,
        content_variables: contentSid ? contentVariables : undefined,
        from_override: fromOverride || undefined,
        status_callback_url: statusCallbackUrl || undefined,
        media_urls: uniqueMediaUrls.length ? uniqueMediaUrls : undefined,
      })
      message.success(res?.sid ? `Mensagem enviada (${res.sid})` : 'Mensagem enviada')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao enviar mensagem')
    }
  }

  const twilioUploadRequest = async (options: any) => {
    const { file, onSuccess, onError } = options || {}
    try {
      const res = await api.uploadTwilioMedia(file as File)
      try {
        ;(file as any).url = res.url
      } catch {}
      if (onSuccess) onSuccess(res, file)
    } catch (e: any) {
      if (onError) onError(e)
    }
  }

  const twilioMessagingServiceOptions = (() => {
    const base = (twilioMessagingServices || []).map((s: any) => {
      const sid = String(s?.sid || '').trim()
      const name = String(s?.friendly_name || '').trim()
      return { label: name ? `${name} (${sid})` : sid, value: sid }
    }).filter((o: any) => !!o.value)
    const searched = String(twilioMessagingServiceSearch || '').trim()
    if (searched && !base.find((o: any) => o.value === searched)) {
      return [{ label: searched, value: searched }, ...base]
    }
    return base
  })()

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <h1 className="page-title">INTEGRAÇÕES</h1>
      <Tabs
        defaultActiveKey="tse"
        onChange={setActiveTab}
        items={[
          {
            key: 'tse',
            label: 'TSE',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={16}>
                  <Card title="APIS TSE" extra={<Tag color="blue">AMAZONAS</Tag>}>
                    <Form form={formTse} layout="vertical" initialValues={{ baseUrl: 'https://dadosabertos.tse.jus.br', uf: 'AM', dataset: 'eleitorado_municipio' }}>
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item name="baseUrl" label="Base URL">
                            <Input placeholder="https://dadosabertos.tse.jus.br" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="uf" label="UF">
                            <Select options={[{ label: 'Amazonas', value: 'AM' }]} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item name="dataset" label="Dataset">
                            <Select
                              onChange={async () => { await loadRecursos(); await previewRecurso(); }}
                              options={[
                                { label: 'Eleitorado por município', value: 'eleitorado_municipio' },
                                { label: 'Resultados por município', value: 'resultados_municipio' },
                                { label: 'Zonas eleitorais', value: 'zonas_eleitorais' },
                                { label: 'Candidatos', value: 'candidatos' },
                              ]}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="municipio" label="Município (opcional)">
                            <Select
                              showSearch
                              placeholder="Selecione um município"
                              options={municipios.map(m => ({ label: m.nome, value: m.nome }))}
                            />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Space wrap>
                        <Button type="primary" onClick={async () => {
                          try {
                            setStatusConexao('TESTANDO')
                            const { baseUrl, uf, dataset, municipio } = formTse.getFieldsValue()
                            try {
                              const resp = await api.testarIntegracao({ base_url: baseUrl, uf, dataset, municipio })
                              if (resp.connected) {
                                setStatusConexao('CONECTADO')
                                message.success('Conexão realizada com sucesso')
                              } else {
                                setStatusConexao('DESCONECTADO')
                                message.error(`Falha na conexão (HTTP ${resp.status_code})`)
                              }
                            } catch {
                              const res = await axios.get(baseUrl)
                              const ok = res.status >= 200 && res.status < 300
                              setStatusConexao(ok ? 'CONECTADO' : 'DESCONECTADO')
                              message[ok ? 'success' : 'error'](ok ? 'Conexão realizada com sucesso' : `Falha na conexão (HTTP ${res.status})`)
                            }
                          } catch (e: any) {
                            setStatusConexao('DESCONECTADO')
                            message.error(e?.response?.data?.detail || 'Erro ao testar conexão')
                          }
                        }}>Testar Conexão</Button>
                        <Button onClick={async () => {
                          try {
                            const { baseUrl, uf, dataset, municipio } = formTse.getFieldsValue()
                            const { webhookUrl, webhookSecret } = formWebhook.getFieldsValue()
                            const { tseToken, externalApiToken } = formTokens.getFieldsValue()
                            const cfg = {
                              base_url: baseUrl,
                              uf,
                              dataset,
                              municipio,
                              webhook_url: webhookUrl,
                              webhook_secret: webhookSecret,
                              tse_token: tseToken,
                              external_api_token: externalApiToken,
                              active_webhook: false,
                            }
                            const saved = await api.salvarIntegracaoConfig(cfg)
                            if (saved.saved) {
                              message.success('Configuração salva')
                            }
                          } catch (e: any) {
                            try {
                              const { baseUrl, uf, dataset, municipio } = formTse.getFieldsValue()
                              const { webhookUrl, webhookSecret } = formWebhook.getFieldsValue()
                              const { tseToken, externalApiToken } = formTokens.getFieldsValue()
                              const cfg = {
                                base_url: baseUrl,
                                uf,
                                dataset,
                                municipio,
                                webhook_url: webhookUrl,
                                webhook_secret: webhookSecret,
                                tse_token: tseToken,
                                external_api_token: externalApiToken,
                                active_webhook: false,
                              }
                              localStorage.setItem('integracao_cfg', JSON.stringify(cfg))
                              message.success('Configuração salva localmente')
                            } catch {
                              message.error(e?.response?.data?.detail || 'Erro ao salvar configuração')
                            }
                          }
                        }}>Salvar Configuração</Button>
                        <Tag color={statusConexao === 'CONECTADO' ? 'green' : (statusConexao === 'TESTANDO' ? 'blue' : 'default')}>STATUS: {statusConexao}</Tag>
                        <Button onClick={async () => { await loadRecursos(); await previewRecurso(); }}>Prévia Dataset (AM)</Button>
                        <Select
                          style={{ minWidth: 240 }}
                          placeholder="Selecione recurso"
                          value={recursos.length ? selectedResourceIndex : undefined}
                          onChange={(idx) => setSelectedResourceIndex(idx)}
                          options={recursos.map((r, i) => ({ label: r.name || r.url, value: i }))}
                        />
                      </Space>
                    </Form>
                  </Card>
                  <Divider />
                  <Card title="Prévia do Dataset Selecionado (primeiras linhas)">
                    <Table
                      size="small"
                      bordered
                      pagination={false}
                      columns={previewCols.map(c => ({ title: c, dataIndex: c }))}
                      dataSource={previewRows}
                      rowKey={(_row, idx) => String(idx)}
                    />
                  </Card>
                </Col>

                <Col xs={24} xl={8}>
                  <Card title="Webhooks">
                    <Form form={formWebhook} layout="vertical">
                      <Form.Item name="webhookUrl" label="URL">
                        <Input placeholder="https://seu-sistema.com/webhook" />
                      </Form.Item>
                      <Form.Item name="webhookSecret" label="Segredo">
                        <Input placeholder="segredo-opcional" />
                      </Form.Item>
                      <Space>
                        <Button type="primary">Salvar</Button>
                        <Switch checkedChildren="Ativo" unCheckedChildren="Inativo" />
                      </Space>
                    </Form>
                  </Card>

                  <Divider />

                  <Card title="Tokens / Credenciais">
                    <Form form={formTokens} layout="vertical">
                      <Form.Item name="tseToken" label="Token TSE (se aplicável)">
                        <Input placeholder="insira seu token, se necessário" />
                      </Form.Item>
                      <Form.Item name="externalApiToken" label="Token API Externa">
                        <Input placeholder="token de outros serviços" />
                      </Form.Item>
                      <Button type="primary">Salvar</Button>
                    </Form>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'evolution',
            label: 'EVOLUTION API',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={10}>
                  <Card title="Evolution API">
                    <Form layout="vertical">
                      <Form.Item label="Chave de Autenticação (mascarada)">
                        <Input value={evoKeyMasked} readOnly />
                      </Form.Item>
                      <Space>
                        <Button type="primary" onClick={testarEvolution}>Testar Evolution API</Button>
                        <Tag color={evoStatus === 'CONECTADO' ? 'green' : (evoStatus === 'TESTANDO' ? 'blue' : 'default')}>EVOLUTION: {evoStatus}</Tag>
                      </Space>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} xl={14}>
                  <Card title="Instâncias">
                    <Table
                      size="small"
                      bordered
                      pagination={false}
                      dataSource={evoInstances || []}
                      rowKey={(r, idx) => String((r as any)?.id ?? idx)}
                      columns={[
                        { title: 'ID', dataIndex: 'id' },
                        { title: 'Nome', dataIndex: 'name' },
                        { title: 'Número', dataIndex: 'number' },
                        { title: 'Token', dataIndex: 'hasToken', render: (v) => <Tag color={v ? 'green' : 'default'}>{v ? 'SIM' : 'NÃO'}</Tag> },
                        { title: 'Status', dataIndex: 'connectionStatus' },
                      ]}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'whatsapp',
            label: 'WHATSAPP API',
            children: (
              <Row gutter={[16, 16]}>
                <Col span={24}>
                  <Card title="WhatsApp API">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>Esta integração usa a Evolution API para envio e consulta.</div>
                      <div>Configure e teste na aba EVOLUTION API.</div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'twilio',
            label: 'TWILIO',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={12}>
                  <Card title="Twilio Messaging - Configuração">
                    <Form
                      form={formTwilio}
                      layout="vertical"
                      initialValues={{
                        enabled: true,
                        enabled_channels: ['sms', 'whatsapp', 'mms'],
                        whatsapp_from: 'whatsapp:+14155238886',
                        inbound_webhook_url: defaultTwilioInboundWebhookUrl,
                        status_callback_url: defaultTwilioStatusCallbackUrl,
                        validate_signature: false,
                      }}
                    >
                      <Divider orientation="left">Credenciais</Divider>
                      <Form.Item name="account_sid" label="Account SID (AC...)" rules={[{ required: true, message: 'Informe o Account SID' }]}>
                        <Input placeholder="Cole o Account SID em Console → Live/Test credentials" />
                      </Form.Item>

                      <Form.Item label="Auth Token do Account (mascarado)">
                        <Input value={twilioTokenMasked || (twilioHasToken ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="auth_token" label="Novo Auth Token do Account (opcional)">
                        <Input.Password placeholder={twilioHasToken ? 'deixe em branco para manter o atual' : 'cole o Auth token em Live/Test credentials'} />
                      </Form.Item>

                      <Form.Item name="api_key_sid" label="API Key SID (SK... opcional)">
                        <Input placeholder="SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
                      </Form.Item>
                      <Form.Item label="API Key Secret (mascarado)">
                        <Input value={twilioApiKeySecretMasked || (twilioHasApiKeySecret ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="api_key_secret" label="Novo API Key Secret (opcional)">
                        <Input.Password placeholder={twilioHasApiKeySecret ? 'deixe em branco para manter o atual' : 'cole o Secret da API Key'} />
                      </Form.Item>

                      <Divider orientation="left">Origem (From)</Divider>
                      <Form.Item
                        name="messaging_service_sid"
                        label="Messaging Service SID (MG... opcional)"
                        extra={<Button onClick={loadTwilioMessagingServices} loading={twilioMessagingServicesLoading}>Atualizar lista</Button>}
                      >
                        <Select
                          allowClear
                          showSearch
                          loading={twilioMessagingServicesLoading}
                          placeholder="Console → Messaging → Services → Service SID (MG...)"
                          options={twilioMessagingServiceOptions as any}
                          onSearch={(v) => setTwilioMessagingServiceSearch(String(v || ''))}
                          filterOption={(input, option) => {
                            const i = String(input || '').toLowerCase()
                            const l = String((option as any)?.label || '').toLowerCase()
                            const v = String((option as any)?.value || '').toLowerCase()
                            return l.includes(i) || v.includes(i)
                          }}
                        />
                      </Form.Item>
                      <Form.Item name="sms_from" label="SMS From (opcional)">
                        <Input placeholder="+15551234567" />
                      </Form.Item>
                      <Form.Item name="whatsapp_from" label="WhatsApp From (opcional)">
                        <Input placeholder="whatsapp:+14155238886" />
                      </Form.Item>

                      <Divider orientation="left">Canais</Divider>
                      <Form.Item name="enabled_channels" label="Canais habilitados">
                        <Checkbox.Group
                          options={[
                            { label: 'SMS', value: 'sms' },
                            { label: 'WhatsApp', value: 'whatsapp' },
                            { label: 'MMS', value: 'mms' },
                            { label: 'RCS', value: 'rcs' },
                            { label: 'Email', value: 'email' },
                            { label: 'Voice', value: 'voice' },
                          ]}
                        />
                      </Form.Item>

                      <Divider orientation="left">Webhooks</Divider>
                      <Form.Item name="inbound_webhook_url" label="Incoming Messages Webhook (URL)">
                        <Input placeholder={defaultTwilioInboundWebhookUrl} />
                      </Form.Item>
                      <Form.Item name="status_callback_url" label="Status Callback (URL)">
                        <Input placeholder={defaultTwilioStatusCallbackUrl} />
                      </Form.Item>
                      <Form.Item name="validate_signature" label="Validar assinatura Twilio" valuePropName="checked">
                        <Switch checkedChildren="Sim" unCheckedChildren="Não" />
                      </Form.Item>

                      <Divider orientation="left">Status</Divider>
                      <Form.Item name="enabled" valuePropName="checked">
                        <Switch checkedChildren="Ativo" unCheckedChildren="Inativo" />
                      </Form.Item>
                      <Space wrap>
                        <Button type="primary" onClick={salvarTwilio}>Salvar</Button>
                        <Button onClick={testarTwilio}>Testar Conexão</Button>
                        <Tag color={twilioStatus === 'CONECTADO' ? 'green' : (twilioStatus === 'TESTANDO' ? 'blue' : 'default')}>TWILIO: {twilioStatus}</Tag>
                      </Space>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} xl={12}>
                  <Space direction="vertical" style={{ width: '100%' }} size={16}>
                    <Card title="Enviar mensagem de teste">
                      <Form form={formTwilioSend} layout="vertical" initialValues={{ channel: 'sms', body: 'Teste CAPTAR', status_callback_url_override: defaultTwilioStatusCallbackUrl }}>
                        <Form.Item name="channel" label="Canal">
                          <Select
                            options={[
                              { label: 'SMS', value: 'sms' },
                              { label: 'WhatsApp', value: 'whatsapp' },
                              { label: 'MMS', value: 'mms' },
                            ]}
                          />
                        </Form.Item>
                        <Form.Item name="to" label="Para (to)" rules={[{ required: true, message: 'Informe o destino' }]}>
                          <Input placeholder="+5511999999999 ou whatsapp:+5511999999999" />
                        </Form.Item>
                        <Form.Item name="body" label="Mensagem">
                          <Input.TextArea rows={4} placeholder="Digite a mensagem" />
                        </Form.Item>
                        <Form.Item name="content_sid" label="Content SID (opcional)">
                          <Input placeholder="HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
                        </Form.Item>
                        <Form.Item name="content_variables" label="Content Variables (opcional)">
                          <Input.TextArea rows={3} placeholder='{"1":"12/1","2":"3pm"}' />
                        </Form.Item>
                        <Form.Item
                          name="attachments"
                          label="Anexos (upload)"
                          valuePropName="fileList"
                          getValueFromEvent={(e) => e?.fileList || []}
                        >
                          <Upload
                            multiple
                            customRequest={twilioUploadRequest}
                            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.mp3,.wav,.ogg,.m4a,.mp4,.mov,.avi"
                          >
                            <Button>Selecionar arquivos</Button>
                          </Upload>
                        </Form.Item>
                        <Form.Item name="media_urls" label="Media URLs (opcional)">
                          <Input.TextArea rows={2} placeholder="Uma URL por linha (MMS/WhatsApp)" />
                        </Form.Item>
                        <Form.Item name="from_override" label="From (override opcional)">
                          <Input placeholder="Use apenas se não estiver usando Messaging Service" />
                        </Form.Item>
                        <Form.Item name="status_callback_url_override" label="Status Callback (override opcional)">
                          <Input placeholder={defaultTwilioStatusCallbackUrl} />
                        </Form.Item>
                        <Button type="primary" onClick={enviarTwilioTeste}>Enviar</Button>
                      </Form>
                    </Card>
                    <Card title="Opt-in (Twilio WhatsApp)">
                      <Form form={formTwilioOptin} layout="vertical" initialValues={{ source: 'manual' }}>
                        <Form.Item
                          name="numbers"
                          label="Números"
                          rules={[{ required: true, message: 'Informe ao menos um número' }]}
                          extra="Separe por espaço, vírgula, ponto e vírgula ou quebra de linha"
                        >
                          <Input.TextArea rows={4} placeholder="+5592988557788 whatsapp:+5592988557788 5592981497639" />
                        </Form.Item>
                        <Form.Item name="source" label="Origem (opcional)">
                          <Input placeholder="Ex: manual, importação, cliente antigo" />
                        </Form.Item>
                        <Space wrap>
                          <Button type="primary" onClick={() => registrarTwilioOptin(true)} loading={twilioOptinLoading}>Registrar Opt-in</Button>
                          <Button danger onClick={() => registrarTwilioOptin(false)} loading={twilioOptinLoading}>Registrar Opt-out</Button>
                          <Button onClick={consultarTwilioOptin} loading={twilioOptinLoading}>Consultar</Button>
                        </Space>
                        <Divider />
                        <Table
                          size="small"
                          bordered
                          pagination={false}
                          dataSource={twilioOptinItems || []}
                          rowKey={(r) => String((r as any)?.number || '')}
                          columns={[
                            { title: 'Número', dataIndex: 'number' },
                            { title: 'Status', dataIndex: 'status' },
                            { title: 'Opt-in', dataIndex: 'opted_in', render: (v) => <Tag color={v ? 'green' : 'default'}>{v ? 'SIM' : 'NÃO'}</Tag> },
                          ]}
                        />
                      </Form>
                    </Card>
                    <Card title="Notas">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <div>Account SID e Auth Token ficam em Console → API keys & tokens → Live/Test credentials.</div>
                        <div>API Key (SK...) é alternativa ao Auth Token. Informe SID e Secret.</div>
                        <div>Messaging Service SID (MG...) fica em Console → Messaging → Services.</div>
                        <div>Para WhatsApp, use destino no formato <Tag>whatsapp:+5511999999999</Tag>.</div>
                        <div>Para envio via WhatsApp/Twilio, o sistema exige opt-in por número. Use o card Opt-in para cadastrar antes de enviar.</div>
                      </Space>
                    </Card>
                  </Space>
                </Col>
              </Row>
            ),
          },
          {
            key: 'meta',
            label: 'META CLOUD API',
            children: (
              <Tabs
                defaultActiveKey="config"
                onChange={async (k) => {
                  if (k === 'stats') await carregarMetaStats()
                }}
                items={[
                  {
                    key: 'config',
                    label: 'CONFIGURAÇÃO',
                    children: (
                      <>
                        <Row gutter={[16, 16]}>
                          <Col xs={24} xl={24}>
                            <Card title="Meta Cloud API - Perfis">
                              <Space wrap style={{ marginBottom: 12 }}>
                                <Button type="primary" onClick={abrirNovoPerfilMeta}>NOVA CONEXÃO META CLOUD API</Button>
                                <Button onClick={() => carregarListaMetaPerfis()} loading={metaProfilesLoading}>Atualizar lista</Button>
                                <Button onClick={() => abrirEdicaoPerfilMeta(metaConfigId)} disabled={!metaConfigId}>Editar selecionado</Button>
                                <Button onClick={testarMeta} disabled={!metaConfigId}>Testar conexão</Button>
                                <Tag color={metaStatus === 'CONECTADO' ? 'green' : (metaStatus === 'TESTANDO' ? 'blue' : 'default')}>META: {metaStatus}</Tag>
                              </Space>

                              <Table
                                size="small"
                                bordered
                                loading={metaProfilesLoading}
                                dataSource={metaProfiles || []}
                                rowKey="id"
                                pagination={{ pageSize: 10 }}
                                columns={[
                                  { title: 'Perfil', dataIndex: 'perfil' },
                                  { title: 'WhatsApp Phone', dataIndex: 'whatsapp_phone' },
                                  { title: 'WABA ID', dataIndex: 'business_account_id' },
                                  { title: 'PhoneID', dataIndex: 'phone_number_id' },
                                  { title: 'Status', dataIndex: 'enabled', render: (v: any) => <Tag color={v ? 'green' : 'red'}>{v ? 'ATIVO' : 'INATIVO'}</Tag> },
                                  {
                                    title: 'Ações',
                                    render: (_: any, record: any) => (
                                      <Space wrap>
                                        <Button type={Number(record?.id || 0) === Number(metaConfigId || 0) ? 'primary' : 'default'} onClick={() => setMetaConfigId(Number(record?.id || 0))}>Selecionar</Button>
                                        <Button onClick={() => abrirEdicaoPerfilMeta(Number(record?.id || 0))}>Editar</Button>
                                        <Button danger onClick={() => excluirPerfilMeta(Number(record?.id || 0))}>Excluir</Button>
                                      </Space>
                                    ),
                                  },
                                ]}
                              />

                              <Divider orientation="left">Webhook URL (perfil selecionado)</Divider>
                              <Input value={defaultMetaWebhookUrl} readOnly />
                            </Card>
                          </Col>
                        </Row>

                        <Row gutter={[16, 16]}>
                          <Col xs={24} xl={12}>
                            <Card title="Webhooks - Overrides">
                              <Form
                                form={formMetaWebhook}
                                layout="vertical"
                                initialValues={{
                                  phone_number_id: '',
                                  waba_id: '',
                                  override_callback_uri: '',
                                  verify_token: '',
                                }}
                              >
                                <Form.Item name="phone_number_id" label="Phone Number ID">
                                  <Input placeholder="(deixe em branco para usar o do perfil selecionado)" />
                                </Form.Item>
                                <Form.Item name="waba_id" label="WABA ID (Business Account ID)">
                                  <Input placeholder="(deixe em branco para usar o do perfil selecionado)" />
                                </Form.Item>
                                <Form.Item name="override_callback_uri" label="Override Callback URL">
                                  <Input placeholder={defaultMetaWebhookUrl || 'https://...'} />
                                </Form.Item>
                                <Form.Item name="verify_token" label="Verify Token (override)">
                                  <Input.Password placeholder="use o token definido no override" />
                                </Form.Item>

                                <Space wrap>
                                  <Button onClick={() => metaWebhookApplyPhone(true)} loading={metaWebhookLoading}>Aplicar no Phone</Button>
                                  <Button onClick={() => metaWebhookApplyPhone(false)} loading={metaWebhookLoading}>Remover do Phone</Button>
                                  <Button onClick={() => metaWebhookApplyWaba(true)} loading={metaWebhookLoading}>Aplicar no WABA</Button>
                                  <Button onClick={() => metaWebhookApplyWaba(false)} loading={metaWebhookLoading}>Remover do WABA</Button>
                                </Space>

                                <Divider />
                                <Space wrap>
                                  <Button onClick={metaWebhookLoadStatus} loading={metaWebhookLoading}>Consultar status (Phone)</Button>
                                  <Button onClick={metaWebhookLoadSubscribedApps} loading={metaWebhookLoading}>Consultar subscribed_apps (WABA)</Button>
                                </Space>

                                <Divider orientation="left">Resposta (Status)</Divider>
                                <Input.TextArea value={metaWebhookStatusText} readOnly autoSize={{ minRows: 6, maxRows: 16 }} />
                                <Divider orientation="left">Resposta (Subscribed Apps)</Divider>
                                <Input.TextArea value={metaWebhookSubscribedText} readOnly autoSize={{ minRows: 6, maxRows: 16 }} />
                              </Form>
                            </Card>
                          </Col>
                          <Col xs={24} xl={12}>
                            <Card title="Notas">
                              <Space direction="vertical" style={{ width: '100%' }}>
                                <div>O callback do webhook é validado via Verify Token e pode validar assinatura via App Secret.</div>
                                <div>O endpoint de webhook precisa estar em HTTPS com certificado válido (sem self-signed) para produção.</div>
                              </Space>
                            </Card>
                          </Col>
                        </Row>

                        <MetaCloudAPIModal
                          open={metaModalOpen}
                          initial={metaModalInitial}
                          onCancel={() => setMetaModalOpen(false)}
                          onSaved={async () => {
                            await carregarListaMetaPerfis()
                            try { await carregarMetaConfig(metaConfigId) } catch {}
                          }}
                        />
                      </>
                    ),
                  },
                  {
                    key: 'test',
                    label: 'TESTE',
                    children: (
                      <Row gutter={[16, 16]}>
                        <Col xs={24} xl={12}>
                          <Card title="Enviar mensagem de teste">
                            <Form form={formMetaSend} layout="vertical" initialValues={{ text_position: 'bottom', body: 'Teste CAPTAR' }}>
                              <Form.Item name="to" label="Para (to)" rules={[{ required: true, message: 'Informe o destino' }]}>
                                <Input placeholder="+5511999999999" />
                              </Form.Item>
                              <Divider orientation="left">Template (opcional)</Divider>
                              <Form.Item name="template_name" label="Template Name">
                                <Input placeholder="ex: ola_captar" />
                              </Form.Item>
                              <Form.Item name="template_lang" label="Template Language">
                                <Input placeholder="pt_BR" />
                              </Form.Item>
                              <Form.Item name="template_components" label="Template Components (JSON array, opcional)">
                                <Input.TextArea rows={4} placeholder='[{"type":"body","parameters":[{"type":"text","text":"João"}]}]' />
                              </Form.Item>
                              <Divider orientation="left">Texto/Mídia (se não for template)</Divider>
                              <Form.Item name="body" label="Mensagem">
                                <Input.TextArea rows={4} placeholder="Digite a mensagem" />
                              </Form.Item>
                              <Form.Item name="text_position" label="Posição do texto">
                                <Select options={[{ label: 'Acima da mídia', value: 'top' }, { label: 'Abaixo da mídia', value: 'bottom' }]} />
                              </Form.Item>
                              <Form.Item
                                name="attachments"
                                label="Anexo (upload)"
                                valuePropName="fileList"
                                getValueFromEvent={(e) => e?.fileList || []}
                              >
                                <Upload
                                  multiple={false}
                                  customRequest={metaUploadRequest}
                                  accept=".png,.jpg,.jpeg,.gif,.webp"
                                >
                                  <Button>Selecionar imagem</Button>
                                </Upload>
                              </Form.Item>
                              <Form.Item name="media_url" label="Media URL (opcional)">
                                <Input placeholder="https://..." />
                              </Form.Item>
                              <Button type="primary" onClick={enviarMetaTeste}>Enviar</Button>
                            </Form>
                          </Card>
                        </Col>
                        <Col xs={24} xl={12}>
                          <Card title="Testes rápidos">
                            <Space wrap>
                              <Button onClick={testarMeta}>Testar Conexão</Button>
                              <Tag color={metaStatus === 'CONECTADO' ? 'green' : (metaStatus === 'TESTANDO' ? 'blue' : 'default')}>META: {metaStatus}</Tag>
                            </Space>
                          </Card>
                        </Col>
                      </Row>
                    ),
                  },
                  {
                    key: 'embedded',
                    label: 'EMBEDDED SIGNUP',
                    children: (
                      <Row gutter={[16, 16]}>
                        <Col xs={24} xl={12}>
                          <Card title="Iniciar Embedded Signup">
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <Tag color={metaFbLoaded ? 'green' : 'default'}>FB SDK: {metaFbLoaded ? 'CARREGADO' : 'NÃO CARREGADO'}</Tag>
                              <Button type="primary" onClick={iniciarEmbeddedSignup} loading={metaEmbeddedLoading}>
                                Iniciar Embedded Signup
                              </Button>
                              <Divider />
                              <div style={{ fontWeight: 600 }}>Code (response_type=code)</div>
                              <Input
                                value={metaEmbeddedCode}
                                onChange={(e) => setMetaEmbeddedCode(e.target.value)}
                                placeholder="Cole aqui o code, se necessário"
                              />
                              <Space wrap>
                                <Button onClick={trocarCodePorToken} loading={metaEmbeddedLoading}>Trocar code por token</Button>
                              </Space>
                            </Space>
                          </Card>
                        </Col>
                        <Col xs={24} xl={12}>
                          <Card title="Resposta do Facebook (sessão)">
                            <Input.TextArea value={metaEmbeddedSessionText} readOnly autoSize={{ minRows: 10, maxRows: 18 }} />
                          </Card>
                          <Card title="Resposta do backend (exchange)" style={{ marginTop: 16 }}>
                            <Input.TextArea value={metaEmbeddedResultText} readOnly autoSize={{ minRows: 10, maxRows: 18 }} />
                          </Card>
                        </Col>
                      </Row>
                    ),
                  },
                  {
                    key: 'templates',
                    label: 'TEMPLATES',
                    children: (
                      <Row gutter={[16, 16]}>
                        <Col xs={24} xl={12}>
                          <Card title="Criar template (category=MARKETING/UTILITY/AUTHENTICATION)">
                            <Form
                              form={formMetaTemplate}
                              layout="vertical"
                              initialValues={{ language: 'pt_BR', category: 'UTILITY' }}
                            >
                              <Form.Item name="template_name" label="Template Name" rules={[{ required: true, message: 'Informe o nome' }]}>
                                <Input placeholder="ex: ola_captar" />
                              </Form.Item>
                              <Form.Item name="language" label="Language">
                                <Input placeholder="pt_BR" />
                              </Form.Item>
                              <Form.Item name="category" label="Category">
                                <Select
                                  options={[
                                    { label: 'UTILITY', value: 'UTILITY' },
                                    { label: 'MARKETING', value: 'MARKETING' },
                                    { label: 'AUTHENTICATION', value: 'AUTHENTICATION' },
                                  ]}
                                />
                              </Form.Item>
                              <Form.Item name="body_text" label="Body Text" rules={[{ required: true, message: 'Informe o texto' }]}>
                                <Input.TextArea rows={6} placeholder="Conteúdo do template" />
                              </Form.Item>
                              <Button type="primary" onClick={criarMetaTemplate} loading={metaTemplatesLoading}>Criar</Button>
                            </Form>
                          </Card>
                        </Col>
                        <Col xs={24} xl={12}>
                          <Card title="Listar templates">
                            <Form form={formMetaTemplateList} layout="vertical" initialValues={{ limit: 50 }}>
                              <Form.Item name="waba_id" label="WABA ID (opcional)">
                                <Input placeholder="(deixe em branco para usar o configurado)" />
                              </Form.Item>
                              <Form.Item name="name" label="Filtrar por nome (opcional)">
                                <Input placeholder="ex: ola_captar" />
                              </Form.Item>
                              <Form.Item name="status" label="Status (opcional)">
                                <Select
                                  allowClear
                                  options={[
                                    { label: 'APPROVED', value: 'APPROVED' },
                                    { label: 'PENDING', value: 'PENDING' },
                                    { label: 'REJECTED', value: 'REJECTED' },
                                    { label: 'PAUSED', value: 'PAUSED' },
                                  ]}
                                />
                              </Form.Item>
                              <Form.Item name="limit" label="Limit">
                                <InputNumber min={1} max={250} style={{ width: '100%' }} />
                              </Form.Item>
                              <Space wrap>
                                <Button type="primary" onClick={listarMetaTemplates} loading={metaTemplatesLoading}>Listar</Button>
                              </Space>
                            </Form>
                          </Card>
                          <Card title="Resposta" style={{ marginTop: 16 }} loading={metaTemplatesLoading}>
                            <Input.TextArea value={metaTemplatesText} readOnly autoSize={{ minRows: 14, maxRows: 24 }} />
                          </Card>
                        </Col>
                      </Row>
                    ),
                  },
                  {
                    key: 'stats',
                    label: 'ESTATÍSTICAS',
                    children: (
                      <Row gutter={[16, 16]}>
                        <Col xs={24} xl={8}>
                          <Card title="Filtros">
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <div>
                                <div style={{ marginBottom: 6 }}>Período</div>
                                <Select
                                  style={{ width: '100%' }}
                                  value={metaStatsDays}
                                  options={[
                                    { label: '7 dias', value: 7 },
                                    { label: '14 dias', value: 14 },
                                    { label: '30 dias', value: 30 },
                                    { label: '60 dias', value: 60 },
                                    { label: '90 dias', value: 90 },
                                  ]}
                                  onChange={async (v) => { setMetaStatsDays(v); await carregarMetaStats(v) }}
                                />
                              </div>
                              <div>
                                <div style={{ marginBottom: 6 }}>Métrica</div>
                                <Select
                                  style={{ width: '100%' }}
                                  value={metaStatsMetric}
                                  options={[
                                    { label: 'Total', value: 'total' },
                                    { label: 'Enviados', value: 'sent' },
                                    { label: 'Entregues', value: 'delivered' },
                                    { label: 'Visualizados', value: 'read' },
                                    { label: 'Falhas', value: 'failed' },
                                  ]}
                                  onChange={(v) => setMetaStatsMetric(v)}
                                />
                              </div>
                              <Button onClick={() => carregarMetaStats()} loading={metaStatsLoading}>Atualizar</Button>
                            </Space>
                          </Card>
                        </Col>
                        <Col xs={24} xl={16}>
                          <Card title="Mensagens por dia" loading={metaStatsLoading}>
                            {Array.isArray(metaStatsRows) && metaStatsRows.length ? (
                              <ChartComponent data={metaStatsRows} type="bar" xField="date" yField={metaStatsMetric} />
                            ) : (
                              <div>Nenhum dado no período</div>
                            )}
                            <Divider />
                            <Table
                              size="small"
                              bordered
                              pagination={false}
                              dataSource={metaStatsRows || []}
                              rowKey={(r) => String((r as any)?.date || '')}
                              columns={[
                                { title: 'Dia', dataIndex: 'date' },
                                { title: 'Enviados', dataIndex: 'sent' },
                                { title: 'Entregues', dataIndex: 'delivered' },
                                { title: 'Visualizados', dataIndex: 'read' },
                                { title: 'Falhas', dataIndex: 'failed' },
                                { title: 'Total', dataIndex: 'total' },
                              ]}
                            />
                          </Card>
                        </Col>
                      </Row>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'ycloud',
            label: 'YCLOUD',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={12}>
                  <Card title="YCloud - Configuração">
                    <Form form={formYCloud} layout="vertical" initialValues={{ enabled: true }}>
                      <Form.Item name="base_url" label="Base URL (opcional)">
                        <Input placeholder="https://..." />
                      </Form.Item>
                      <Form.Item name="phone_number_id" label="Phone Number ID (opcional)">
                        <Input placeholder="Ex: 123456789012345" />
                      </Form.Item>
                      <Form.Item name="business_account_id" label="WABA (Business Account ID) (opcional)">
                        <Input placeholder="Ex: 123456789012345" />
                      </Form.Item>
                      <Divider orientation="left">Credenciais</Divider>
                      <Form.Item label="API Key (mascarada)">
                        <Input value={ycloudApiKeyMasked || (ycloudHasApiKey ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="api_key" label="Nova API Key (opcional)">
                        <Input.Password placeholder={ycloudHasApiKey ? 'deixe em branco para manter a atual' : 'cole a API key'} />
                      </Form.Item>
                      <Form.Item label="Webhook Verify Token (mascarado)">
                        <Input value={ycloudVerifyTokenMasked || (ycloudHasVerifyToken ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="webhook_verify_token" label="Novo Webhook Verify Token (opcional)">
                        <Input.Password placeholder={ycloudHasVerifyToken ? 'deixe em branco para manter o atual' : 'cole o verify token'} />
                      </Form.Item>
                      <Divider orientation="left">Status</Divider>
                      <Form.Item name="enabled" valuePropName="checked">
                        <Switch checkedChildren="Ativo" unCheckedChildren="Inativo" />
                      </Form.Item>
                      <Button type="primary" onClick={salvarYCloud}>Salvar</Button>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} xl={12}>
                  <Card title="Notas">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>Use este formulário para guardar credenciais de um provedor WhatsApp Cloud.</div>
                      <div>O envio ainda depende do provedor selecionado em Campanhas.</div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'dialog360',
            label: '360DIALOG',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={12}>
                  <Card title="360dialog - Configuração">
                    <Form form={formDialog360} layout="vertical" initialValues={{ enabled: true }}>
                      <Form.Item name="base_url" label="Base URL (opcional)">
                        <Input placeholder="https://..." />
                      </Form.Item>
                      <Form.Item name="phone_number_id" label="Phone Number ID (opcional)">
                        <Input placeholder="Ex: 123456789012345" />
                      </Form.Item>
                      <Form.Item name="business_account_id" label="WABA (Business Account ID) (opcional)">
                        <Input placeholder="Ex: 123456789012345" />
                      </Form.Item>
                      <Divider orientation="left">Credenciais</Divider>
                      <Form.Item label="API Key (mascarada)">
                        <Input value={dialog360ApiKeyMasked || (dialog360HasApiKey ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="api_key" label="Nova API Key (opcional)">
                        <Input.Password placeholder={dialog360HasApiKey ? 'deixe em branco para manter a atual' : 'cole a API key'} />
                      </Form.Item>
                      <Form.Item label="Webhook Verify Token (mascarado)">
                        <Input value={dialog360VerifyTokenMasked || (dialog360HasVerifyToken ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="webhook_verify_token" label="Novo Webhook Verify Token (opcional)">
                        <Input.Password placeholder={dialog360HasVerifyToken ? 'deixe em branco para manter o atual' : 'cole o verify token'} />
                      </Form.Item>
                      <Divider orientation="left">Status</Divider>
                      <Form.Item name="enabled" valuePropName="checked">
                        <Switch checkedChildren="Ativo" unCheckedChildren="Inativo" />
                      </Form.Item>
                      <Button type="primary" onClick={salvarDialog360}>Salvar</Button>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} xl={12}>
                  <Card title="Notas">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>360dialog é um BSP para WhatsApp Business API.</div>
                      <div>Guarde aqui as credenciais para uso futuro no backend.</div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'wanotifier',
            label: 'WANOTIFIER',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={12}>
                  <Card title="WANotifier - Configuração">
                    <Form form={formWANotifier} layout="vertical" initialValues={{ enabled: true }}>
                      <Form.Item name="base_url" label="Base URL (opcional)">
                        <Input placeholder="https://..." />
                      </Form.Item>
                      <Form.Item name="phone_number_id" label="Phone Number ID (opcional)">
                        <Input placeholder="Ex: 123456789012345" />
                      </Form.Item>
                      <Form.Item name="business_account_id" label="WABA (Business Account ID) (opcional)">
                        <Input placeholder="Ex: 123456789012345" />
                      </Form.Item>
                      <Divider orientation="left">Credenciais</Divider>
                      <Form.Item label="API Key (mascarada)">
                        <Input value={wanotifierApiKeyMasked || (wanotifierHasApiKey ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="api_key" label="Nova API Key (opcional)">
                        <Input.Password placeholder={wanotifierHasApiKey ? 'deixe em branco para manter a atual' : 'cole a API key'} />
                      </Form.Item>
                      <Form.Item label="Webhook Verify Token (mascarado)">
                        <Input value={wanotifierVerifyTokenMasked || (wanotifierHasVerifyToken ? '********' : '')} readOnly />
                      </Form.Item>
                      <Form.Item name="webhook_verify_token" label="Novo Webhook Verify Token (opcional)">
                        <Input.Password placeholder={wanotifierHasVerifyToken ? 'deixe em branco para manter o atual' : 'cole o verify token'} />
                      </Form.Item>
                      <Divider orientation="left">Status</Divider>
                      <Form.Item name="enabled" valuePropName="checked">
                        <Switch checkedChildren="Ativo" unCheckedChildren="Inativo" />
                      </Form.Item>
                      <Button type="primary" onClick={salvarWANotifier}>Salvar</Button>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} xl={12}>
                  <Card title="Notas">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>WANotifier pode ser usado como camada de automação/conectores.</div>
                      <div>Configure aqui as credenciais para uso nas automações.</div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'n8n',
            label: 'N8N',
            children: (
              <Row gutter={[16, 16]}>
                <Col span={24}>
                  <Card title="N8N">
                    <div>Em breve.</div>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'chatwoot',
            label: 'CHATWOOT',
            children: (
              <Row gutter={[16, 16]}>
                <Col span={24}>
                  <Card title="Chatwoot">
                    <div>Em breve.</div>
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </motion.div>
  )
}
