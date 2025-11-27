import { useEffect, useState } from 'react'
import { Table, Button, Space, message, Modal, Form, Input, Select } from 'antd'
import { motion } from 'framer-motion'
import { useApi } from '../context/ApiContext'

export default function Tenants() {
  const api = useApi()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form] = Form.useForm()

  const load = async () => {
    try {
      setLoading(true)
      const res = await api.listTenants()
      setData(res.rows || [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar tenants')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editing?.IdTenant) {
        await api.updateTenant(editing.IdTenant, values)
        message.success('Tenant atualizado')
      } else {
        await api.createTenant(values)
        message.success('Tenant criado')
      }
      setModalOpen(false)
      setEditing(null)
      await load()
    } catch {}
  }

  const columns = [
    { title: 'ID', dataIndex: 'IdTenant' },
    { title: 'NOME', dataIndex: 'Nome' },
    { title: 'SLUG', dataIndex: 'Slug' },
    { title: 'STATUS', dataIndex: 'Status' },
    { title: 'PLANO', dataIndex: 'Plano' },
    { title: 'ATUALIZADO', dataIndex: 'DataUpdate' },
    {
      title: 'AÇÕES',
      dataIndex: '__actions__',
      render: (_: any, record: any) => (
        <Space>
          <Button type="text" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>EDITAR</Button>
          <Button type="text" danger onClick={async () => { try { await api.deleteTenant(record.IdTenant); message.success('Tenant deletado'); await load() } catch (e: any) { message.error(e?.response?.data?.detail || 'Erro ao deletar') } }}>DELETAR</Button>
        </Space>
      )
    }
  ]

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Space>
          <Button type="primary" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true) }}>NOVO TENANT</Button>
        </Space>
      </div>
      <Table rowKey={(r) => r.IdTenant || JSON.stringify(r)} loading={loading} dataSource={data} columns={columns as any} bordered size="middle" />
      <Modal open={modalOpen} title={editing?.IdTenant ? 'Editar Tenant' : 'Novo Tenant'} onCancel={() => setModalOpen(false)} onOk={handleSave}>
        <Form form={form} layout="vertical">
          <Form.Item name="Nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="Slug" label="Slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="Status" label="Status">
            <Select options={[{ value: 'ATIVO', label: 'ATIVO' }, { value: 'INATIVO', label: 'INATIVO' }]} />
          </Form.Item>
          <Form.Item name="Plano" label="Plano">
            <Select options={[{ value: 'PADRAO', label: 'PADRÃO' }, { value: 'PRO', label: 'PRO' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </motion.div>
  )
}
