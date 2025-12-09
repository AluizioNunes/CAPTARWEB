import { useEffect, useState } from 'react'
import { Card, Space, Button, Table, Modal, Form, Input, Switch, App } from 'antd'
import { motion } from 'framer-motion'
import { useApi } from '../context/ApiContext'

export default function Eleicoes() {
  const api = useApi()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    try {
      setLoading(true)
      const res = await api.listEleicoes()
      setRows(res.rows || [])
    } catch { message.error('Erro ao carregar eleições') } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  const colsDef = [
    { title: 'Id', dataIndex: 'IdEleicao', key: 'IdEleicao', width: 80 },
    { title: 'Nome', dataIndex: 'Nome', key: 'Nome' },
    { title: 'Ano', dataIndex: 'Ano', key: 'Ano', width: 100 },
    { title: 'Turno', dataIndex: 'Turno', key: 'Turno', width: 100 },
    { title: 'Cargo', dataIndex: 'Cargo', key: 'Cargo', width: 160 },
    { title: 'Início', dataIndex: 'DataInicio', key: 'DataInicio', width: 160 },
    { title: 'Fim', dataIndex: 'DataFim', key: 'DataFim', width: 160 },
    { title: 'Ativo', dataIndex: 'Ativo', key: 'Ativo', width: 100 },
  ]
  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values, Ativo: !!values.Ativo }
      const r = await api.createEleicao(payload)
      if (r && r.id) { message.success('Eleição criada'); setOpen(false); form.resetFields(); load() }
    } catch {}
  }
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>ELEIÇÕES</h3>
        <Space>
          <Button type="primary" onClick={() => setOpen(true)}>NOVA ELEIÇÃO</Button>
        </Space>
      </div>
      <Card>
        <Table
          loading={loading}
          dataSource={rows}
          columns={colsDef as any}
          rowKey={r => r.IdEleicao ?? JSON.stringify(r)}
          pagination={{ pageSize: 10 }}
          scroll={{ y: 480 }}
          locale={{ emptyText: 'Nenhuma eleição' }}
        />
      </Card>
      <Modal title="Nova Eleição" open={open} onCancel={() => setOpen(false)} onOk={handleOk} okText="Salvar">
        <Form layout="vertical" form={form}>
          <Form.Item name="Nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="Ano" label="Ano">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="Turno" label="Turno">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="Cargo" label="Cargo">
            <Input />
          </Form.Item>
          <Form.Item name="DataInicio" label="Data Início">
            <Input placeholder="YYYY-MM-DD HH:mm:ss" />
          </Form.Item>
          <Form.Item name="DataFim" label="Data Fim">
            <Input placeholder="YYYY-MM-DD HH:mm:ss" />
          </Form.Item>
          <Form.Item name="Ativo" label="Ativo" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </motion.div>
  )
}
