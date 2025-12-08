import { Modal, Avatar } from 'antd'
import { useMemo, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { format, parseISO, isValid } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Logo from '../images/CAPTAR LOGO OFICIAL.jpg'

interface Props {
  open: boolean
  dsn?: string
  onCancel: () => void
}

export default function DsnViewModal({ open, dsn, onCancel }: Props) {
  const { user } = useAuthStore()
  const [connectionText] = useState('')
  const loginDateObj = useMemo(() => {
    const lt = (user as any)?.login_time
    if (!lt) return null as Date | null
    const dIso = parseISO(lt as any)
    if (isValid(dIso)) return dIso
    const d = new Date(lt as any)
    return isNaN(d.getTime()) ? null : d
  }, [user])
  const loginText = loginDateObj ? format(loginDateObj, 'dd/MM/yyyy HH:mm', { locale: ptBR }) : ''
  const currentTenantSlug = String(localStorage.getItem('tenantSlug') || 'captar')
  const currentTenantName = String(localStorage.getItem('tenantName') || 'CAPTAR')

  return (
    <Modal
      open={open}
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="navbar-logo" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src={Logo} alt="CAPTAR" style={{ height: 110, backgroundColor: '#ffffff', borderRadius: 8, padding: 6 }} />
            <div style={{ fontSize: 12 }}>
              TENANT: <strong style={{ color: '#333' }}>{String(currentTenantName || currentTenantSlug).toUpperCase()}</strong>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: 700 }}>
                {(user as any)?.usuario ? String((user as any)?.usuario).toUpperCase() : String((user as any)?.nome || '').toUpperCase() || 'USUÁRIO'}
              </div>
              <div style={{ fontSize: 12 }}>
                {`FUNÇÃO: ${String((user as any)?.funcao || '').toUpperCase()} | PERFIL: ${String((user as any)?.perfil || '').toUpperCase()}`}
              </div>
              <div style={{ fontSize: 12 }}>
                {`LOGIN: ${loginText || '--'} | TEMPO CONECTADO: ${connectionText || '--:--:--'}`}
              </div>
            </div>
            <Avatar size="large" />
          </div>
        </div>
      }
      onCancel={onCancel}
      footer={null}
      destroyOnHidden
      width={800}
      closable={false}
      maskClosable={false}
      className="tenants-modal"
    >
      <style>{`.tenants-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .tenants-modal .ant-modal-content{ border-radius: 0 !important; }`}</style>
      <div style={{ fontFamily: 'monospace' }}>{dsn || '—'}</div>
    </Modal>
  )
}

