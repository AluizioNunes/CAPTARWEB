import { Layout as AntLayout, Menu, Button, Dropdown } from 'antd'
import { LogoutOutlined, DashboardOutlined, UserOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import './Layout.css'

const { Header, Sider, Content } = AntLayout

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
      onClick: () => navigate('/'),
    },
    {
      key: '/eleitores',
      icon: <UserOutlined />,
      label: 'Eleitores',
      onClick: () => navigate('/eleitores'),
    },
    {
      key: '/ativistas',
      icon: <TeamOutlined />,
      label: 'Ativistas',
      onClick: () => navigate('/ativistas'),
    },
    {
      key: '/usuarios',
      icon: <FileTextOutlined />,
      label: 'Usuários',
      onClick: () => navigate('/usuarios'),
    },
  ]

  const userMenu = {
    items: [
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: 'Logout',
        onClick: handleLogout,
      },
    ],
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={0}>
        <div className="logo">CAPTAR</div>
        <Menu theme="dark" mode="inline" items={menuItems} />
      </Sider>
      <AntLayout>
        <Header className="header">
          <div className="header-content">
            <h2>CAPTAR - Sistema de Gestão Eleitoral</h2>
            <Dropdown menu={userMenu} trigger={['click']}>
              <Button type="text" style={{ color: 'white' }}>
                {user?.nome}
              </Button>
            </Dropdown>
          </div>
        </Header>
        <Content className="content">{children}</Content>
      </AntLayout>
    </AntLayout>
  )
}
