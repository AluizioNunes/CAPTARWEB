import { Layout, Menu, Dropdown, Avatar } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { useMemo, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useAuthStore } from '../store/authStore'

const { Header, Sider, Content } = Layout

export default function AppShell({ children }: { children: any }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, user } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)
  const [nowText, setNowText] = useState('')

  useEffect(() => {
    const tick = () => setNowText(format(new Date(), 'dd/MM/yyyy HH:mm', { locale: ptBR }))
    tick()
    const id = setInterval(tick, 1000 * 30)
    return () => clearInterval(id)
  }, [])

  const items = useMemo(() => ([
    {
      key: 'dashboard', label: 'Dashboard', onClick: () => navigate('/')
    },
    {
      key: 'operacoes', label: 'Operações', children: [
        { key: 'eleitores', label: 'Eleitores', onClick: () => navigate('/eleitores') },
        { key: 'ativistas', label: 'Ativistas', onClick: () => navigate('/ativistas') },
        { key: 'estatisticas', label: 'Estatísticas', onClick: () => navigate('/estatisticas') },
      ]
    },
    {
      key: 'cadastros', label: 'Cadastros', children: [
        { key: 'usuarios', label: 'Usuários', onClick: () => navigate('/usuarios') },
        { key: 'perfil', label: 'Perfis', onClick: () => navigate('/perfil') },
        { key: 'funcoes', label: 'Funções', onClick: () => navigate('/funcoes') },
        { key: 'permissoes', label: 'Permissões', onClick: () => navigate('/permissoes') },
      ]
    },
    {
      key: 'almox', label: 'Almoxarifado', children: [
        { key: 'almox-estoque', label: 'Estoque', onClick: () => navigate('/almox/estoque') },
        { key: 'almox-entradas', label: 'Entradas', onClick: () => navigate('/almox/entradas') },
        { key: 'almox-saidas', label: 'Saídas', onClick: () => navigate('/almox/saidas') },
        { key: 'almox-fornecedores', label: 'Fornecedores', onClick: () => navigate('/almox/fornecedores') },
        { key: 'almox-pedidos', label: 'Pedidos', onClick: () => navigate('/almox/pedidos') },
        { key: 'almox-relatorios', label: 'Relatórios', onClick: () => navigate('/almox/relatorios') },
      ]
    },
    {
      key: 'integracoes', label: 'Integrações', onClick: () => navigate('/integracoes')
    },
    {
      key: 'parametros', label: 'Parâmetros', children: [
        { key: 'tenants', label: 'Tenants', onClick: () => navigate('/parametros/tenants') },
        { key: 'tenant-parametros', label: 'Tenant Parametros', onClick: () => navigate('/parametros/tenant-parametros') },
        { key: 'metas', label: 'Metas', onClick: () => navigate('/parametros/metas') },
      ]
    },
  ]), [navigate])

  const selectedKeys = useMemo(() => {
    const p = location.pathname
    if (p.startsWith('/almox/')) return [p.replace('/','').replace(/\//g,'-')]
    const key = p === '/' ? 'dashboard' : p.replace('/','')
    return [key]
  }, [location.pathname])

  const userMenu = {
    items: [
      { key: 'logout', label: 'Sair', onClick: () => { localStorage.clear(); window.location.href = '/login' } },
    ]
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {isAuthenticated && (
        <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={240} theme="light">
          <div style={{ padding: 16, fontWeight: 700 }}>CAPTAR</div>
          <Menu mode="inline" selectedKeys={selectedKeys as any} items={items as any} />
        </Sider>
      )}
      <Layout>
        {isAuthenticated && (
          <Header style={{ background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingInline: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ fontSize: 12, color: '#666' }}>{nowText}</div>
            </div>
            <Dropdown menu={userMenu as any} placement="bottomRight">
              <Avatar style={{ backgroundColor: '#FFD700', color: '#000' }}>{String((user as any)?.usuario || 'U')[0].toUpperCase()}</Avatar>
            </Dropdown>
          </Header>
        )}
        <Content style={{ padding: 16 }}>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            {children}
          </motion.div>
        </Content>
      </Layout>
    </Layout>
  )
}

