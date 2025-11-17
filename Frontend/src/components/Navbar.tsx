import { Layout, Button, Dropdown, Avatar } from 'antd'
import { LogoutOutlined, UserOutlined, DownOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import './Navbar.css'

const { Header } = Layout

export default function Navbar() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  if (!user) {
    return null
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const menuItems = [
    {
      key: 'logout',
      label: 'Logout',
      icon: <LogoutOutlined />,
      onClick: handleLogout,
    },
  ]

  return (
    <Header className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo">
          <h2>CAPTAR</h2>
        </div>

        <div className="navbar-content">
          <div className="navbar-user-info">
            <div className="user-details">
              <p className="user-name">{user.nome}</p>
              <p className="user-meta">
                Função: <strong>{user.funcao}</strong> | Perfil: <strong>{user.perfil}</strong>
              </p>
              <p className="user-login-time">Login: {user.login_time}</p>
            </div>
          </div>

          <Dropdown menu={{ items: menuItems }} trigger={['click']}>
            <Button type="text" className="user-menu-button">
              <Avatar icon={<UserOutlined />} size="large" />
              <DownOutlined />
            </Button>
          </Dropdown>

          <Button
            type="primary"
            danger
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            className="logout-button"
          >
            Logout
          </Button>
        </div>
      </div>
    </Header>
  )
}
