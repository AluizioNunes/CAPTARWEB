import React from 'react'
import { Layout, Button, Dropdown, Avatar, Menu } from 'antd'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'
import { LogoutOutlined, UserOutlined, DownOutlined, DashboardOutlined, TeamOutlined, FileTextOutlined, SettingOutlined, ApiOutlined } from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useApi } from '../context/ApiContext'
import { motion } from 'framer-motion'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const { Header } = Layout

function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const api = useApi()
  const tenantSlug = (typeof window !== 'undefined' ? localStorage.getItem('tenantSlug') : null) || 'captar'
  const [tenantName, setTenantName] = useState<string>(localStorage.getItem('tenantName') || '')
  useEffect(() => {
    const slug = (localStorage.getItem('tenantSlug') || 'captar')
    ;(async () => {
      try {
        const res = await api.listTenants()
        const rows = res.rows || []
        const t = rows.find((r: any) => String(r.Slug ?? r.slug).toUpperCase() === String(slug).toUpperCase())
        const name = t ? String(t.Nome ?? t.nome) : slug
        setTenantName(name)
        try { localStorage.setItem('tenantName', name) } catch {}
      } catch {
        setTenantName(slug)
      }
    })()
  }, [api])

  if (!user) {
    return null
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const loginDateObj = useMemo(() => {
    const lt = user?.login_time
    if (!lt) return null
    const dIso = parseISO(lt)
    if (isValid(dIso)) return dIso
    const d = new Date(lt)
    return isNaN(d.getTime()) ? null : d
  }, [user?.login_time])

  const loginText = loginDateObj ? format(loginDateObj, 'dd/MM/yyyy HH:mm', { locale: ptBR }) : ''

  const [connectionText, setConnectionText] = useState('')
  useEffect(() => {
    const update = () => {
      if (!loginDateObj) {
        setConnectionText('')
        return
      }
      const diff = Date.now() - loginDateObj.getTime()
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      const hh = String(h).padStart(2, '0')
      const mm = String(m).padStart(2, '0')
      const ss = String(s).padStart(2, '0')
      setConnectionText(`${hh}:${mm}:${ss}`)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [loginDateObj])

  const userMenuItems = [
    {
      key: 'logout',
      label: 'LOGOUT',
      icon: <LogoutOutlined />,
      onClick: handleLogout,
    },
  ]

  const topMenuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'DASHBOARD', onClick: () => navigate('/') },
    {
      key: 'cadastros',
      icon: <UserOutlined />,
      label: 'CADASTROS',
      children: [
        { key: '/eleitores', icon: <UserOutlined />, label: 'ELEITORES', onClick: () => navigate('/eleitores') },
        { key: '/ativistas', icon: <TeamOutlined />, label: 'ATIVISTAS', onClick: () => navigate('/ativistas') },
      ],
    },
    { key: '/estatisticas', icon: <FileTextOutlined />, label: 'ESTATÍSTICAS', onClick: () => navigate('/estatisticas') },
    { key: '/consultas', icon: <FileTextOutlined />, label: 'CONSULTAS', onClick: () => navigate('/consultas') },
    {
      key: 'sistema',
      icon: <SettingOutlined />,
      label: 'SISTEMA',
      children: [
        { key: '/usuarios', icon: <FileTextOutlined />, label: 'USUÁRIOS', onClick: () => navigate('/usuarios') },
        { key: '/perfil', icon: <UserOutlined />, label: 'PERFIL', onClick: () => navigate('/perfil') },
        { key: '/funcoes', icon: <UserOutlined />, label: 'FUNÇÕES', onClick: () => navigate('/funcoes') },
        { key: '/permissoes', icon: <FileTextOutlined />, label: 'PERMISSÕES', onClick: () => navigate('/permissoes') },
        { key: '/integracoes', icon: <ApiOutlined />, label: 'INTEGRAÇÕES', onClick: () => navigate('/integracoes') },
      ],
    },
    {
      key: 'parametros',
      icon: <FileTextOutlined />,
      label: 'PARÂMETROS',
      children: (() => {
        const items = [
          { key: '/parametros/metas', icon: <FileTextOutlined />, label: 'METAS', onClick: () => navigate('/parametros/metas') },
          { key: '/parametros/tenants', icon: <FileTextOutlined />, label: 'TENANTS', onClick: () => navigate('/parametros/tenants') },
          { key: '/parametros/tenant-parametros', icon: <FileTextOutlined />, label: 'TENANT PARÂMETROS', onClick: () => navigate('/parametros/tenant-parametros') },
        ]
        const slug = String(tenantSlug || '').toLowerCase()
        if (slug !== 'captar') {
          return items.filter(i => i.key !== '/parametros/tenants' && i.key !== '/parametros/tenant-parametros')
        }
        return items
      })(),
    },
  ]

  return (
    <Header className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo" style={{ height: '100%', display: 'flex', alignItems: 'center' }}>
          <img src={Logo} alt="CAPTAR" style={{ height: 110, backgroundColor: '#ffffff', borderRadius: 8, padding: 6 }} />
          <span style={{ marginLeft: 12, fontSize: 12, color: '#666', letterSpacing: '.3px' }}>
            TENANT: <strong style={{ color: '#333' }}>{String(tenantName || tenantSlug).toUpperCase()}</strong>
          </span>
        </div>

        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={topMenuItems}
            className="navbar-menu"
          />
        </motion.div>

        <div className="navbar-content">
          <div className="navbar-user-info">
            <div className="user-details">
              <p className="user-name">{user.nome}</p>
              <p className="user-meta">
                Função: <strong>{user.funcao}</strong> | Perfil: <strong>{user.perfil}</strong>
              </p>
              <p className="user-login-time">LOGIN: {loginText} | TEMPO CONECTADO: {connectionText}</p>
            </div>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <Dropdown menu={{ items: userMenuItems }} trigger={['click']}>
              <Button type="text" className="user-menu-button">
                <Avatar icon={<UserOutlined />} size="large" />
                <DownOutlined />
              </Button>
            </Dropdown>
          </motion.div>

          
        </div>
      </div>
    </Header>
  )
}

export default React.memo(Navbar)
