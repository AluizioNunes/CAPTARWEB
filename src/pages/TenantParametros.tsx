import { useEffect, useState } from 'react'
import { Table, Button, Space, message, Modal, Form, Input, Select } from 'antd'
import { motion } from 'framer-motion'
import { useApi } from '../context/ApiContext'

export default function TenantParametros() {
  const api = useApi()
  const [tenants, setTenants] = useState<any[]>([])
  const [tenantId, setTenantId] = useState<number | null>(null)
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form] = Form.useForm()

  const loadTenants = async () => {
    try {
      const res = await api.listTenants()
      setTenants(res.rows || [])
      const curSlug = localStorage.getItem('tenantSlug') || 'captar'
      const found = (res.rows || []).find((t: any) => t.Slug === curSlug)
      if (found?.IdTenant) setTenantId(found.IdTenant)
    } catch {}
  }

  const load = async () => {
    if (!tenantId) return
    try {
      setLoading(true)
      const res = await api.listTenantParametros(tenantId)
      setData(res.rows || [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar parâmetros')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadTenants() }, [])
  useEffect(() => { load() }, [tenantId])

  const handleSave = async () => {
    if (!tenantId) return
    try {
      const values = await form.validateFields()
      if (editing?.IdParametro) {
        await api.updateTenantParametro(tenantId, editing.IdParametro, values)
        message.success('Parâmetro atualizado')
      } else {
        await api.createTenantParametro(tenantId, values)
        message.success('Parâmetro criado')
      }
      setModalOpen(false)
      setEditing(null)
      await load()
    } catch {}
  }

  const columns = [
    { title: 'ID', dataIndex: 'IdParametro' },
    { title: 'CHAVE', dataIndex: 'Chave' },
    { title: 'VALOR', dataIndex: 'Valor' },
    { title: 'TIPO', dataIndex: 'Tipo' },
    { title: 'DESCRIÇÃO', dataIndex: 'Descricao' },
    { title: 'ATUALIZADO', dataIndex: 'AtualizadoEm' },
    {
      title: 'AÇÕES',
      dataIndex: '__actions__',
      render: (_: any, record: any) => (
        <Space>
          <Button type="text" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>EDITAR</Button>
          <Button type="text" danger onClick={async () => { try { await api.deleteTenantParametro(tenantId!, record.IdParametro); message.success('Parâmetro deletado'); await load() } catch (e: any) { message.error(e?.response?.data?.detail || 'Erro ao deletar') } }}>DELETAR</Button>
        </Space>
      )
    }
  ]

  const tenantOptions = (tenants || []).map((t: any) => ({ value: t.IdTenant, label: t.Nome }))

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Select style={{ width: 280 }} placeholder="Selecione o tenant" options={tenantOptions} value={tenantId ?? undefined} onChange={(v) => setTenantId(v)} />
        <Space>
          <Button type="primary" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }} disabled={!tenantId}>NOVO PARÂMETRO</Button>
        </Space>
      </div>
      <Table rowKey={(r) => r.IdParametro || JSON.stringify(r)} loading={loading} dataSource={data} columns={columns as any} bordered size="middle" />
      <Modal open={modalOpen} title={editing?.IdParametro ? 'Editar Parâmetro' : 'Novo Parâmetro'} onCancel={() => setModalOpen(false)} onOk={handleSave}>
        <Form form={form} layout="vertical">
          <Form.Item name="Chave" label="Chave" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="Valor" label="Valor" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="Tipo" label="Tipo">
            <Select options={[{ value: 'TEXT', label: 'TEXT' }, { value: 'NUMBER', label: 'NUMBER' }, { value: 'BOOL', label: 'BOOL' }]} />
          </Form.Item>
          <Form.Item name="Descricao" label="Descrição">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </motion.div>
  )
}
