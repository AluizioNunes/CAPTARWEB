import { useEffect, useState } from 'react'
import { Table, Button, Space, message, Modal, Form, Input, Select, Tag } from 'antd'
import { motion } from 'framer-motion'
import { useApi } from '../context/ApiContext'

export default function Tenants() {
  const api = useApi()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form] = Form.useForm()
  const [provOpen, setProvOpen] = useState(false)
  const [provForm] = Form.useForm()
  const [dsnViewOpen, setDsnViewOpen] = useState(false)
  const [dsnView, setDsnView] = useState<string>('')

  const load = async () => {
    try {
      setLoading(true)
      const res = await api.listTenants()
      const rows = (res.rows || [])
      const withDb = await Promise.all(rows.map(async (r: any) => {
        try {
          const prm = await api.listTenantParametros(r.IdTenant)
          const dsn = (prm.rows || []).find((p: any) => String(p.Chave || p.chave).toUpperCase() === 'DB_DSN')
          return { ...r, __db__: !!dsn }
        } catch {
          return { ...r, __db__: false }
        }
      }))
      setData(withDb)
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
        setData((prev) => prev.map(r => r.IdTenant === editing.IdTenant ? { ...r, ...values } : r))
      } else {
        const res = await api.createTenant(values)
        const newRow = { IdTenant: res.id, Nome: values.Nome, Slug: values.Slug, Status: values.Status ?? 'ATIVO', Plano: values.Plano ?? 'PADRAO' }
        setData((prev) => [newRow, ...prev])
        message.success('Tenant criado')
      }
      setModalOpen(false)
      setEditing(null)
      load()
    } catch {}
  }

  const columns = [
    { title: 'ID', dataIndex: 'IdTenant' },
    { title: 'NOME', dataIndex: 'Nome' },
    { title: 'SLUG', dataIndex: 'Slug' },
    { title: 'STATUS', dataIndex: 'Status' },
    { title: 'PLANO', dataIndex: 'Plano' },
    { title: 'ATUALIZADO', dataIndex: 'DataUpdate' },
    { title: 'DB', dataIndex: '__db__',
      onCell: (_record: any) => ({
        title: 'Estado do DSN do Tenant'
      }),
      render: (v: any) => (v ? <Tag color="green">CONFIGURADO</Tag> : <Tag>NAO CONFIGURADO</Tag>)
    },
    {
      title: 'AÇÕES',
      dataIndex: '__actions__',
      render: (_: any, record: any) => (
        <Space>
          <Button type="text" onClick={() => { setEditing(record); form.setFieldsValue(record); setModalOpen(true) }}>EDITAR</Button>
          <Button type="text" danger onClick={async () => { try { await api.deleteTenant(record.IdTenant); message.success('Tenant deletado'); await load() } catch (e: any) { message.error(e?.response?.data?.detail || 'Erro ao deletar') } }}>DELETAR</Button>
          <Button type="text" onClick={async () => {
            try {
              const res = await api.listTenantParametros(record.IdTenant)
              const dsnParam = (res.rows || []).find((p: any) => String(p.Chave || p.chave).toUpperCase() === 'DB_DSN')
              setDsnView(dsnParam ? String(dsnParam.Valor || dsnParam.valor) : '—')
              setDsnViewOpen(true)
            } catch { setDsnView('—'); setDsnViewOpen(true) }
          }}>VER DSN</Button>
          <Button type="primary" onClick={() => {
            const id = record.IdTenant
            const slug = String(record.Slug || '').toLowerCase()
            const nome = String(record.Nome || '')
            const db_name = `captar_t${String(id).padStart(2,'0')}_${slug}`
            provForm.setFieldsValue({ nome, slug, db_name, db_host: 'postgres', db_port: '5432', db_user: 'captar', db_password: 'captar' })
            setProvOpen(true)
          }}>CRIAR BANCO DE DADOS</Button>
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
      <Modal open={provOpen} title={'Criar Banco de Dados do Tenant'} onCancel={() => setProvOpen(false)} onOk={async () => {
        try {
          const values = await provForm.validateFields()
          const res = await api.provisionTenant(values)
          message.success(`Banco provisionado: ${res.dsn}`)
          setProvOpen(false)
          await load()
        } catch (e: any) {
          message.error(e?.response?.data?.detail || 'Erro ao provisionar banco')
        }
      }}>
        <Form form={provForm} layout="vertical">
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="db_name" label="Nome do Banco" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="db_host" label="Host" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="db_port" label="Porta" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="db_user" label="Usuário" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="db_password" label="Senha" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
      <Modal open={dsnViewOpen} title={'DSN do Tenant'} onCancel={() => setDsnViewOpen(false)} footer={null}>
        <div style={{ fontFamily: 'monospace' }}>{dsnView || '—'}</div>
      </Modal>
    </motion.div>
  )
}
