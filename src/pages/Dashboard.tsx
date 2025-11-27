import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Spin, message } from 'antd'
import { UserOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons'
import { useApi } from '../context/ApiContext'
import { motion } from 'framer-motion'

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const api = useApi()
  // removidos gráficos adicionais para foco nos KPIs da primeira linha

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const statsData = await api.getDashboardStats()
      setStats(statsData)
    } catch (error) {
      message.error('Erro ao carregar dados do dashboard')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="dashboard-loading">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <motion.div className="dashboard-container" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        <Row gutter={[16, 16]} className="stats-row">
          <Col xs={24} sm={12} md={8} xl={8}>
            <Card style={{ background: '#e6f4ff' }} hoverable>
              <Statistic
                title="TOTAL DE ELEITORES"
                value={stats?.total_eleitores || 0}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#1677ff', fontWeight: 700 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} xl={8}>
            <Card style={{ background: '#f6ffed' }} hoverable>
              <Statistic
                title="TOTAL DE ATIVISTAS"
                value={stats?.total_ativistas || 0}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#52c41a', fontWeight: 700 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} xl={8}>
            <Card style={{ background: '#fff7e6' }} hoverable>
              <Statistic
                title="TOTAL DE USUÁRIOS"
                value={stats?.total_usuarios || 0}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: '#faad14', fontWeight: 700 }}
              />
            </Card>
          </Col>
        </Row>
    </motion.div>
  )
}
