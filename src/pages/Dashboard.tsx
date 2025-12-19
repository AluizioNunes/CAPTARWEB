import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Spin, Select } from 'antd'
import { toast } from 'sonner'
import { UserOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons'
import { useApi } from '../context/ApiContext'
import { motion } from 'framer-motion'

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tenantOptions, setTenantOptions] = useState<{ label: string; value: string }[]>([])
  const tenantSlug = (typeof window !== 'undefined' ? localStorage.getItem('tenantSlug') : null) || 'captar'
  const api = useApi()

  useEffect(() => {
    ;(async () => {
      try {
        if (String(tenantSlug).toLowerCase() === 'captar') {
          try { localStorage.setItem('adminContext', '1') } catch {}
          const res = await api.listTenants()
          const rows = res.rows || []
          const others = rows.filter((r: any) => String(r.Slug ?? r.slug).toLowerCase() !== 'captar')
          const opts = others.length > 0
            ? [{ label: 'TODOS OS TENANTS', value: '' }, ...others.map((r: any) => ({ label: String(r.Nome ?? r.nome), value: String(r.Slug ?? r.slug) }))]
            : []
          setTenantOptions(opts)
        } else {
          setTenantOptions([])
        }
      } catch {}
      loadDashboardData()
    })()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const statsData = await api.getDashboardStats()
      setStats(statsData)
    } catch (error) {
      toast.error('Erro ao carregar dados do dashboard')
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div className="dashboard-container" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        {loading && (
          <div className="dashboard-loading" style={{ position: 'relative', zIndex: 1, marginBottom: 12 }}>
            <Spin size="large" />
          </div>
        )}
        {String(tenantSlug).toLowerCase() === 'captar' && tenantOptions.length > 0 && (
          <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: '#666' }}>VISUALIZAR:</span>
            <Select
              style={{ minWidth: 240 }}
              size="small"
              placeholder="Selecionar tenant"
              value={(typeof window !== 'undefined' ? localStorage.getItem('viewTenantSlug') : null) || ''}
              options={tenantOptions}
              onChange={(val) => {
                try {
                  const opt = tenantOptions.find(o => String(o.value).toLowerCase() === String(val).toLowerCase())
                  const name = opt ? opt.label : val
                  if (val) {
                    localStorage.setItem('viewTenantSlug', String(val))
                    localStorage.setItem('viewTenantName', String(name))
                  } else {
                    localStorage.removeItem('viewTenantSlug')
                    localStorage.removeItem('viewTenantName')
                  }
                } catch {}
                loadDashboardData()
              }}
            />
          </div>
        )}
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
