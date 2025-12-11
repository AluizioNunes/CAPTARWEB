import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Space, Popconfirm, App as AntdApp } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useApi } from '../context/ApiContext'
import { motion } from 'framer-motion'

export default function Eleitor() {
  const { message } = AntdApp.useApp()
  const [eleitores, setEleitores] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [editingId, setEditingId] = useState<number | null>(null)
  const api = useApi()

  const formatCelular = (v: string) => {
    const d = (v || '').replace(/\D/g, '').slice(0, 11)
    if (d.length <= 2) return `(${d}`
    if (d.length <= 7) return `(${d.slice(0,2)}) ${d.slice(2)}`
    return `(${d.slice(0,2)}) ${d.slice(2,7)}-${d.slice(7)}`
  }

  useEffect(() => {
    loadEleitores()
  }, [])

  const loadEleitores = async () => {
    try {
      setLoading(true)
      const data = await api.getEleitores()
      setEleitores(Array.isArray(data) ? data : (data.rows || []))
    } catch (error) {
      message.error('Erro ao carregar eleitores')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingId(null)
    form.resetFields()
    setIsModalVisible(true)
  }

  const handleEdit = (record: any) => {
    setEditingId(record.id)
    form.setFieldsValue(record)
    setIsModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.deleteEleitor(id)
      message.success('Eleitor deletado com sucesso')
      loadEleitores()
    } catch (error) {
      message.error('Erro ao deletar eleitor')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editingId) {
        await api.updateEleitor(editingId, values)
        message.success('Eleitor atualizado com sucesso')
      } else {
        await api.createEleitor(values)
        message.success('Eleitor criado com sucesso')
      }
      setIsModalVisible(false)
      loadEleitores()
    } catch (error) {
      message.error('Erro ao salvar eleitor')
    }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: 'Nome', dataIndex: 'nome', key: 'nome' },
    { title: 'CPF', dataIndex: 'cpf', key: 'cpf' },
    { title: 'Celular', dataIndex: 'celular', key: 'celular', render: (v: any) => formatCelular(String(v || '')) },
    { title: 'Bairro', dataIndex: 'bairro', key: 'bairro' },
    {
      title: 'Ações',
      key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Confirmar exclusão"
            description="Tem certeza que deseja deletar este eleitor?"
            onConfirm={() => handleDelete(record.id)}
            okText="Sim"
            cancelText="Não"
          >
            <Button type="primary" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      
        <div className="page-actions">
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            NOVO ELEITOR
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={eleitores}
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />

        <Modal
          title={editingId ? 'EDITAR ELEITOR' : 'NOVO ELEITOR'}
          open={isModalVisible}
          onOk={() => form.submit()}
          onCancel={() => setIsModalVisible(false)}
        >
          <Form form={form} layout="vertical" onFinish={handleSubmit}>
            <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="cpf" label="CPF" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="celular" label="Celular">
              <Input maxLength={15} onChange={(e) => {
                const masked = formatCelular(e.target.value)
                form.setFieldsValue({ celular: masked })
              }} />
            </Form.Item>
            <Form.Item name="bairro" label="Bairro">
              <Input />
            </Form.Item>
          </Form>
        </Modal>
    </motion.div>
  )
}
