import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Button, Spin, Table, App } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import apiService from '../services/api'

interface DadosEstatisticas {
  totalEleitores: number
  totalAtivistas: number
  totalUsuarios: number
  topAtivistas: any[]
  topUsuarios: any[]
  topBairros: any[]
  topZonas: any[]
  topSupervisores: any[]
  topCoordenadores: any[]
}

export default function Estatisticas() {
  const [dados, setDados] = useState<DadosEstatisticas | null>(null)
  const [carregando, setCarregando] = useState(false)
  const { message } = App.useApp()

  useEffect(() => {
    carregarEstatisticas()
  }, [])

  const carregarEstatisticas = async () => {
    try {
      setCarregando(true)
      const resposta = await apiService.getDashboardStats()
      setDados(resposta)
    } catch (erro) {
      message.error('Erro ao carregar estatísticas')
    } finally {
      setCarregando(false)
    }
  }

  const handleExportar = async (formato: 'pdf' | 'excel') => {
    try {
      await apiService.exportData('eleitores', formato)
      message.success(`Exportação em ${formato.toUpperCase()} iniciada`)
    } catch (erro) {
      message.error('Erro ao exportar dados')
    }
  }

  if (carregando) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      <h1>📊 ESTATÍSTICAS E RELATÓRIOS</h1>

      {/* Botões de Exportação */}
      <Card style={{ marginBottom: '24px' }}>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => handleExportar('excel')}
          style={{ marginRight: '8px' }}
        >
          Exportar Excel
        </Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => handleExportar('pdf')}
        >
          Exportar PDF
        </Button>
      </Card>

      {/* KPIs */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total de Eleitores"
              value={dados?.totalEleitores || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total de Ativistas"
              value={dados?.totalAtivistas || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total de Usuários"
              value={dados?.totalUsuarios || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Taxa de Atividade"
              value={85}
              suffix="%"
              valueStyle={{ color: '#eb2f96' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabelas */}
      <Card title="Top 10 Ativistas" style={{ marginBottom: '24px' }}>
        <Table
          columns={[
            { title: 'NOME', dataIndex: 'nome', key: 'nome', sorter: (a: any, b: any) => String(a.nome).toUpperCase().localeCompare(String(b.nome).toUpperCase()), sortDirections: ['ascend','descend'] as any },
            { title: 'QUANTIDADE', dataIndex: 'quantidade', key: 'quantidade', sorter: (a: any, b: any) => Number(a.quantidade) - Number(b.quantidade), sortDirections: ['ascend','descend'] as any },
          ]}
          dataSource={dados?.topAtivistas || []}
          pagination={{ pageSize: 10 }}
          bordered
          size="middle"
          className="ant-table-striped"
          rowKey="nome"
        />
      </Card>

      <Card title="Top 10 Usuários" style={{ marginBottom: '24px' }}>
        <Table
          columns={[
            { title: 'NOME', dataIndex: 'nome', key: 'nome', sorter: (a: any, b: any) => String(a.nome).toUpperCase().localeCompare(String(b.nome).toUpperCase()), sortDirections: ['ascend','descend'] as any },
            { title: 'QUANTIDADE', dataIndex: 'quantidade', key: 'quantidade', sorter: (a: any, b: any) => Number(a.quantidade) - Number(b.quantidade), sortDirections: ['ascend','descend'] as any },
          ]}
          dataSource={dados?.topUsuarios || []}
          pagination={{ pageSize: 10 }}
          bordered
          size="middle"
          className="ant-table-striped"
          rowKey="nome"
        />
      </Card>

      <Card title="Top 10 Bairros" style={{ marginBottom: '24px' }}>
        <Table
          columns={[
            { title: 'BAIRRO', dataIndex: 'bairro', key: 'bairro', sorter: (a: any, b: any) => String(a.bairro).toUpperCase().localeCompare(String(b.bairro).toUpperCase()), sortDirections: ['ascend','descend'] as any },
            { title: 'QUANTIDADE', dataIndex: 'quantidade', key: 'quantidade', sorter: (a: any, b: any) => Number(a.quantidade) - Number(b.quantidade), sortDirections: ['ascend','descend'] as any },
          ]}
          dataSource={dados?.topBairros || []}
          pagination={{ pageSize: 10 }}
          bordered
          size="middle"
          className="ant-table-striped"
          rowKey="bairro"
        />
      </Card>

      <Card title="Top 10 Zonas" style={{ marginBottom: '24px' }}>
        <Table
          columns={[
            { title: 'ZONA', dataIndex: 'zona', key: 'zona', sorter: (a: any, b: any) => String(a.zona).toUpperCase().localeCompare(String(b.zona).toUpperCase()), sortDirections: ['ascend','descend'] as any },
            { title: 'QUANTIDADE', dataIndex: 'quantidade', key: 'quantidade', sorter: (a: any, b: any) => Number(a.quantidade) - Number(b.quantidade), sortDirections: ['ascend','descend'] as any },
          ]}
          dataSource={dados?.topZonas || []}
          pagination={{ pageSize: 10 }}
          bordered
          size="middle"
          className="ant-table-striped"
          rowKey="zona"
        />
      </Card>

      <Card title="Supervisores com Mais Eleitores" style={{ marginBottom: '24px' }}>
        <Table
          columns={[
            { title: 'SUPERVISOR', dataIndex: 'supervisor', key: 'supervisor', sorter: (a: any, b: any) => String(a.supervisor).toUpperCase().localeCompare(String(b.supervisor).toUpperCase()), sortDirections: ['ascend','descend'] as any },
            { title: 'QUANTIDADE', dataIndex: 'quantidade', key: 'quantidade', sorter: (a: any, b: any) => Number(a.quantidade) - Number(b.quantidade), sortDirections: ['ascend','descend'] as any },
          ]}
          dataSource={dados?.topSupervisores || []}
          pagination={{ pageSize: 10 }}
          bordered
          size="middle"
          className="ant-table-striped"
          rowKey="supervisor"
        />
      </Card>

      <Card title="Coordenadores com Mais Eleitores">
        <Table
          columns={[
            { title: 'COORDENADOR', dataIndex: 'coordenador', key: 'coordenador', sorter: (a: any, b: any) => String(a.coordenador).toUpperCase().localeCompare(String(b.coordenador).toUpperCase()), sortDirections: ['ascend','descend'] as any },
            { title: 'QUANTIDADE', dataIndex: 'quantidade', key: 'quantidade', sorter: (a: any, b: any) => Number(a.quantidade) - Number(b.quantidade), sortDirections: ['ascend','descend'] as any },
          ]}
          dataSource={dados?.topCoordenadores || []}
          pagination={{ pageSize: 10 }}
          bordered
          size="middle"
          className="ant-table-striped"
          rowKey="coordenador"
        />
      </Card>
    </div>
  )
}
