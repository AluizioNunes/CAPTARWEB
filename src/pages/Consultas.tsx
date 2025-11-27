import { useState } from 'react'
import { Table, Form, Button, Input, Select, DatePicker, Space, Card, Row, Col } from 'antd'
import { SearchOutlined, ClearOutlined, DownloadOutlined } from '@ant-design/icons'

interface QueryResult {
  id: string
  nome: string
  tipo: string
  data: string
  status: string
  resultado: string
}

const Consultas = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<QueryResult[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a: any, b: any) => String(a.id).localeCompare(String(b.id)),
      sortDirections: ['ascend','descend'] as any,
    },
    {
      title: 'NOME',
      dataIndex: 'nome',
      key: 'nome',
      width: 150,
      sorter: (a: any, b: any) => String(a.nome).toUpperCase().localeCompare(String(b.nome).toUpperCase()),
      sortDirections: ['ascend','descend'] as any,
    },
    {
      title: 'TIPO',
      dataIndex: 'tipo',
      key: 'tipo',
      width: 120,
      sorter: (a: any, b: any) => String(a.tipo).toUpperCase().localeCompare(String(b.tipo).toUpperCase()),
      sortDirections: ['ascend','descend'] as any,
    },
    {
      title: 'DATA',
      dataIndex: 'data',
      key: 'data',
      width: 120,
      sorter: (a: any, b: any) => new Date(a.data).getTime() - new Date(b.data).getTime(),
      sortDirections: ['ascend','descend'] as any,
    },
    {
      title: 'STATUS',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      sorter: (a: any, b: any) => String(a.status).toUpperCase().localeCompare(String(b.status).toUpperCase()),
      sortDirections: ['ascend','descend'] as any,
      render: (status: string) => {
        const colors: Record<string, string> = {
          ativo: 'green',
          inativo: 'red',
          pendente: 'orange',
        }
        return <span style={{ color: colors[status] || 'black' }}>{String(status).toUpperCase()}</span>
      },
    },
    {
      title: 'RESULTADO',
      dataIndex: 'resultado',
      key: 'resultado',
      width: 200,
      sorter: (a: any, b: any) => String(a.resultado).toUpperCase().localeCompare(String(b.resultado).toUpperCase()),
      sortDirections: ['ascend','descend'] as any,
    },
  ]

  const handleSearch = async () => {
    setLoading(true)
    try {
      // Simular chamada à API
      const mockResults: QueryResult[] = [
        {
          id: '1',
          nome: 'Eleitor 1',
          tipo: 'Eleitor',
          data: '2025-01-15',
          status: 'ativo',
          resultado: 'Encontrado',
        },
        {
          id: '2',
          nome: 'Ativista 2',
          tipo: 'Ativista',
          data: '2025-01-14',
          status: 'ativo',
          resultado: 'Encontrado',
        },
      ]
      setResults(mockResults)
      setPagination({ ...pagination, total: mockResults.length })
    } catch (error) {
      console.error('Erro ao buscar:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    form.resetFields()
    setResults([])
  }

  const handleExport = () => {
    console.log('Exportando resultados...')
  }

  return (
    <div className="consultas-container">
      <Card title="Consultas Avançadas" className="consultas-card">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSearch}
          className="consultas-form"
        >
          <Row gutter={16}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Buscar por"
                name="searchType"
                initialValue="nome"
              >
                <Select
                  options={[
                    { label: 'Nome', value: 'nome' },
                    { label: 'CPF', value: 'cpf' },
                    { label: 'Email', value: 'email' },
                    { label: 'Telefone', value: 'telefone' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Valor"
                name="searchValue"
                rules={[{ required: true, message: 'Digite um valor' }]}
              >
                <Input placeholder="Digite o valor para buscar" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Tipo"
                name="tipo"
                initialValue="todos"
              >
                <Select
                  options={[
                    { label: 'Todos', value: 'todos' },
                    { label: 'Eleitor', value: 'eleitor' },
                    { label: 'Ativista', value: 'ativista' },
                    { label: 'Usuário', value: 'usuario' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Data Inicial"
                name="dataInicial"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Data Final"
                name="dataFinal"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Status"
                name="status"
                initialValue="todos"
              >
                <Select
                  options={[
                    { label: 'Todos', value: 'todos' },
                    { label: 'Ativo', value: 'ativo' },
                    { label: 'Inativo', value: 'inativo' },
                    { label: 'Pendente', value: 'pendente' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SearchOutlined />}
                loading={loading}
              >
                Buscar
              </Button>
              <Button
                icon={<ClearOutlined />}
                onClick={handleClear}
              >
                Limpar
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={results.length === 0}
              >
                Exportar
              </Button>
            </Space>
          </Form.Item>
        </Form>

        <Table
          columns={columns}
          dataSource={results}
          loading={loading}
          pagination={pagination}
          rowKey="id"
          size="middle"
          bordered
          className="ant-table-striped"
        />
      </Card>
    </div>
  )
}

export default Consultas
