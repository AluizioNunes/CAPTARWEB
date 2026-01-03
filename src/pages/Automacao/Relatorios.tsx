import { useEffect, useMemo, useState } from 'react'
import { Card, Row, Col, Typography, Button, Space, Table, Select, Input, Modal, App, Tag } from 'antd'
import { FileTextOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useApi } from '../../context/ApiContext'

export default function Relatorios() {
  const api = useApi()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [loadingComprovante, setLoadingComprovante] = useState(false)
  const [campanhas, setCampanhas] = useState<any[]>([])
  const [campanhaId, setCampanhaId] = useState<number | undefined>(undefined)
  const [titulo, setTitulo] = useState('')
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('portrait')
  const [dados, setDados] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const [relatorioSelecionado, setRelatorioSelecionado] = useState<any>(null)

  const baixarPdf = async (relatorioId: number) => {
    try {
      const blob = await api.downloadRelatorioPdf(relatorioId, orientation)
      const url = window.URL.createObjectURL(blob)
      const w = window.open(url, '_blank')
      if (!w) {
        const a = document.createElement('a')
        a.href = url
        a.download = `relatorio_${relatorioId}.pdf`
        document.body.appendChild(a)
        a.click()
        a.remove()
      }
      window.setTimeout(() => window.URL.revokeObjectURL(url), 3000)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao baixar PDF')
    }
  }

  const campanhaOptions = useMemo(() => {
    return (campanhas || []).map(c => ({
      label: `${c.nome} (#${c.id})`,
      value: Number(c.id),
    }))
  }, [campanhas])

  const columns = [
    { title: 'ID', dataIndex: 'id', align: 'center', sorter: (a: any, b: any) => Number(a.id) - Number(b.id) },
    { title: 'CAMPANHA', dataIndex: 'campanha_id', align: 'center', render: (v: any) => v ? String(v) : '—' },
    { title: 'TÍTULO', dataIndex: 'titulo', align: 'left', render: (v: any) => String(v || '') || '—' },
    { title: 'TIPO', dataIndex: 'tipo', align: 'center', render: (v: any) => <Tag>{String(v || '').toUpperCase() || '—'}</Tag> },
    { title: 'CRIADO EM', dataIndex: 'criado_em', align: 'center', render: (v: any) => v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—' },
    { title: 'CRIADO POR', dataIndex: 'criado_por', align: 'left', render: (v: any) => v ? String(v) : '—' },
    {
      title: 'AÇÕES',
      dataIndex: 'id',
      align: 'center',
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={async () => {
            try {
              const r = await api.getRelatorio(Number(record.id))
              setRelatorioSelecionado(r)
              setOpen(true)
            } catch (e: any) {
              message.error(e?.response?.data?.detail || 'Erro ao abrir relatório')
            }
          }}>
            Abrir
          </Button>
          {String(record?.tipo || '').toUpperCase() === 'COMPROVANTE' ? (
            <Button size="small" icon={<DownloadOutlined />} onClick={() => baixarPdf(Number(record.id))}>
              PDF
            </Button>
          ) : null}
        </Space>
      ),
    },
  ]

  const load = async () => {
    try {
      setLoading(true)
      const [resCampanhas, resRelatorios] = await Promise.all([
        api.getCampanhas(),
        api.getRelatorios({ limit: 200 }),
      ])
      setCampanhas(resCampanhas.rows || [])
      setDados(resRelatorios.rows || [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar relatórios')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const gerarComprovante = async () => {
    if (!campanhaId) {
      message.warning('Selecione uma campanha')
      return
    }
    try {
      setLoadingComprovante(true)
      await api.createRelatorioComprovante({ campanha_id: campanhaId, titulo: titulo || undefined })
      setTitulo('')
      await load()
      message.success('Relatório gerado')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao gerar relatório')
    } finally {
      setLoadingComprovante(false)
    }
  }

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Space style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
              <Space>
                <FileTextOutlined />
                <Typography.Title level={4} style={{ margin: 0 }}>AUTOMAÇÃO • RELATÓRIOS</Typography.Title>
              </Space>
              <Button icon={<ReloadOutlined />} onClick={load}>Atualizar</Button>
            </Space>
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Gerar comprovante">
            <Row gutter={[12, 12]}>
              <Col xs={24} md={8}>
                <Typography.Text>Campanha</Typography.Text>
                <Select
                  style={{ width: '100%' }}
                  showSearch
                  optionFilterProp="label"
                  placeholder="Selecione"
                  value={campanhaId}
                  onChange={(v) => setCampanhaId(Number(v))}
                  options={campanhaOptions}
                />
              </Col>
              <Col xs={24} md={8}>
                <Typography.Text>Título (opcional)</Typography.Text>
                <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Comprovante..." />
              </Col>
              <Col xs={24} md={4}>
                <Typography.Text>Orientação PDF</Typography.Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="Selecione"
                  value={orientation}
                  onChange={(v) => setOrientation(v)}
                  options={[
                    { label: 'Retrato', value: 'portrait' },
                    { label: 'Paisagem', value: 'landscape' },
                  ]}
                />
              </Col>
              <Col xs={24} md={4} style={{ display: 'flex', alignItems: 'end' }}>
                <Button type="primary" block loading={loadingComprovante} onClick={gerarComprovante}>Gerar</Button>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={24}>
          <Card>
            <Table
              rowKey={(r, idx) => String((r as any).id ?? idx)}
              loading={loading}
              dataSource={dados}
              columns={columns as any}
              size="small"
              bordered
            />
          </Card>
        </Col>
      </Row>

      <Modal
        open={open}
        onCancel={() => setOpen(false)}
        width={900}
        footer={
          <Space>
            {String(relatorioSelecionado?.tipo || '').toUpperCase() === 'COMPROVANTE' && relatorioSelecionado?.id ? (
              <Button icon={<DownloadOutlined />} onClick={() => baixarPdf(Number(relatorioSelecionado.id))}>
                Baixar PDF
              </Button>
            ) : null}
            <Button onClick={() => setOpen(false)}>Fechar</Button>
          </Space>
        }
        title={relatorioSelecionado?.titulo || 'Relatório'}
      >
        <pre style={{ margin: 0, maxHeight: 520, overflow: 'auto' }}>
          {relatorioSelecionado ? JSON.stringify(relatorioSelecionado, null, 2) : ''}
        </pre>
      </Modal>
    </motion.div>
  )
}
