import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import Layout from '../components/Layout'
import apiService from '../services/api'

export default function EleitorPage() {
  const [eleitores, setEleitores] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [editingId, setEditingId] = useState<number | null>(null)

  useEffect(() => {
    loadEleitores()
  }, [])

  const loadEleitores = async () => {
    try {
      setLoading(true)
      const data = await apiService.getEleitores()
      setEleitores(data)
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
      await apiService.deleteEleitor(id)
      message.success('Eleitor deletado com sucesso')
      loadEleitores()
    } catch (error) {
      message.error('Erro ao deletar eleitor')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editingId) {
        await apiService.updateEleitor(editingId, values)
        message.success('Eleitor atualizado com sucesso')
      } else {
        await apiService.createEleitor(values)
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
    { title: 'Celular', dataIndex: 'celular', key: 'celular' },
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
    <Layout>
      <div style={{ padding: '24px' }}>
        <div style={{ marginBottom: '16px' }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Novo Eleitor
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
          title={editingId ? 'Editar Eleitor' : 'Novo Eleitor'}
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
              <Input />
            </Form.Item>
            <Form.Item name="bairro" label="Bairro">
              <Input />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </Layout>
  )
}
