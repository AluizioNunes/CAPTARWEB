import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Layout } from 'antd'
import { useAuthStore } from './store/authStore'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Eleitor from './pages/Eleitor'
import Ativista from './pages/Ativista'
import Usuario from './pages/Usuario'
import Permissoes from './pages/Permissoes'
import Estatisticas from './pages/Estatisticas'
import Consultas from './pages/Consultas'
import Perfil from './pages/Perfil'
import Funcoes from './pages/Funcoes'
import Integracoes from './pages/Integracoes'
import Metas from './pages/Metas'
import Tenants from './pages/Tenants'
import TenantParametros from './pages/TenantParametros'
import './App.css'
import { AnimatePresence, motion } from 'framer-motion'

const { Content } = Layout

function AppRoutes() {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <motion.div key={location.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
        <Routes location={location}>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/eleitores" element={isAuthenticated ? <Eleitor /> : <Navigate to="/login" />} />
          <Route path="/ativistas" element={isAuthenticated ? <Ativista /> : <Navigate to="/login" />} />
          <Route path="/usuarios" element={isAuthenticated ? <Usuario /> : <Navigate to="/login" />} />
          <Route path="/perfil" element={isAuthenticated ? <Perfil /> : <Navigate to="/login" />} />
          <Route path="/funcoes" element={isAuthenticated ? <Funcoes /> : <Navigate to="/login" />} />
          <Route path="/permissoes" element={isAuthenticated ? <Permissoes /> : <Navigate to="/login" />} />
          <Route path="/estatisticas" element={isAuthenticated ? <Estatisticas /> : <Navigate to="/login" />} />
          <Route path="/consultas" element={isAuthenticated ? <Consultas /> : <Navigate to="/login" />} />
          <Route path="/integracoes" element={isAuthenticated ? <Integracoes /> : <Navigate to="/login" />} />
          <Route path="/parametros/metas" element={isAuthenticated ? <Metas /> : <Navigate to="/login" />} />
          <Route path="/parametros/tenants" element={isAuthenticated ? <Tenants /> : <Navigate to="/login" />} />
          <Route path="/parametros/tenant-parametros" element={isAuthenticated ? <TenantParametros /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

function App() {
  const { isAuthenticated } = useAuthStore()
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      {isAuthenticated && <Navbar />}
      <Layout>
        <Content className="app-content">
          <AppRoutes />
        </Content>
      </Layout>
    </Router>
  )
}

export default App
