import { motion } from 'framer-motion'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { Table, Button, Space, Dropdown, Checkbox, Tag, Card, Statistic, Image, List, Row, Col, Tooltip, App, Select } from 'antd'
import { TeamOutlined, CheckCircleOutlined, ExclamationCircleOutlined, SyncOutlined, SendOutlined, PictureOutlined, WhatsAppOutlined, CheckCircleFilled, CloseCircleFilled, ClockCircleFilled, RightOutlined, ReloadOutlined } from '@ant-design/icons'
import { useAuthStore } from '../../store/authStore'
import { useApi } from '../../context/ApiContext'
import CampanhasModal from '../../components/CampanhasModal'
import dayjs from 'dayjs'

export default function Campanha() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [columnsMeta, setColumnsMeta] = useState<{ name: string; type: string; nullable: boolean; maxLength?: number }[]>([])
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({})
  const [orderedKeys, setOrderedKeys] = useState<string[]>([])
  const [selectedRowKeys, setSelectedRowKeys] = useState<any[]>([])
  
  // New states for the enriched view
  const [eventLogs, setEventLogs] = useState<string[]>([])
  const [contactStatuses, setContactStatuses] = useState<any[]>([])
  const [evolutionInstances, setEvolutionInstances] = useState<any[]>([])
  const [selectedEvolutionInstanceId, setSelectedEvolutionInstanceId] = useState<string | 'ALL' | null>(null)

  const api = useApi()
  const { user } = useAuthStore()
  const { message, modal } = App.useApp()

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

  const selectedCampanha = useMemo(() => {
      if (selectedRowKeys.length !== 1) return null
      return data.find(r => r.id === selectedRowKeys[0])
  }, [selectedRowKeys, data])

  const selectedCampanhaConfig = useMemo(() => {
    const raw = selectedCampanha?.conteudo_arquivo
    if (!raw) return {}
    try {
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        const cfg = (parsed as any).config
        if (cfg && typeof cfg === 'object') return cfg
      }
    } catch {}
    return {}
  }, [api, selectedCampanha?.id, selectedCampanha?.conteudo_arquivo])

  const eventLogsKey = useMemo(() => {
    if (!selectedCampanha?.id) return null
    const u = String((user as any)?.usuario || 'default')
    return `campanhas.eventLogs.${u}.${Number(selectedCampanha.id)}`
  }, [selectedCampanha?.id, (user as any)?.usuario])

  useEffect(() => {
    if (!eventLogsKey) {
      setEventLogs([])
      return
    }
    try {
      const raw = localStorage.getItem(eventLogsKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
          setEventLogs(parsed.map((x: any) => String(x)))
          return
        }
      }
    } catch {}
    setEventLogs([`[${dayjs().format('HH:mm:ss')}] Sistema pronto. Aguardando início do disparo.`])
  }, [eventLogsKey])

  useEffect(() => {
    if (!eventLogsKey) return
    try {
      localStorage.setItem(eventLogsKey, JSON.stringify((eventLogs || []).slice(-2000)))
    } catch {}
  }, [eventLogsKey, eventLogs])

  const loadEvolutionInstances = useCallback(async () => {
    try {
      const res = await api.listEvolutionInstances()
      setEvolutionInstances(res?.rows || [])
    } catch {
      setEvolutionInstances([])
    }
  }, [api])

  useEffect(() => {
    loadEvolutionInstances()
  }, [loadEvolutionInstances])

  const availableEvolutionInstances = useMemo(() => {
    const cfg = selectedCampanhaConfig || {}
    const rawIds = (cfg as any).evolution_api_ids ?? (cfg as any).evolution_api_id
    const allowedIds = (Array.isArray(rawIds) ? rawIds : (rawIds !== undefined && rawIds !== null ? [rawIds] : []))
      .map((x: any) => String(x ?? '').trim())
      .filter((s: any) => !!s)
    const all = evolutionInstances || []
    if (!allowedIds.length) return all
    const setAllowed = new Set(allowedIds)
    const filtered = all.filter((x: any) => setAllowed.has(String(x?.id ?? '').trim()))
    return filtered.length ? filtered : all
  }, [evolutionInstances, selectedCampanhaConfig])

  useEffect(() => {
    if (!selectedCampanha) {
      setSelectedEvolutionInstanceId(null)
      return
    }
    if (!availableEvolutionInstances.length) {
      setSelectedEvolutionInstanceId(null)
      return
    }
    const cur = selectedEvolutionInstanceId
    if (cur === 'ALL') return
    if (typeof cur === 'string' && availableEvolutionInstances.some((x: any) => String(x?.id ?? '').trim() === cur)) return
    const connected = availableEvolutionInstances.find((x: any) => String(x?.connectionStatus || '').toUpperCase() === 'CONNECTED')
    setSelectedEvolutionInstanceId(String((connected || availableEvolutionInstances[0])?.id ?? '').trim() || null)
  }, [availableEvolutionInstances, selectedCampanha?.id, selectedEvolutionInstanceId, selectedCampanha])

  // Handle selection change and load real data
  useEffect(() => {
    if (selectedCampanha) {
        let contacts: any[] = []

        const parseResposta = (v: any) => {
            const s = String(v ?? '').trim()
            if (!s) return null
            if (s === '1' || s === '2') return Number(s)
            const low = s.toLowerCase()
            if (/\bsim\b/.test(low) || low === 's') return 1
            if (/\bnao\b/.test(low) || /\bnão\b/.test(low) || low === 'n') return 2
            if (/^\(?\s*1\b/.test(low)) return 1
            if (/^\(?\s*2\b/.test(low)) return 2
            return null
        }

        const parseBool = (v: any): boolean | null => {
            if (v === true || v === false) return v
            const s = String(v ?? '').trim().toLowerCase()
            if (!s) return null
            if (s === 'true' || s === '1' || s === 'sim' || s === 's' || s === 'valido' || s === 'válido') return true
            if (s === 'false' || s === '0' || s === 'nao' || s === 'não' || s === 'n' || s === 'invalido' || s === 'inválido') return false
            return null
        }

        const findVal = (obj: any, keys: string[]) => {
            if (!obj) return ''
            const objKeys = Object.keys(obj)
            for (const k of keys) {
                const found = objKeys.find(ok => ok.trim().toLowerCase() === k.trim().toLowerCase())
                if (found) {
                    const val = obj[found]
                    if (val === undefined || val === null) continue
                    if (typeof val === 'string' && !val.trim()) continue
                    return val
                }
            }
            return ''
        }

        if (selectedCampanha.conteudo_arquivo) {
            try {
                const parsed = JSON.parse(selectedCampanha.conteudo_arquivo)
                if (Array.isArray(parsed)) {
                    contacts = parsed
                } else if (parsed.contacts && Array.isArray(parsed.contacts)) {
                    // New Format
                    contacts = parsed.contacts
                }

                if (contacts.length > 0) {
                    contacts = contacts.map((row: any, idx: number) => {
                        // Try to find phone number
                        const phone = findVal(row, ['whatsapp', 'celular', 'telefone', 'phone', 'mobile', 'tel'])
                        // Try to find name
                        const name = findVal(row, ['nome', 'name', 'cliente', 'full_name', 'fullname']) || `Contato ${idx + 1}`
                        const respRaw = findVal(row, ['resposta', 'response', 'respondido', 'reply'])
                        const resposta = parseResposta(respRaw)
                        const isWhatsapp = parseBool(findVal(row, ['is_whatsapp', 'isWhatsapp', 'whatsapp_valido', 'whatsappValido']))
                        const whatsappJid = findVal(row, ['whatsapp_jid', 'whatsappJid', 'jid'])
                        
                        return {
                            id: idx,
                            nome: name,
                            whatsapp: phone,
                            status: row.status || 'waiting',
                            resposta,
                            is_whatsapp: isWhatsapp === null ? undefined : isWhatsapp,
                            whatsapp_jid: whatsappJid ? String(whatsappJid) : undefined,
                            original: row
                        }
                    }).filter(c => c.whatsapp) // Filter out those without phone

                    const digitsOnly = (v: any) => String(v ?? '').replace(/\D/g, '')
                    const freq = new Map<string, number>()
                    for (const c of contacts) {
                      const d = digitsOnly((c as any).whatsapp)
                      if (!d) continue
                      freq.set(d, (freq.get(d) || 0) + 1)
                    }
                    const seen = new Set<string>()
                    let excluidos = 0
                    let duplicadosDistintos = 0
                    for (const c of freq.values()) {
                      if (c > 1) {
                        duplicadosDistintos++
                        excluidos += (c - 1)
                      }
                    }
                    contacts = contacts
                      .map((c: any) => ({ ...c, whatsapp: digitsOnly(c.whatsapp) }))
                      .filter((c: any) => !!String(c.whatsapp || '').trim())
                      .filter((c: any) => {
                        const d = String(c.whatsapp)
                        if (!d) return false
                        if (seen.has(d)) return false
                        seen.add(d)
                        return true
                      })

                    if (duplicadosDistintos > 0 || excluidos > 0) {
                      setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] LISTA: ${duplicadosDistintos} número(s) repetido(s), ${excluidos} registro(s) não entrarão. Válidos: ${contacts.length}.`])
                    }
                    
                    if (contacts.length === 0) {
                         setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] ERRO: Nenhum contato com 'whatsapp' encontrado.`])
                    }
                }
            } catch (e) {
                console.error("Erro ao fazer parse do conteudo_arquivo", e)
                setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] ERRO: Não foi possível ler o arquivo de contatos.`])
            }
        } else if (selectedCampanha.usar_eleitores) {
             setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] INFO: Esta campanha utiliza a base de Eleitores. Visualização individual não carregada para performance.`])
             // Here we could fetch a sample if needed, but for now leave empty or show a placeholder
             contacts = [] 
        }

        if (contacts.length === 0 && !selectedCampanha.usar_eleitores) {
             setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] AVISO: Nenhum contato válido encontrado no arquivo.`])
        }

        setContactStatuses(contacts)

        let cancelled = false
        ;(async () => {
            try {
                if (!contacts.length) return
                const digitsOnly = (v: any) => String(v ?? '').replace(/\D/g, '')
                const numbers = Array.from(new Set(contacts.map(c => digitsOnly(c.whatsapp)).filter(Boolean)))
                if (!numbers.length) return

                const [waRes, presRes] = await Promise.allSettled([
                    api.whatsappCheckNumbers({ numbers }),
                    api.whatsappPresenceCache({ numbers }),
                ])

                const waByNumber = new Map<string, { is_whatsapp: boolean; jid?: string | null }>()
                if (waRes.status === 'fulfilled') {
                    for (const r of waRes.value?.rows || []) {
                        const d = digitsOnly((r as any).number)
                        if (!d) continue
                        waByNumber.set(d, { is_whatsapp: !!(r as any).is_whatsapp, jid: (r as any).jid ?? null })
                    }
                }

                const presByNumber = new Map<string, string | null>()
                if (presRes.status === 'fulfilled') {
                    for (const r of presRes.value?.rows || []) {
                        const d = digitsOnly((r as any).number)
                        if (!d) continue
                        const p = (r as any).presence
                        presByNumber.set(d, p ? String(p) : null)
                    }
                }

                if (cancelled) return
                setContactStatuses(prev => prev.map((c: any) => {
                    const d = digitsOnly(c.whatsapp)
                    const wa = waByNumber.get(d)
                    const pres = presByNumber.get(d)
                    const nextOriginal = { ...(c.original || {}) } as any
                    if (wa) {
                        nextOriginal.is_whatsapp = wa.is_whatsapp
                        nextOriginal.whatsapp_jid = wa.jid ?? null
                    }
                    return {
                        ...c,
                        is_whatsapp: wa ? wa.is_whatsapp : c.is_whatsapp,
                        whatsapp_jid: wa ? (wa.jid ?? null) : c.whatsapp_jid,
                        presence: pres !== undefined ? pres : c.presence,
                        original: nextOriginal,
                    }
                }))
            } catch {
            }
        })()
        return () => { cancelled = true }
    } else {
        setContactStatuses([])
        return undefined
    }
  }, [api, selectedCampanha?.id, selectedCampanha?.conteudo_arquivo])

  const canSend = useMemo(() => {
      if (!selectedCampanha) return false
      const start = selectedCampanha.data_inicio
      const end = selectedCampanha.data_fim
      if (!start) return false
      
      const now = dayjs()
      const sDate = dayjs(start)
      const eDate = end ? dayjs(end) : dayjs('2100-01-01')
      
      return now.isAfter(sDate.startOf('day')) && now.isBefore(eDate.endOf('day')) || now.isSame(sDate, 'day') || now.isSame(eDate, 'day')
  }, [selectedCampanha])

  const aguardarRespostasAtivo = useMemo(() => {
      if (!selectedCampanha) return false
      const cfg = selectedCampanhaConfig || {}
      return String(cfg.response_mode || '').toUpperCase() === 'SIM_NAO'
  }, [selectedCampanha, selectedCampanhaConfig])

  const handleResetarCampanha = () => {
      if (!selectedCampanha) return

      modal.confirm({
          title: 'RESETAR CAMPANHA',
          content: 'Deseja realmente resetar esta campanha? Todos os contatos voltarão para o status "Aguardando" e os contadores serão zerados (exceto META).',
          okText: 'SIM, RESETAR',
          cancelText: 'CANCELAR',
          onOk: async () => {
              message.loading({ content: 'Resetando campanha...', key: 'reset' })
              try {
                  await api.resetCampanhaDisparos(selectedCampanha.id)

                  // 1. Reset local contacts
                  const resetContacts = contactStatuses.map(c => {
                      const original = { ...c.original, status: 'waiting' } as any
                      if (original) {
                        delete original.resposta
                        delete original.response
                        delete original.respondido_em
                        delete original.respondidoEm
                        delete original.enviado_em
                        delete original.enviadoEm
                      }
                      return {
                        ...c,
                        status: 'waiting',
                        original
                      }
                  })

                  // 2. Prepare Counters
                  const newStats = {
                      enviados: 0,
                      nao_enviados: 0,
                      positivos: 0,
                      negativos: 0,
                      aguardando: 0
                  }

                  // 3. Prepare JSON
                  let finalAnexo: any = resetContacts.map(c => c.original)
                  if (selectedCampanha.conteudo_arquivo) {
                      try {
                          const parsed = JSON.parse(selectedCampanha.conteudo_arquivo)
                          if (!Array.isArray(parsed) && parsed.contacts) {
                              finalAnexo = {
                                  ...parsed,
                                  contacts: finalAnexo
                              }
                          }
                      } catch (e) {}
                  }

                  // 4. Update DB
                  await api.updateCampanha(selectedCampanha.id, {
                      ...newStats,
                      anexo_json: finalAnexo,
                      status: 'ATIVO'
                  })

                  // 5. Update UI
                  setContactStatuses(resetContacts)
                  // Update data list to reflect counters immediately
                  setData(prev => prev.map(d => {
                      if (d.id === selectedCampanha.id) {
                          return { ...d, ...newStats, status: 'ATIVO' }
                      }
                      return d
                  }))

                  try {
                    if (eventLogsKey) localStorage.removeItem(eventLogsKey)
                  } catch {}
                  setEventLogs([
                    `[${dayjs().format('HH:mm:ss')}] Sistema pronto. Aguardando início do disparo.`,
                    `[${dayjs().format('HH:mm:ss')}] CAMPANHA RESETADA.`,
                  ])
                  message.success({ content: 'Campanha resetada com sucesso!', key: 'reset' })
                  
                  // Reload from server to be sure
                  await load()
              } catch (e: any) {
                  console.error(e)
                  message.error({ content: 'Erro ao resetar campanha', key: 'reset' })
              }
          }
      })
  }

  const handleAtualizarCampanha = async () => {
      if (!selectedCampanha) return
      message.loading({ content: 'Atualizando...', key: 'refresh' })
      try {
          await load({ refreshSchema: true })
          message.success({ content: 'Atualizado!', key: 'refresh' })
      } catch {
          message.error({ content: 'Erro ao atualizar', key: 'refresh' })
      }
  }

  const handleEnviarCampanha = async () => {
      if (!selectedCampanha) return

      message.loading({ content: 'Iniciando automação...', key: 'envio' })
      setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] INICIANDO DISPARO DA CAMPANHA: ${selectedCampanha.nome}`])
      
      try {
          // Check connection first
          setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] Verificando conexão com EvolutionAPI...`])
          
          // Filter targets: Waiting or Error (Retry)
          // Exclude Success
          const targetContacts = contactStatuses.filter(c => c.status !== 'success')
          setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] Iniciando envio para ${targetContacts.length} contatos.`])

          let localContacts = [...contactStatuses]
          
          // Counters for DB update (delta from initial state of this run)
          let deltaEnviados = 0
          let deltaNaoEnviados = 0
          let deltaAguardando = 0
          
          // Prepare media payload once
          // If it starts with data:, it's base64. If http, it's URL. Otherwise, assume it's a filename that backend will resolve.
          const mediaPayload = selectedCampanha.imagem ? resolveImageSrc(selectedCampanha.imagem) : undefined
          
          const config = (() => {
              return selectedCampanhaConfig || {}
          })()
          const aguardarRespostas = String(config.response_mode || '').toUpperCase() === 'SIM_NAO'
          const evoIds = (() => {
            const rawIds = (config as any).evolution_api_ids ?? (config as any).evolution_api_id
            const arr = Array.isArray(rawIds) ? rawIds : (rawIds !== undefined && rawIds !== null ? [rawIds] : [])
            return arr.map((x: any) => String(x ?? '').trim()).filter((s: any) => !!s)
          })()
          const computedAguardandoBase = Math.max(0, (selectedCampanha.enviados || 0) - ((selectedCampanha.positivos || 0) + (selectedCampanha.negativos || 0)))
          const baseAguardando = aguardarRespostas ? (selectedCampanha.aguardando !== undefined && selectedCampanha.aguardando !== null ? Number(selectedCampanha.aguardando || 0) : computedAguardandoBase) : 0

          const recorrenciaAtiva = !!(selectedCampanha as any).recorrencia_ativa
          const totalBlocos = Number((selectedCampanha as any).total_blocos ?? 5)
          const mensagensPorBloco = Number((selectedCampanha as any).mensagens_por_bloco ?? 500)
          const blocosPorDia = Number((selectedCampanha as any).blocos_por_dia ?? 1)
          let blocoAtual = Number((selectedCampanha as any).bloco_atual ?? 0)
          const intervaloMinSegRaw = Number((selectedCampanha as any).intervalo_min_seg ?? 5)
          const intervaloMaxSegRaw = Number((selectedCampanha as any).intervalo_max_seg ?? 120)
          const intervaloMinSeg = Math.max(1, Math.min(intervaloMinSegRaw, intervaloMaxSegRaw))
          const intervaloMaxSeg = Math.max(1, Math.max(intervaloMinSegRaw, intervaloMaxSegRaw))
          const maxEnviosNesteRun = recorrenciaAtiva ? Math.max(1, Math.floor(mensagensPorBloco)) : Number.POSITIVE_INFINITY

          if (recorrenciaAtiva && Number.isFinite(totalBlocos) && blocoAtual >= totalBlocos) {
            setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] RECORRÊNCIA ENCERRADA: blocos concluídos (${blocoAtual}/${totalBlocos}).`])
            message.warning({ content: 'Recorrência já concluiu todos os blocos.', key: 'envio' })
            return
          }
          if (recorrenciaAtiva) {
            setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] RECORRÊNCIA ATIVA: bloco ${blocoAtual + 1}/${totalBlocos}, até ${maxEnviosNesteRun} mensagens, intervalo ${intervaloMinSeg}s-${intervaloMaxSeg}s.`])
          }

          let enviosNesteRun = 0
          let dispatchIndex = 0
          let lastDispatchAtMs: number | null = null

          const rrPool = (() => {
            if (selectedEvolutionInstanceId !== 'ALL') return []
            const list = availableEvolutionInstances || []
            const connected = list.filter((x: any) => String(x?.connectionStatus || '').toUpperCase() === 'CONNECTED')
            return (connected.length ? connected : list).filter((x: any) => !!String(x?.id ?? '').trim())
          })()

          try {
              const digitsOnly = (v: any) => String(v ?? '').replace(/\D/g, '')
              const toValidate = Array.from(new Set(
                localContacts
                  .filter(c => typeof (c as any).is_whatsapp !== 'boolean')
                  .map(c => digitsOnly((c as any).whatsapp))
                  .filter(Boolean)
              ))
              if (toValidate.length) {
                  setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] Validando números no WhatsApp (${toValidate.length})...`])
                  const evoId =
                    (typeof selectedEvolutionInstanceId === 'string' && selectedEvolutionInstanceId && selectedEvolutionInstanceId !== 'ALL')
                      ? selectedEvolutionInstanceId
                      : undefined
                  const wa = await api.whatsappCheckNumbers({ numbers: toValidate, evolution_api_id: evoId })
                  const waByNumber = new Map<string, { is_whatsapp: boolean; jid?: string | null }>()
                  for (const r of wa?.rows || []) {
                      const d = digitsOnly((r as any).number)
                      if (!d) continue
                      waByNumber.set(d, { is_whatsapp: !!(r as any).is_whatsapp, jid: (r as any).jid ?? null })
                  }
                  localContacts = localContacts.map((c: any) => {
                      const d = digitsOnly(c.whatsapp)
                      const hit = waByNumber.get(d)
                      if (!hit) return c
                      return { ...c, is_whatsapp: hit.is_whatsapp, whatsapp_jid: hit.jid ?? null, original: { ...(c.original || {}), is_whatsapp: hit.is_whatsapp, whatsapp_jid: hit.jid ?? null } }
                  })
                  setContactStatuses([...localContacts])
              }
          } catch {
          }

          // We iterate over the FULL list to maintain indices, but skip success
          for (let i = 0; i < localContacts.length; i++) {
              if (enviosNesteRun >= maxEnviosNesteRun) break
              const contact = localContacts[i]
              
              // Skip if already success
              if (contact.status === 'success') continue
              enviosNesteRun++
              const attemptIndex = dispatchIndex
              dispatchIndex++
              
              setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] Enviando mensagem para ${contact.nome} (${contact.whatsapp})...`])
              
              const prevStatus = contact.status
              let success = false
              let errorMsg = ''

              if (contact.is_whatsapp === false) {
                  success = false
                  errorMsg = 'Número não possui WhatsApp'
              } else try {
                  // Variable Substitution
                  let msg = String(selectedCampanha.descricao ?? '')
                  // Replace (NOME), {NOME}, (NAME), {NAME}
                  const nameToUse = contact.nome || ''
                  msg = msg.replace(/\(NOME\)/gi, nameToUse)
                           .replace(/\{NOME\}/gi, nameToUse)
                           .replace(/\(NAME\)/gi, nameToUse)
                           .replace(/\{NAME\}/gi, nameToUse)

                  if (attemptIndex === 0) {
                      setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] DEBUG: Exemplo de mensagem resolvida: "${msg}"`])
                  }

                  if (aguardarRespostas) {
                      const question = String(config.question || '').trim()
                      const parts = [msg.trim()]
                      if (question) parts.push(question)
                      parts.push('RESPONDA:\n1 - SIM\n2 - NÃO')
                      msg = parts.filter(Boolean).join('\n\n')
                  }
                  let textPosition = config.text_position || 'bottom'
                  if (!msg.trim()) {
                      if (!mediaPayload) throw new Error('Mensagem vazia')
                  }

                  const chosenEvoId =
                    selectedEvolutionInstanceId === 'ALL'
                      ? (rrPool.length ? String(rrPool[attemptIndex % rrPool.length]?.id ?? '').trim() : undefined)
                      : (typeof selectedEvolutionInstanceId === 'string' ? selectedEvolutionInstanceId : (evoIds.length ? evoIds[attemptIndex % evoIds.length] : undefined))
                  await api.sendWhatsAppMessage(
                      String(contact.whatsapp), 
                      msg,
                      mediaPayload,
                      textPosition,
                      { campanha_id: selectedCampanha.id, contato_nome: contact.nome, evolution_api_id: chosenEvoId ?? undefined }
                  )
                  success = true
              } catch (err: any) {
                  console.error(err)
                  success = false
                  errorMsg = err.response?.data?.detail || err.message || 'Erro desconhecido'
              }

              const dispatchAtMs = Date.now()
              lastDispatchAtMs = dispatchAtMs
              
              // Update status in local array
              const sentIso = success ? new Date(dispatchAtMs).toISOString() : undefined
              const nextOriginal = { ...(contact.original || {}) } as any
              if (success && sentIso) nextOriginal.enviado_em = sentIso
              if (typeof contact.is_whatsapp === 'boolean') nextOriginal.is_whatsapp = contact.is_whatsapp
              if (contact.whatsapp_jid !== undefined) nextOriginal.whatsapp_jid = contact.whatsapp_jid
              if (contact.resposta !== undefined && contact.resposta !== null) nextOriginal.resposta = contact.resposta
              if ((contact as any).respondido_em) nextOriginal.respondido_em = (contact as any).respondido_em
              localContacts[i] = { ...contact, status: success ? 'success' : 'error', original: nextOriginal }
              
              // Calculate deltas based on transition
              if (success) {
                  deltaEnviados++
                  if (prevStatus === 'error') deltaNaoEnviados--
                  if (aguardarRespostas) deltaAguardando++
              } else {
                  if (prevStatus === 'waiting') {
                      deltaNaoEnviados++
                  }
                  // If it was error and stays error, no change in counters
              }
                  
              // Update UI State (Contacts List)
              setContactStatuses([...localContacts])

              // Update Cards Real-time
              // We use selectedCampanha (captured at start) as base, adding deltas
              setData(prevData => prevData.map(d => {
                  if (d.id === selectedCampanha.id) {
                      return {
                          ...d,
                          enviados: (selectedCampanha.enviados || 0) + deltaEnviados,
                          nao_enviados: (selectedCampanha.nao_enviados || 0) + deltaNaoEnviados,
                          aguardando: aguardarRespostas ? Math.max(0, baseAguardando + deltaAguardando) : 0
                      }
                  }
                  return d
              }))
                  
              if (success) {
                  setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] [SUCESSO] Mensagem entregue para ${contact.whatsapp}`])
              } else {
                  setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] [ERRO] Falha ao entregar para ${contact.whatsapp}: ${errorMsg}`])
              }
              
              const waitSeconds = recorrenciaAtiva
                ? Math.floor(Math.random() * (intervaloMaxSeg - intervaloMinSeg + 1)) + intervaloMinSeg
                : 1
              const baseMs = lastDispatchAtMs ?? Date.now()
              const targetMs = baseMs + (waitSeconds * 1000)
              const sleepMs = Math.max(0, targetMs - Date.now())
              if (recorrenciaAtiva) {
                setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] INTERVALO: aguardando ${Math.ceil(sleepMs / 1000)}s (range ${intervaloMinSeg}-${intervaloMaxSeg}).`])
              }
              await new Promise(resolve => globalThis.setTimeout(resolve, sleepMs))
          }
          
          setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] DISPARO FINALIZADO.`])
          
          // Update campaign stats and JSON in database (final sync)
          try {
             // Construct new AnexoJSON with updated statuses
             // Map localContacts back to original structure but update status field
             const newAnexo = localContacts.map(c => {
                 const base = { ...(c.original || {}) } as any
                 if (typeof (c as any).is_whatsapp === 'boolean') base.is_whatsapp = (c as any).is_whatsapp
                 if ((c as any).whatsapp_jid !== undefined) base.whatsapp_jid = (c as any).whatsapp_jid
                 if ((c as any).resposta !== undefined && (c as any).resposta !== null) base.resposta = (c as any).resposta
                 if ((c as any).respondido_em) base.respondido_em = (c as any).respondido_em
                 base.status = c.status
                 return base
             })

             let finalAnexo: any = newAnexo
             if (selectedCampanha.conteudo_arquivo) {
                 try {
                     const parsed = JSON.parse(selectedCampanha.conteudo_arquivo)
                     if (!Array.isArray(parsed) && parsed.contacts) {
                         finalAnexo = {
                             ...parsed,
                             contacts: newAnexo
                         }
                     }
                 } catch {}
             }
             
             const shouldAdvanceBlock = recorrenciaAtiva && enviosNesteRun > 0
             const nextBlocoAtual = shouldAdvanceBlock ? blocoAtual + 1 : blocoAtual
             const nextExec = (() => {
               if (!recorrenciaAtiva || !shouldAdvanceBlock) return undefined
               const perDay = Number.isFinite(blocosPorDia) && blocosPorDia > 0 ? blocosPorDia : 1
               if (perDay === 1) return dayjs().add(1, 'day').toISOString()
               const minutes = Math.max(1, Math.floor(1440 / perDay))
               return dayjs().add(minutes, 'minute').toISOString()
             })()

             await api.updateCampanha(selectedCampanha.id, {
                 status: 'ATIVO',
                 enviados: (selectedCampanha.enviados || 0) + deltaEnviados,
                 nao_enviados: (selectedCampanha.nao_enviados || 0) + deltaNaoEnviados,
                 aguardando: aguardarRespostas ? Math.max(0, baseAguardando + deltaAguardando) : 0,
                 anexo_json: finalAnexo,
                 ...(recorrenciaAtiva ? { bloco_atual: nextBlocoAtual, proxima_execucao: nextExec } : {})
             })
             
             // Reload list to update table and ensure consistency
             load({ refreshSchema: false })
          } catch (updateErr) {
             console.error("Erro ao atualizar status da campanha", updateErr)
             setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] ERRO AO SALVAR NO BANCO: ${updateErr}`])
          }

          message.success({ content: 'Automação finalizada!', key: 'envio' })
      } catch (e) {
          setEventLogs(prev => [...prev, `[${dayjs().format('HH:mm:ss')}] ERRO CRÍTICO: ${e}`])
          message.error({ content: 'Erro ao iniciar automação', key: 'envio' })
      }
  }


  const IconEdit = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z" fill="currentColor"/><path d="M20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" fill="currentColor"/></svg>
  )
  const IconDelete = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M6 7h12M9 7v10m6-10v10M4 7h16l-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
  )
  const IconColumns = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 4h6v16H3V4zm12 0h6v16h-6V4z" fill="currentColor"/></svg>
  )
  const IconAdd = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )

  const getStatus = (record: any) => {
    if (!record) return { label: '-', color: 'default' }
    
    const today = dayjs().startOf('day')
    const start = record.data_inicio ? dayjs(record.data_inicio).startOf('day') : null
    const end = record.data_fim ? dayjs(record.data_fim).endOf('day') : null
    
    // Check master switch (boolean or string)
    let isActive = false
    const s = record.status
    // Handle various truthy formats
    if (s === true || s === 'true' || s === 'TRUE' || s === '1' || s === 1 || String(s).toUpperCase() === 'ATIVO') {
        isActive = true
    }
    
    // Explicit inactive check
    if (s === false || s === 'false' || s === 'FALSE' || s === '0' || s === 0 || String(s).toUpperCase() === 'INATIVO') {
        isActive = false
    }

    if (!isActive) return { label: 'INATIVO', color: 'red' }
    
    // If Active, check dates
    if (start && today.isBefore(start)) return { label: 'AGENDADO', color: 'blue' }
    if (end && today.isAfter(end)) return { label: 'INATIVO', color: 'red' } // Expired
    
    return { label: 'ATIVO', color: 'green' }
  }

  const load = useCallback(async (opts?: { refreshSchema?: boolean }) => {
    try {
      setLoading(true)
      const shouldRefreshSchema = opts?.refreshSchema ?? (columnsMeta.length === 0)
      if (shouldRefreshSchema) {
        const schema = await api.getCampanhasSchema()
        const defaultOrder = [
          'id',
          'nome',
          'status',
          'meta',
          'enviados',
          'aguardando',
          'data_inicio',
          'data_fim',
          'created_at',
        ]
        const byName: Record<string, { name: string; type: string; nullable: boolean }> = {}
        for (const c of schema.columns || []) byName[c.name] = c
        const ordered = defaultOrder.filter(n => byName[n]).map(n => byName[n])
        const rest = (schema.columns || []).filter(c => !defaultOrder.includes(c.name))
        setColumnsMeta([...ordered, ...rest])

        const visDefault: Record<string, boolean> = {}
        for (const n of defaultOrder) if (byName[n]) visDefault[n] = true
        for (const c of rest) visDefault[c.name] = false
        
        const visKey = `campanhas.columns.visible.${(user as any)?.usuario || 'default'}`
        const savedVis = localStorage.getItem(visKey)
        setVisibleCols(savedVis ? JSON.parse(savedVis) : visDefault)
        
        const orderKey = `campanhas.columns.order.${(user as any)?.usuario || 'default'}`
        const savedOrder = localStorage.getItem(orderKey)
        setOrderedKeys(savedOrder ? JSON.parse(savedOrder) : defaultOrder.filter(n => byName[n]))
      }

      const res = await api.getCampanhas()
      const rows = res.rows || []
      setData(rows)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar campanhas')
    } finally {
      setLoading(false)
    }
  }, [api, columnsMeta.length, message, user])

  useEffect(() => { load({ refreshSchema: true }) }, [load])

  useEffect(() => {
    if (!selectedCampanha || !aguardarRespostasAtivo) return
    const refresh = async () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      await load({ refreshSchema: false })
    }
    const id = globalThis.setInterval(refresh, 15000)
    return () => globalThis.clearInterval(id)
  }, [aguardarRespostasAtivo, load, selectedCampanha?.id])

  const baseColumns = columnsMeta.map(col => {
    const dataIndex = col.name
    const uniqueValues = Array.from(new Set((data || []).map(r => r[dataIndex]).filter(v => v !== undefined && v !== null)))
    const filters = uniqueValues.slice(0, 20).map(v => ({ text: String(v).toUpperCase(), value: String(v).toUpperCase() }))
    const type = (col.type || '').toLowerCase()
    
    const sorter = (a: any, b: any) => {
      const av = a[dataIndex]
      const bv = b[dataIndex]
      if (av === undefined || av === null) return -1
      if (bv === undefined || bv === null) return 1
      if (type.includes('int') || type.includes('numeric') || type.includes('decimal')) return Number(av) - Number(bv)
      if (type.includes('date') || type.includes('timestamp')) return new Date(av).getTime() - new Date(bv).getTime()
      return String(av).toUpperCase().localeCompare(String(bv).toUpperCase())
    }

    const titleMap: Record<string, string> = {
      id: 'ID',
      nome: 'NOME DA CAMPANHA',
      descricao: 'DESCRIÇÃO',
      status: 'STATUS',
      data_inicio: 'INÍCIO',
      data_fim: 'FIM',
      meta: 'META',
      enviados: 'ENVIADOS',
      nao_enviados: 'NÃO ENVIADOS',
      positivos: 'RESPOSTAS POSITIVAS',
      negativos: 'RESPOSTAS NEGATIVAS',
      aguardando: 'AGUARDANDO RESPOSTAS',
      created_at: 'CRIADO EM',
    }

    const centerCols = new Set(['id', 'status', 'data_inicio', 'data_fim', 'created_at'])

    return {
      title: titleMap[dataIndex] || dataIndex.toUpperCase(),
      dataIndex,
      align: centerCols.has(dataIndex) ? 'center' : 'left',
      filters,
      onFilter: (value: any, record: any) => String(record[dataIndex]).toUpperCase() === String(value).toUpperCase(),
      sorter,
      render: (v: any, record: any) => {
          if (v === null || v === undefined) return ''
          if (type.includes('date') || type.includes('timestamp')) {
             const d = new Date(v)
             if (!isNaN(d.getTime())) return d.toLocaleDateString('pt-BR')
          }
          if (dataIndex === 'status') {
             const { label, color } = getStatus(record)
             return <Tag color={color}>{label}</Tag>
          }
          return String(v).toUpperCase()
      },
      onHeaderCell: () => ({
        draggable: true,
        onDragStart: (e: any) => { e.dataTransfer.setData('text/plain', dataIndex) },
        onDragOver: (e: any) => { e.preventDefault() },
        onDrop: (e: any) => {
          const from = e.dataTransfer.getData('text/plain')
          const to = dataIndex
          if (!from || from === to) return
          setOrderedKeys((prev) => {
            const next = prev.filter(k => k !== from)
            const idx = next.indexOf(to)
            if (idx === -1) return prev
            next.splice(idx, 0, from)
            const orderKey = `campanhas.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      })
    }
  })

  const actionColumn: any = {
    title: 'AÇÕES',
    dataIndex: '__actions__',
    align: 'center',
    render: (_: any, record: any) => (
      <Space>
        <Button type="text" icon={<IconEdit />} title="EDITAR" onClick={() => { setEditing(record); setModalOpen(true) }} />
        <Button type="text" danger icon={<IconDelete />} title="DELETAR" onClick={async () => {
          try {
            if (!record.id) { message.info('REGISTRO SEM ID'); return }
            await api.deleteCampanha(record.id)
            message.success('CAMPANHA DELETADA')
            await load()
          } catch (e: any) {
            message.error(e?.response?.data?.detail || 'ERRO AO DELETAR CAMPANHA')
          }
        }} />
      </Space>
    )
  }

  const orderedVisible = orderedKeys.length ? orderedKeys : baseColumns.map(c => c.dataIndex)
  const visibleColumns = orderedVisible
    .map(k => baseColumns.find(c => c.dataIndex === k))
    .filter(Boolean)
    .filter((c: any) => visibleCols[(c as any).dataIndex])
    .concat([actionColumn])

  const columnChooser = (
    <div style={{ padding: 12 }}>
      {columnsMeta.map(c => (
        <div key={c.name} style={{ marginBottom: 6 }}>
          <Checkbox
            checked={!!visibleCols[c.name]}
            onChange={(e) => {
              const next = { ...visibleCols, [c.name]: e.target.checked }
              setVisibleCols(next)
              const visKey = `campanhas.columns.visible.${(user as any)?.usuario || 'default'}`
              localStorage.setItem(visKey, JSON.stringify(next))
            }}
          >{c.name.toUpperCase()}</Checkbox>
        </div>
      ))}
    </div>
  )

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      
      {/* METRICS AND INFO PANEL */}
      <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }} styles={{ body: { padding: '12px' } }}>
         <Row gutter={16} align="middle">
             <Col span={16}>
                <Row gutter={8} wrap={false}>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#f0f5ff', borderColor: '#adc6ff' }}>
                            <Statistic title="META" value={selectedCampanha?.meta || 0} valueStyle={{ color: '#2f54eb', fontSize: '18px' }} prefix={<TeamOutlined />} />
                        </Card>
                    </Col>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#fff0f6', borderColor: '#ffadd2' }}>
                            <Statistic title="DISPAROS" value={(selectedCampanha?.enviados || 0) + (selectedCampanha?.nao_enviados || 0)} valueStyle={{ color: '#eb2f96', fontSize: '18px' }} prefix={<ClockCircleFilled />} />
                        </Card>
                    </Col>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#f6ffed', borderColor: '#b7eb8f' }}>
                            <Statistic title="ENVIADOS" value={selectedCampanha?.enviados || 0} valueStyle={{ color: '#3f8600', fontSize: '18px' }} prefix={<CheckCircleOutlined />} />
                        </Card>
                    </Col>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#fff1f0', borderColor: '#ffa39e' }}>
                            <Statistic title="NÃO ENV." value={selectedCampanha?.nao_enviados || 0} valueStyle={{ color: '#cf1322', fontSize: '18px' }} prefix={<ExclamationCircleOutlined />} />
                        </Card>
                    </Col>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#e6f7ff', borderColor: '#91d5ff' }}>
                            <Statistic title="RESPOSTAS POSITIVAS" value={selectedCampanha?.positivos || 0} valueStyle={{ color: '#096dd9', fontSize: '18px' }} />
                        </Card>
                    </Col>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#fffbe6', borderColor: '#ffe58f' }}>
                            <Statistic title="RESPOSTAS NEGATIVAS" value={selectedCampanha?.negativos || 0} valueStyle={{ color: '#d48806', fontSize: '18px' }} />
                        </Card>
                    </Col>
                    <Col flex="1">
                        <Card size="small" style={{ textAlign: 'center', background: '#f9f0ff', borderColor: '#d3adf7' }}>
                            <Statistic title="AGUARDANDO RESPOSTAS" value={aguardarRespostasAtivo ? (selectedCampanha?.aguardando || 0) : 0} valueStyle={{ color: '#722ed1', fontSize: '18px' }} prefix={<SyncOutlined spin={aguardarRespostasAtivo && (selectedCampanha?.aguardando || 0) > 0} />} />
                        </Card>
                    </Col>
                </Row>
             </Col>
             <Col span={8} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderLeft: '1px solid #e8e8e8', paddingLeft: 16 }}>
                 <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                     {selectedCampanha?.imagem ? (
                         <Image 
                           src={resolveImageSrc(selectedCampanha.imagem)} 
                            height={60} 
                            width={60} 
                            style={{ objectFit: 'cover', borderRadius: 4 }}
                            alt="Campanha"
                         />
                     ) : (
                         <div style={{ width: 60, height: 60, background: '#eee', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                             <PictureOutlined style={{ fontSize: 24 }} />
                         </div>
                     )}
                     <div style={{ fontSize: 12, color: '#666' }}>
                         {selectedCampanha ? (
                             <>
                                <strong>{selectedCampanha.nome}</strong><br/>
                                <span style={{ fontSize: 10 }}>
                                    {(() => {
                                        const s = getStatus(selectedCampanha)
                                        return <Tag color={s.color} style={{ margin: 0 }}>{s.label}</Tag>
                                    })()}
                                </span>
                             </>
                         ) : <span>Selecione uma campanha</span>}
                     </div>
                 </div>
                 
                 <div style={{ display: 'flex', gap: 8 }}>
                     <Select
                       value={selectedEvolutionInstanceId ?? undefined}
                       placeholder="Instância Evolution"
                       style={{ minWidth: 220 }}
                       disabled={!selectedCampanha || !availableEvolutionInstances.length}
                       options={[
                         { value: 'ALL', label: 'TODAS AS INSTÂNCIAS (ALTERNAR)' },
                         ...(availableEvolutionInstances || []).map((x: any) => {
                           const status = String(x?.connectionStatus || '').toUpperCase()
                           const nm = String(x?.name || x?.nome || x?.id)
                           const num = String(x?.number || '').trim()
                           const label = `${nm}${num ? ` - ${num}` : ''}${status ? ` (${status})` : ''}`
                           return { value: String(x?.id ?? '').trim(), label }
                         }),
                       ]}
                       onChange={(val) => {
                         if (val === 'ALL') setSelectedEvolutionInstanceId('ALL')
                         else setSelectedEvolutionInstanceId((val ? String(val).trim() : null) || null)
                       }}
                       allowClear
                     />
                     <Tooltip title="Atualizar dados e respostas da campanha">
                         <Button
                            onClick={handleAtualizarCampanha}
                            disabled={!selectedCampanha}
                            icon={<SyncOutlined />}
                         >
                            ATUALIZAR
                         </Button>
                     </Tooltip>
                     <Tooltip title="Resetar todos os contatos e contadores">
                         <Button
                            onClick={handleResetarCampanha}
                            disabled={!selectedCampanha}
                            icon={<ReloadOutlined />}
                            danger
                         >
                            RESETAR
                         </Button>
                     </Tooltip>
                     <Tooltip title={!selectedCampanha ? "Selecione uma campanha" : (!canSend ? "Fora do período de vigência" : "Iniciar automação")}>
                          <Button 
                            onClick={handleEnviarCampanha} 
                            disabled={!canSend}
                            icon={<SendOutlined />}
                            type="primary"
                            style={{ 
                                background: canSend ? '#52c41a' : undefined, 
                                borderColor: canSend ? '#52c41a' : undefined 
                            }}
                          >
                            ENVIAR
                          </Button>
                     </Tooltip>
                 </div>
             </Col>
         </Row>
      </Card>

      {/* MONITORING PANEL */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
          {/* CONTACT STATUS TABLE */}
          <Col span={6}>
              <Card size="small" title="Status dos Contatos" styles={{ body: { padding: 0, height: 400, overflowY: 'auto' } }}>
                  <List
                    size="small"
                    dataSource={contactStatuses}
                    renderItem={item => (
                        <List.Item style={{ padding: '8px 12px' }}>
                            <Space>
                                {item.status === 'success' && <CheckCircleFilled style={{ color: '#52c41a' }} />}
                                {item.status === 'error' && <CloseCircleFilled style={{ color: '#ff4d4f' }} />}
                                {item.status === 'waiting' && <ClockCircleFilled style={{ color: '#faad14' }} />}
                                <div>
                                    <div style={{ fontWeight: 500 }}>{item.nome}</div>
                                    <div style={{ fontSize: 11, color: '#999' }}>{item.whatsapp}</div>
                                </div>
                                {item.is_whatsapp === true && <Tag color="green" style={{ marginLeft: 6 }}>WHATSAPP VÁLIDO</Tag>}
                                {item.is_whatsapp === false && <Tag color="red" style={{ marginLeft: 6 }}>WHATSAPP INVÁLIDO</Tag>}
                                {(() => {
                                    const p = String(item.presence || '').toLowerCase().trim()
                                    if (!p) return null
                                    if (p === 'available' || p === 'online') return <Tag color="green" style={{ marginLeft: 6 }}>ONLINE</Tag>
                                    if (p === 'unavailable' || p === 'offline') return <Tag style={{ marginLeft: 6 }}>OFFLINE</Tag>
                                    if (p === 'composing' || p === 'typing') return <Tag color="blue" style={{ marginLeft: 6 }}>DIGITANDO</Tag>
                                    if (p === 'recording') return <Tag color="purple" style={{ marginLeft: 6 }}>GRAVANDO</Tag>
                                    return <Tag style={{ marginLeft: 6 }}>{p.toUpperCase()}</Tag>
                                })()}
                                {item.resposta === 1 && <Tag color="green" style={{ marginLeft: 6 }}>SIM</Tag>}
                                {item.resposta === 2 && <Tag color="red" style={{ marginLeft: 6 }}>NÃO</Tag>}
                            </Space>
                        </List.Item>
                    )}
                  />
                  {contactStatuses.length === 0 && <div style={{ padding: 16, textAlign: 'center', color: '#999' }}>{!selectedCampanha ? "Selecione uma campanha" : "Nenhum contato na lista"}</div>}
              </Card>
          </Col>

          {/* WHATSAPP PREVIEW */}
          <Col span={8}>
              <Card size="small" title="Preview da Mensagem" styles={{ body: { padding: 0, height: 400, background: '#e5ddd5', display: 'flex', flexDirection: 'column' } }}>
                 <div style={{ flex: 1, padding: 20, overflowY: 'auto', backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")', backgroundSize: 'contain' }}>
                     {selectedCampanha ? (
                         <div style={{ background: '#fff', borderRadius: '0 8px 8px 8px', padding: 8, maxWidth: '85%', boxShadow: '0 1px 1px rgba(0,0,0,0.1)' }}>
                             {selectedCampanha.imagem && (
                                 <Image 
                                     src={resolveImageSrc(selectedCampanha.imagem)} 
                                     style={{ width: '100%', borderRadius: 8, marginBottom: 8 }} 
                                     preview={false}
                                 />
                             )}
                                 <div style={{ fontSize: 14, lineHeight: '1.4', color: '#303030', whiteSpace: 'pre-wrap' }}>
                                 {(() => {
                                    const config = selectedCampanhaConfig || {}
                                    let msg = String(selectedCampanha.descricao || '').trim()
                                    if (String(config.response_mode || '').toUpperCase() === 'SIM_NAO') {
                                      const q = String(config.question || '').trim()
                                      const parts = [msg]
                                      if (q) parts.push(q)
                                      parts.push('RESPONDA:\n1 - SIM\n2 - NÃO')
                                      msg = parts.filter(Boolean).join('\n\n')
                                    }
                                    return msg || 'Sem texto'
                                 })()}
                             </div>
                             <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4, gap: 4 }}>
                                 <span style={{ fontSize: 11, color: '#999' }}>{dayjs().format('HH:mm')}</span>
                                 <CheckCircleFilled style={{ fontSize: 14, color: '#34b7f1' }} />
                             </div>
                         </div>
                     ) : (
                         <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#999', flexDirection: 'column', gap: 8 }}>
                             <WhatsAppOutlined style={{ fontSize: 32 }} />
                             <span>Selecione uma campanha para visualizar o preview</span>
                         </div>
                     )}
                 </div>
              </Card>
          </Col>

          {/* EVENT LOGS */}
          <Col span={10}>
              <Card size="small" title="Log de Eventos (Caixa Preta)" styles={{ body: { padding: 12, height: 400, background: '#000', color: '#0f0', fontFamily: 'monospace', overflowY: 'auto' } }}>
                  {eventLogs.length > 0 ? (
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                          {eventLogs.map((log, idx) => (
                              <li key={idx} style={{ marginBottom: 4, borderBottom: '1px solid #333', paddingBottom: 2 }}>
                                  <RightOutlined style={{ fontSize: 10, marginRight: 8 }} />
                                  {log}
                              </li>
                          ))}
                      </ul>
                  ) : (
                      <div style={{ color: '#666' }}>Aguardando eventos...</div>
                  )}
              </Card>
          </Col>
      </Row>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Space>
          <Dropdown placement="bottomRight" trigger={["click"]} menu={{ items: [] }} popupRender={() => columnChooser}>
            <Button shape="circle" icon={<IconColumns />} style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} title="VISUALIZAÇÃO DE COLUNAS" />
          </Dropdown>
          <Button shape="circle" icon={<IconAdd />} style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} onClick={() => { setEditing(null); setModalOpen(true) }} title="NOVA CAMPANHA" />
        </Space>
      </div>
      <style>{`
        .campanhas-table .ant-table-thead > tr > th{ background:#FFD700; color:#000; font-family: 'Arimo', Arial, sans-serif; }
        .campanhas-table .ant-table-thead > tr > th .ant-table-column-title{ display:flex; justify-content:center; align-items:center; text-align:center; }
        .campanhas-table .ant-table-tbody > tr > td{ font-family: 'Roboto Condensed', Arial, sans-serif; padding:2px 6px; line-height:0.95; height:22px; }
      `}</style>
      <Table
        loading={loading}
        dataSource={data}
        columns={visibleColumns as any}
        rowKey="id"
        bordered
        size="small"
        className="ant-table-striped campanhas-table"
        rowSelection={{
            type: 'radio',
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys)
        }}
        onRow={(record) => ({
            onClick: () => setSelectedRowKeys([record.id])
        })}
      />
      <CampanhasModal
        open={modalOpen}
        initial={editing || undefined}
        onCancel={() => setModalOpen(false)}
        onSaved={async () => { setModalOpen(false); await load() }}
      />
    </motion.div>
  )
}
