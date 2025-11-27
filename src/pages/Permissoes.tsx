import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Switch, message, Space, Card, Row, Col } from 'antd'
import { useApi } from '../context/ApiContext'

interface Permissao {
  id: number
  perfil: string
  descricao: string
  pode_criar_eleitor: boolean
  pode_editar_eleitor: boolean
  pode_deletar_eleitor: boolean
  pode_criar_ativista: boolean
  pode_editar_ativista: boolean
  pode_deletar_ativista: boolean
  pode_criar_usuario: boolean
  pode_editar_usuario: boolean
  pode_deletar_usuario: boolean
  pode_enviar_disparos: boolean
  pode_ver_relatorios: boolean
  pode_exportar_dados: boolean
  pode_importar_dados: boolean
  pode_gerenciar_permissoes: boolean
}

export default function Permissoes() {
  const [permissoes, setPermissoes] = useState<Permissao[]>([])
  const [loading, setLoading] = useState(false)
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()
  const api = useApi()

  useEffect(() => {
    loadPermissoes()
  }, [])

  const loadPermissoes = async () => {
    try {
      setLoading(true)
      const data = await api.getPermissoes()
      setPermissoes(data)
    } catch (error) {
      message.error('Erro ao carregar permissões')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (record: Permissao) => {
    setEditingId(record.id)
    form.setFieldsValue(record)
    setIsModalVisible(true)
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editingId) {
        await api.updatePermissao(values.perfil, values)
        message.success('Permissão atualizada com sucesso')
      }
      setIsModalVisible(false)
      loadPermissoes()
    } catch (error) {
      message.error('Erro ao salvar permissão')
    }
  }

  const columns = [
    { title: 'PERFIL', dataIndex: 'perfil', key: 'perfil', sorter: (a: any, b: any) => String(a.perfil).toUpperCase().localeCompare(String(b.perfil).toUpperCase()), sortDirections: ['ascend','descend'] as any },
    { title: 'DESCRIÇÃO', dataIndex: 'descricao', key: 'descricao', sorter: (a: any, b: any) => String(a.descricao).toUpperCase().localeCompare(String(b.descricao).toUpperCase()), sortDirections: ['ascend','descend'] as any },
    {
      title: 'AÇÕES',
      key: 'actions',
      render: (_: any, record: Permissao) => (
        <Space>
          <Button type="text" onClick={() => handleEdit(record)}>
            ✎
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>

        <Table
          columns={columns}
          dataSource={permissoes}
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />

        <Modal
          title={editingId ? 'Editar Permissão' : 'Nova Permissão'}
          open={isModalVisible}
          onOk={() => form.submit()}
          onCancel={() => setIsModalVisible(false)}
          width={800}
        >
          <Form form={form} layout="vertical" onFinish={handleSubmit}>
            <Form.Item name="perfil" label="Perfil" rules={[{ required: true }]}>
              <input disabled />
            </Form.Item>

            <Form.Item name="descricao" label="Descrição">
              <input />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Card title="Eleitores">
                  <Form.Item name="pode_criar_eleitor" valuePropName="checked">
                    <Switch /> Criar
                  </Form.Item>
                  <Form.Item name="pode_editar_eleitor" valuePropName="checked">
                    <Switch /> Editar
                  </Form.Item>
                  <Form.Item name="pode_deletar_eleitor" valuePropName="checked">
                    <Switch /> Deletar
                  </Form.Item>
                </Card>
              </Col>

              <Col span={12}>
                <Card title="Ativistas">
                  <Form.Item name="pode_criar_ativista" valuePropName="checked">
                    <Switch /> Criar
                  </Form.Item>
                  <Form.Item name="pode_editar_ativista" valuePropName="checked">
                    <Switch /> Editar
                  </Form.Item>
                  <Form.Item name="pode_deletar_ativista" valuePropName="checked">
                    <Switch /> Deletar
                  </Form.Item>
                </Card>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Card title="Usuários">
                  <Form.Item name="pode_criar_usuario" valuePropName="checked">
                    <Switch /> Criar
                  </Form.Item>
                  <Form.Item name="pode_editar_usuario" valuePropName="checked">
                    <Switch /> Editar
                  </Form.Item>
                  <Form.Item name="pode_deletar_usuario" valuePropName="checked">
                    <Switch /> Deletar
                  </Form.Item>
                </Card>
              </Col>

              <Col span={12}>
                <Card title="Sistema">
                  <Form.Item name="pode_enviar_disparos" valuePropName="checked">
                    <Switch /> Disparos
                  </Form.Item>
                  <Form.Item name="pode_ver_relatorios" valuePropName="checked">
                    <Switch /> Relatórios
                  </Form.Item>
                  <Form.Item name="pode_exportar_dados" valuePropName="checked">
                    <Switch /> Exportar
                  </Form.Item>
                  <Form.Item name="pode_importar_dados" valuePropName="checked">
                    <Switch /> Importar
                  </Form.Item>
                </Card>
              </Col>
            </Row>
          </Form>
        </Modal>
    </div>
  )
}
