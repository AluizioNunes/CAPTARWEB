import { motion } from 'framer-motion'
import { useState } from 'react'
import { Card, Row, Col, Form, Input, InputNumber, Select, DatePicker, Button, Space, Table, Tag } from 'antd'

interface MetaItem {
  id: string
  nome: string
  tipo: string
  valor: number
  uf?: string
  municipio?: string
  prazo?: string
  status?: string
}

export default function Metas() {
  const [form] = Form.useForm()
  const [data, setData] = useState<MetaItem[]>([])
  const [loading] = useState(false)

  const columns = [
    { title: 'Meta', dataIndex: 'nome' },
    { title: 'Tipo', dataIndex: 'tipo' },
    { title: 'Valor', dataIndex: 'valor' },
    { title: 'UF', dataIndex: 'uf' },
    { title: 'Município', dataIndex: 'municipio' },
    { title: 'Prazo', dataIndex: 'prazo' },
    { title: 'Status', dataIndex: 'status', render: (v: string) => <Tag color={v === 'ATIVA' ? 'green' : 'default'}>{v || '—'}</Tag> },
  ]

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <h1 className="page-title">METAS</h1>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Cadastrar Meta">
            <Form form={form} layout="vertical" onFinish={(values) => {
              const item: MetaItem = {
                id: Math.random().toString(36).slice(2),
                nome: values.nome,
                tipo: values.tipo,
                valor: values.valor,
                uf: values.uf,
                municipio: values.municipio,
                prazo: values.prazo?.format('YYYY-MM-DD'),
                status: 'ATIVA',
              }
              setData([item, ...data])
              form.resetFields()
            }}>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item name="nome" label="Meta" rules={[{ required: true }]}> 
                    <Input placeholder="Ex.: Eleitores cadastrados" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="tipo" label="Tipo" rules={[{ required: true }]}> 
                    <Select options={[{ label: 'Quantidade', value: 'QUANTIDADE' }, { label: 'Percentual', value: 'PERCENTUAL' }]} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item name="valor" label="Valor" rules={[{ required: true }]}> 
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="prazo" label="Prazo"> 
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item name="uf" label="UF"> 
                    <Select options={[{ label: 'Amazonas', value: 'AM' }]} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="municipio" label="Município"> 
                    <Input placeholder="Ex.: Manaus" />
                  </Form.Item>
                </Col>
              </Row>
              <Space>
                <Button type="primary" htmlType="submit" loading={loading}>Salvar</Button>
                <Button onClick={() => form.resetFields()}>Limpar</Button>
              </Space>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <Space>
              <Button>COLUNAS</Button>
              <Button type="primary">NOVA META</Button>
            </Space>
          </div>
          <Table size="middle" bordered dataSource={data} columns={columns.map(c => ({ ...c, title: String(c.title).toUpperCase() }))} rowKey="id" pagination={{ pageSize: 8 }} className="ant-table-striped" />
        </Col>
      </Row>
    </motion.div>
  )
}