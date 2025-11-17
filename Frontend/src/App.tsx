import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import { useAuthStore } from './store/authStore'
import Navbar from './components/Navbar'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import EleitorPage from './pages/EleitorPage'
import AtivistaPage from './pages/AtivistaPage'
import UsuarioPage from './pages/UsuarioPage'
import Permissoes from './pages/Permissoes'
import Estatisticas from './pages/Estatisticas'
import Consultas from './pages/Consultas'
import './App.css'

const { Content } = Layout

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Router>
      {isAuthenticated && <Navbar />}
      <Layout>
        <Content className="app-content">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={isAuthenticated ? <DashboardPage /> : <Navigate to="/login" />}
            />
            <Route
              path="/eleitores"
              element={isAuthenticated ? <EleitorPage /> : <Navigate to="/login" />}
            />
            <Route
              path="/ativistas"
              element={isAuthenticated ? <AtivistaPage /> : <Navigate to="/login" />}
            />
            <Route
              path="/usuarios"
              element={isAuthenticated ? <UsuarioPage /> : <Navigate to="/login" />}
            />
            <Route
              path="/permissoes"
              element={isAuthenticated ? <Permissoes /> : <Navigate to="/login" />}
            />
            <Route
              path="/estatisticas"
              element={isAuthenticated ? <Estatisticas /> : <Navigate to="/login" />}
            />
            <Route
              path="/consultas"
              element={isAuthenticated ? <Consultas /> : <Navigate to="/login" />}
            />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Content>
      </Layout>
    </Router>
  )
}

export default App
