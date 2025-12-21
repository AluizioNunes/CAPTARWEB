import { useEffect, useMemo, useState } from 'react'
import { Card, Row, Col, Typography, Button, Space, Tag, Table, App, Select } from 'antd'
import { ThunderboltOutlined, ReloadOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useApi } from '../../context/ApiContext'


export default function Disparos() {
  const [loading, setLoading] = useState(false)
  const [dados, setDados] = useState<any[]>([])
  const [campanhas, setCampanhas] = useState<any[]>([])
  const [campanhaId, setCampanhaId] = useState<number | null>(null)
  const [stats, setStats] = useState<any | null>(null)
  const [pergunta, setPergunta] = useState<string>('')
  const [aguardarRespostas, setAguardarRespostas] = useState(false)
  const [waMap, setWaMap] = useState<Record<string, boolean>>({})
  const [page, setPage] = useState({ current: 1, pageSize: 50 })
  const api = useApi()
  const { message } = App.useApp()

  const statusColorEnvio = (s: any) => {
    const v = String(s || '').toUpperCase().trim()
    if (v === 'ENVIADO' || v === 'ENTREGUE' || v === 'VISUALIZADO') return 'green'
    if (v === 'FALHA') return 'red'
    if (v === 'PENDENTE') return 'default'
    return 'blue'
  }

  const statusColorResposta = (s: any) => {
    const v = String(s || '').toUpperCase().trim()
    if (v === 'POSITIVO') return 'green'
    if (v === 'NEGATIVO') return 'red'
    if (v === 'AGUARDANDO') return 'default'
    return 'blue'
  }

  const columns = useMemo(() => {
    const base: any[] = [
      { title: 'NOME', dataIndex: 'nome', align: 'left', sorter: (a: any, b: any) => String(a.nome || '').localeCompare(String(b.nome || '')) },
      {
        title: 'NÚMERO',
        dataIndex: 'numero',
        align: 'left',
        sorter: (a: any, b: any) => String(a.numero || '').localeCompare(String(b.numero || '')),
        render: (v: any) => {
          const num = String(v || '').trim()
          const isWa = num ? waMap[num] : undefined
          return (
            <Space size={8} wrap>
              <span>{num || '—'}</span>
              {isWa === true ? <Tag color="green">WHATSAPP VÁLIDO</Tag> : null}
              {isWa === false ? <Tag color="red">WHATSAPP INVÁLIDO</Tag> : null}
            </Space>
          )
        },
      },
      {
        title: 'STATUS ENVIO',
        dataIndex: 'envio_status',
        align: 'center',
        render: (v: any) => {
          const s = String(v || '').toUpperCase() || '—'
          return <Tag color={statusColorEnvio(s)}>{s}</Tag>
        },
      },
      {
        title: 'DATA ENVIO',
        dataIndex: 'envio_datahora',
        align: 'center',
        render: (v: any) => v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—',
        sorter: (a: any, b: any) => new Date(a.envio_datahora || 0).getTime() - new Date(b.envio_datahora || 0).getTime(),
      },
      {
        title: 'ENTREGUE',
        dataIndex: 'entregue_em',
        align: 'center',
        render: (v: any) => v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—',
        sorter: (a: any, b: any) => new Date(a.entregue_em || 0).getTime() - new Date(b.entregue_em || 0).getTime(),
      },
      {
        title: 'VISUALIZADO',
        dataIndex: 'visualizado_em',
        align: 'center',
        render: (v: any) => v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—',
        sorter: (a: any, b: any) => new Date(a.visualizado_em || 0).getTime() - new Date(b.visualizado_em || 0).getTime(),
      },
    ]

    if (!aguardarRespostas) return base

    return [
      ...base,
      {
        title: 'RESPOSTA',
        dataIndex: 'resposta_classificacao',
        align: 'center',
        render: (v: any) => {
          const s = String(v || '').toUpperCase() || '—'
          return <Tag color={statusColorResposta(s)}>{s}</Tag>
        },
      },
      {
        title: 'DATA RESPOSTA',
        dataIndex: 'resposta_datahora',
        align: 'center',
        render: (v: any) => v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—',
        sorter: (a: any, b: any) => new Date(a.resposta_datahora || 0).getTime() - new Date(b.resposta_datahora || 0).getTime(),
      },
    ]
  }, [aguardarRespostas, waMap])

  const loadCampanhas = async () => {
    try {
      setLoading(true)
      const res = await api.getCampanhas()
      const rows = res.rows || []
      setCampanhas(rows)
      if (rows.length && campanhaId === null) {
        const first = rows[0]
        if (first?.id) setCampanhaId(Number(first.id))
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar campanhas')
    } finally {
      setLoading(false)
    }
  }

  const loadGrid = async (id?: number | null) => {
    const cid = typeof id === 'number' ? id : campanhaId
    if (!cid) return
    try {
      setLoading(true)
      setWaMap({})
      setPage({ current: 1, pageSize: 50 })
      const res = await api.getCampanhaDisparosGrid(cid)
      const rows = res.rows || []
      setDados(rows)
      setStats(res.stats || null)
      setPergunta(String(res.pergunta || ''))
      try {
        const anexo = (res as any)?.campanha?.anexo_json
        const anexoObj = typeof anexo === 'string' ? JSON.parse(anexo) : anexo
        const cfg = anexoObj?.config || {}
        setAguardarRespostas(String(cfg?.response_mode || '').toUpperCase() === 'SIM_NAO')
      } catch {
        setAguardarRespostas(false)
      }
      try {
        const firstPageRows = rows.slice(0, 50)
        const nums = Array.from(new Set(firstPageRows.map((r: any) => String(r?.numero || '').trim()).filter(Boolean)))
        if (nums.length) {
          const wa = await api.whatsappCheckNumbers({ numbers: nums })
          const m: Record<string, boolean> = {}
          for (const it of (wa as any)?.rows || []) {
            const n = String(it?.number || '').trim()
            if (n) m[n] = !!it?.is_whatsapp
          }
          setWaMap(m)
        }
      } catch {}
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar disparos da campanha')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadCampanhas() }, [])
  useEffect(() => { if (campanhaId) loadGrid(campanhaId) }, [campanhaId])

  const campanhaOptions = useMemo(() => (
    (campanhas || []).map((c: any) => ({
      label: `${String(c.nome || '').toUpperCase()} (${c.id})`,
      value: Number(c.id),
    }))
  ), [campanhas])

  const selectedCampanha = useMemo(() => (
    campanhas.find((c: any) => Number(c.id) === Number(campanhaId))
  ), [campanhas, campanhaId])

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Row gutter={[16,16]}>
        <Col span={24}>
          <Card>
            <Space style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
              <Space>
                <ThunderboltOutlined />
                <Typography.Title level={4} style={{ margin: 0 }}>AUTOMAÇÃO • DISPAROS</Typography.Title>
              </Space>
              <Space>
                <Select
                  style={{ width: 420 }}
                  placeholder="Selecione uma campanha"
                  showSearch
                  optionFilterProp="label"
                  value={campanhaId ?? undefined}
                  options={campanhaOptions}
                  onChange={(v) => setCampanhaId(Number(v))}
                />
                <Button icon={<ReloadOutlined />} onClick={() => loadGrid()}>Atualizar</Button>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col span={24}>
          <Card>
            <Space style={{ marginBottom: 12, width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <Typography.Text strong>{selectedCampanha ? String(selectedCampanha.nome || '').toUpperCase() : '—'}</Typography.Text>
                {pergunta ? <Tag color="blue">{pergunta}</Tag> : null}
              </Space>
              <Space wrap>
                <Tag color="default">CONTATOS: {Number(stats?.total_contatos || 0)}</Tag>
                <Tag color="green">ENVIADOS: {Number(stats?.enviados || 0)}</Tag>
                <Tag color="green">ENTREGUES: {Number(stats?.entregues || 0)}</Tag>
                <Tag color="green">VISUALIZADOS: {Number(stats?.visualizados || 0)}</Tag>
                <Tag color="red">FALHAS: {Number(stats?.falhas || 0)}</Tag>
                {aguardarRespostas && <Tag color="blue">RESPOSTAS: {Number(stats?.respostas || 0)}</Tag>}
                {aguardarRespostas && <Tag color="green">POSITIVOS: {Number(stats?.positivos || 0)}</Tag>}
                {aguardarRespostas && <Tag color="red">NEGATIVOS: {Number(stats?.negativos || 0)}</Tag>}
                {aguardarRespostas && <Tag color="default">AGUARDANDO: {Number(stats?.aguardando || 0)}</Tag>}
              </Space>
            </Space>
            <Table
              rowKey={(r) => String(r.numero || JSON.stringify(r))}
              loading={loading}
              dataSource={dados}
              columns={columns as any}
              size="small"
              bordered
              pagination={{ pageSize: page.pageSize, current: page.current, showSizeChanger: true }}
              onChange={async (p: any, _filters: any, _sorter: any, extra: any) => {
                const next = { current: Number(p?.current || 1), pageSize: Number(p?.pageSize || 50) }
                setPage(next)
                try {
                  const ds = (extra?.currentDataSource || dados) as any[]
                  const start = (next.current - 1) * next.pageSize
                  const pageRows = ds.slice(start, start + next.pageSize)
                  const nums = Array.from(new Set(pageRows.map((r: any) => String(r?.numero || '').trim()).filter(Boolean)))
                    .filter(n => waMap[n] === undefined)
                  if (!nums.length) return
                  const wa = await api.whatsappCheckNumbers({ numbers: nums })
                  const rows = (wa as any)?.rows || []
                  setWaMap(prev => {
                    const nextMap = { ...prev }
                    for (const it of rows) {
                      const n = String(it?.number || '').trim()
                      if (n) nextMap[n] = !!it?.is_whatsapp
                    }
                    return nextMap
                  })
                } catch {}
              }}
            />
          </Card>
        </Col>
      </Row>
    </motion.div>
  )
}
