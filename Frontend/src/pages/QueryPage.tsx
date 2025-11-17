import { useState } from 'react'
import { Card, Form, Input, Select, Button, Table, message, Row, Col, Space } from 'antd'
import { SearchOutlined, ClearOutlined } from '@ant-design/icons'
import Layout from '../components/Layout'
import apiService from '../services/api'

interface QueryResult {
  id: number
  [key: string]: any
}

export default function QueryPage() {
  const [form] = Form.useForm()
  const [results, setResults] = useState<QueryResult[]>([])
  const [loading, setLoading] = useState(false)
  const [columns, setColumns] = useState<any[]>([])

  const handleSearch = async (values: any) => {
    try {
      setLoading(true)
      const response = await apiService.applyFilter({
        tipo: values.filterType,
        valor: values.filterValue,
      })
      
      setResults(response)
      
      if (response.length > 0) {
        const keys = Object.keys(response[0])
        setColumns(
          keys.map((key) => ({
            title: key.charAt(0).toUpperCase() + key.slice(1),
            dataIndex: key,
            key: key,
            ellipsis: true,
          }))
        )
      }
      
      message.success(`${response.length} registros encontrados`)
    } catch (error) {
      message.error('Erro ao buscar dados')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    form.resetFields()
    setResults([])
    setColumns([])
  }

  return (
    <Layout>
      <div style={{ padding: '24px' }}>
        <h1>🔍 Consultas Avançadas</h1>

        {/* Formulário de Busca */}
        <Card style={{ marginBottom: '24px' }}>
          <Form form={form} layout="vertical" onFinish={handleSearch}>
            <Row gutter={16}>
              <Col xs={24} sm={12} lg={8}>
                <Form.Item
                  name="filterType"
                  label="Tipo de Filtro"
                  rules={[{ required: true, message: 'Selecione um tipo' }]}
                >
                  <Select placeholder="Selecione o tipo de filtro">
                    <Select.Option value="coordenador">Coordenador</Select.Option>
                    <Select.Option value="supervisor">Supervisor</Select.Option>
                    <Select.Option value="ativista">Ativista</Select.Option>
                    <Select.Option value="bairro">Bairro</Select.Option>
                    <Select.Option value="zona">Zona</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} lg={8}>
                <Form.Item
                  name="filterValue"
                  label="Valor"
                  rules={[{ required: true, message: 'Digite um valor' }]}
                >
                  <Input placeholder="Digite o valor para buscar" />
                </Form.Item>
              </Col>
              <Col xs={24} lg={8} style={{ display: 'flex', alignItems: 'flex-end' }}>
                <Space style={{ width: '100%' }}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SearchOutlined />}
                    loading={loading}
                    block
                  >
                    Buscar
                  </Button>
                  <Button
                    icon={<ClearOutlined />}
                    onClick={handleClear}
                    block
                  >
                    Limpar
                  </Button>
                </Space>
              </Col>
            </Row>
          </Form>
        </Card>

        {/* Resultados */}
        <Card title={`Resultados (${results.length} registros)`}>
          <Table
            columns={columns}
            dataSource={results}
            loading={loading}
            rowKey="id"
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1200 }}
          />
        </Card>
      </div>
    </Layout>
  )
}
