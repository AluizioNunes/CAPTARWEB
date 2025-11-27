import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { Card, Row, Col, Form, Input, Select, Button, Space, Tag, Divider, Switch, message, Table } from 'antd'
import { useApi } from '../context/ApiContext'
import axios from 'axios'

export default function Integracoes() {
  const [formTse] = Form.useForm()
  const [formWebhook] = Form.useForm()
  const [formTokens] = Form.useForm()
  const [statusConexao, setStatusConexao] = useState<'CONECTADO'|'DESCONECTADO'|'TESTANDO'>('DESCONECTADO')
  const [municipios, setMunicipios] = useState<{ id: number; nome: string }[]>([])
  const [recursos, setRecursos] = useState<{ id: string; name: string; format: string; url: string }[]>([])
  const [previewCols, setPreviewCols] = useState<string[]>([])
  const [previewRows, setPreviewRows] = useState<any[]>([])
  const [selectedResourceIndex, setSelectedResourceIndex] = useState<number>(0)

  const api = useApi()

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
    })()
  }, [])

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <h1 className="page-title">INTEGRAÇÕES</h1>
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

              <Space>
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
                      // fallback direto
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

          <Divider />
          <Card title="Prévia do Dataset Selecionado (primeiras linhas)">
            <Table
              size="small"
              bordered
              pagination={false}
              columns={previewCols.map(c => ({ title: c, dataIndex: c }))}
              dataSource={previewRows}
              rowKey={(row) => JSON.stringify(row)}
            />
          </Card>
        </Col>
      </Row>
    </motion.div>
  )
}