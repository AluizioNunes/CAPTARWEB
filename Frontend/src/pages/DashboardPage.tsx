import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Spin, message } from 'antd'
import { UserOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons'
import Layout from '../components/Layout'
import ChartComponent from '../components/ChartComponent'
import apiService from '../services/api'
import './DashboardPage.css'

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [topAtivistas, setTopAtivistas] = useState<any[]>([])
  const [topUsuarios, setTopUsuarios] = useState<any[]>([])
  const [topBairros, setTopBairros] = useState<any[]>([])
  const [topZonas, setTopZonas] = useState<any[]>([])

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [statsData, ativistas, usuarios, bairros, zonas] = await Promise.all([
        apiService.getDashboardStats(),
        apiService.getTopAtivistas(),
        apiService.getTopUsuarios(),
        apiService.getTopBairros(),
        apiService.getTopZonas(),
      ])
      setStats(statsData)
      setTopAtivistas(ativistas)
      setTopUsuarios(usuarios)
      setTopBairros(bairros)
      setTopZonas(zonas)
    } catch (error) {
      message.error('Erro ao carregar dados do dashboard')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="dashboard-loading">
          <Spin size="large" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="dashboard-container">
        <h1>Dashboard</h1>

        <Row gutter={[16, 16]} className="stats-row">
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total de Eleitores"
                value={stats?.total_eleitores || 0}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total de Ativistas"
                value={stats?.total_ativistas || 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total de Usuários"
                value={stats?.total_usuarios || 0}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="charts-row">
          <Col xs={24} lg={12}>
            <Card title="Top Ativistas">
              <ChartComponent
                data={topAtivistas}
                type="bar"
                xField="Ativista"
                yField="Quantidade"
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Top Usuários">
              <ChartComponent
                data={topUsuarios}
                type="bar"
                xField="Usuário"
                yField="Quantidade"
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="charts-row">
          <Col xs={24} lg={12}>
            <Card title="Eleitores por Bairro">
              <ChartComponent
                data={topBairros}
                type="pie"
                xField="Bairro"
                yField="Quantidade"
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Eleitores por Zona">
              <ChartComponent
                data={topZonas}
                type="pie"
                xField="Zona"
                yField="Quantidade"
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Layout>
  )
}
