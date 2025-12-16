import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Spin, Select, App as AntdApp } from 'antd'
import * as echarts from 'echarts'
import { useRef } from 'react'
import { UserOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons'
import { useApi } from '../context/ApiContext'
import { motion } from 'framer-motion'

export default function Dashboard() {
  const { message } = AntdApp.useApp()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tenantOptions, setTenantOptions] = useState<{ label: string; value: string }[]>([])
  const tenantSlug = (typeof window !== 'undefined' ? localStorage.getItem('tenantSlug') : null) || 'captar'
  const api = useApi()
  const topUsuariosRef = useRef<HTMLDivElement | null>(null)
  const topAtivistasRef = useRef<HTMLDivElement | null>(null)
  const eleitoresZonaRef = useRef<HTMLDivElement | null>(null)
  const ativistasFuncaoRef = useRef<HTMLDivElement | null>(null)
  const [topUsuarios, setTopUsuarios] = useState<{ name: string; value: number }[]>([])
  const [topAtivistas, setTopAtivistas] = useState<{ name: string; value: number }[]>([])
  const [tenantsCount, setTenantsCount] = useState<number>(0)
  // removidos gráficos adicionais para foco nos KPIs da primeira linha

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
      try {
        const tusu = await api.getTopUsuarios()
        const tusuData = (tusu || []).map((r: any) => ({ name: String(r['Usuário'] ?? r.usuario ?? ''), value: Number(r['Quantidade'] ?? r.qtd ?? 0) }))
        setTopUsuarios(tusuData)
      } catch {}
      try {
        const tati = await api.getTopAtivistas()
        const tatiData = (tati || []).map((r: any) => ({ name: String(r['Categoria'] ?? r.categoria ?? ''), value: Number(r['Quantidade'] ?? r.qtd ?? 0) }))
        setTopAtivistas(tatiData)
      } catch {}
      try {
        const tens = await api.listTenants()
        setTenantsCount((tens.rows || []).length)
      } catch {}
    } catch (error) {
      message.error('Erro ao carregar dados do dashboard')
    } finally {
      setLoading(false)
    }
  }

  // evitar retornar antes de registrar hooks; exibimos spinner dentro do layout

  useEffect(() => {
    if (topUsuariosRef.current) {
      const chart = echarts.init(topUsuariosRef.current)
      chart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: topUsuarios.map(d => d.name), axisLabel: { rotate: 30 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: topUsuarios.map(d => d.value), itemStyle: { color: '#1677ff' } }]
      })
      const r = () => chart.resize()
      window.addEventListener('resize', r)
      return () => { window.removeEventListener('resize', r); chart.dispose() }
    }
    return () => {}
  }, [topUsuarios])

  useEffect(() => {
    if (topAtivistasRef.current) {
      const chart = echarts.init(topAtivistasRef.current)
      chart.setOption({
        tooltip: { trigger: 'item' },
        legend: { top: '3%', left: 'center' },
        series: [{ type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: true, itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }, data: topAtivistas.map(d => ({ name: d.name, value: d.value })) }]
      })
      const r = () => chart.resize()
      window.addEventListener('resize', r)
      return () => { window.removeEventListener('resize', r); chart.dispose() }
    }
    return () => {}
  }, [topAtivistas])

  useEffect(() => {
    if (eleitoresZonaRef.current && stats) {
      const entries = Object.entries(stats.eleitores_por_zona || {})
      const chart = echarts.init(eleitoresZonaRef.current)
      chart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: entries.map(e => String(e[0])), axisLabel: { rotate: 30 } },
        yAxis: { type: 'value' },
        series: [{ type: 'line', smooth: true, data: entries.map(e => Number(e[1])), itemStyle: { color: '#52c41a' } }]
      })
      const r = () => chart.resize()
      window.addEventListener('resize', r)
      return () => { window.removeEventListener('resize', r); chart.dispose() }
    }
    return () => {}
  }, [stats])

  useEffect(() => {
    if (ativistasFuncaoRef.current && stats) {
      const entries = Object.entries(stats.ativistas_por_funcao || {})
      const chart = echarts.init(ativistasFuncaoRef.current)
      chart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: entries.map(e => String(e[0])), axisLabel: { rotate: 30 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: entries.map(e => Number(e[1])), itemStyle: { color: '#faad14' } }]
      })
      const r = () => chart.resize()
      window.addEventListener('resize', r)
      return () => { window.removeEventListener('resize', r); chart.dispose() }
    }
    return () => {}
  }, [stats])

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
        <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
          <Col xs={24} md={12}>
            <Card title="TOP USUÁRIOS (CADASTROS)">
              <div ref={topUsuariosRef} style={{ width: '100%', height: 320 }} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="TOP ATIVISTAS (CATEGORIAS)">
              <div ref={topAtivistasRef} style={{ width: '100%', height: 320 }} />
            </Card>
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
          <Col xs={24} md={12}>
            <Card title="ELEITORES POR ZONA">
              <div ref={eleitoresZonaRef} style={{ width: '100%', height: 300 }} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="ATIVISTAS POR FUNÇÃO">
              <div ref={ativistasFuncaoRef} style={{ width: '100%', height: 300 }} />
            </Card>
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
          <Col xs={24} md={6}>
            <Card>
              <Statistic title="TENANTS" value={tenantsCount} valueStyle={{ fontWeight: 700 }} />
            </Card>
          </Col>
        </Row>
    </motion.div>
  )
}
