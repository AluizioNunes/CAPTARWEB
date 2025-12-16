import { useEffect, useState } from 'react'
import { Table, Button, Space, Modal, Tag, Dropdown, Checkbox, App } from 'antd'
import { motion } from 'framer-motion'
import { useApi } from '../context/ApiContext'
import { useAuthStore } from '../store/authStore'
import TenantsModal from '../components/TenantsModal'
import TenantProvisionModal from '../components/TenantProvisionModal'
import DsnViewModal from '../components/DsnViewModal'

export default function Tenants() {
  const api = useApi()
  const { message, modal } = App.useApp()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [provOpen, setProvOpen] = useState(false)
  const [provInit, setProvInit] = useState<{ nome?: string; slug?: string; db_name?: string; db_host?: string; db_port?: string; db_user?: string; db_password?: string } | undefined>(undefined)
  const [dsnViewOpen, setDsnViewOpen] = useState(false)
  const [dsnView, setDsnView] = useState<string>('')
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({})
  const [orderedKeys, setOrderedKeys] = useState<string[]>([])
  const { user } = useAuthStore()
  const [deleteChoice, setDeleteChoice] = useState<{ open: boolean; record?: any }>({ open: false })

  const refresh = async () => {
    try {
      setLoading(true)
      const res = await api.listTenants()
      const rows = (res.rows || [])
      const withDb = rows.map((r: any) => ({ ...r, __db__: !!r.Dsn, __db_created_at__: r.DbCreatedAt || r.dbCreatedAt || '' }))
      setData((prev) => {
        const locals = (prev || []).filter((r: any) => (r && (r as any).__new__))
        const all = [...locals, ...withDb]
        const uniq: any[] = []
        const seen = new Set<string>()
        for (const r of all) {
          const key = r.IdTenant ? `id:${String(r.IdTenant)}` : `slug:${String(r.Slug || r.slug || '').toUpperCase()}`
          if (seen.has(key)) continue
          seen.add(key)
          uniq.push(r)
        }
        return uniq
      })
      const defaultOrder = ['IdTenant','Nome','Slug','Status','Plano','DataCadastro','DataUpdate','__db__','__db_created_at__','__actions__']
      const visKey = `tenants.columns.visible.${(user as any)?.usuario || 'default'}`
      const savedVis = localStorage.getItem(visKey)
      const visDefault: Record<string, boolean> = {}
      for (const n of defaultOrder) visDefault[n] = true
      setVisibleCols(savedVis ? JSON.parse(savedVis) : { ...visDefault, __db__: true, __db_created_at__: true, __actions__: true })
      const orderKey = `tenants.columns.order.${(user as any)?.usuario || 'default'}`
      const savedOrder = localStorage.getItem(orderKey)
      setOrderedKeys(savedOrder ? JSON.parse(savedOrder) : defaultOrder)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar tenants')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  const titleMap: Record<string, string> = {
    IdTenant: 'ID',
    Nome: 'NOME',
    Slug: 'SLUG',
    Status: 'STATUS',
    Plano: 'PLANO',
    DataCadastro: 'DATA E HORA DE CADASTRO',
    DataUpdate: 'DATA UPDATE'
  }
  const centerCols = new Set(['IdTenant','Status','Plano','DataCadastro','DataUpdate'])
  const baseColumns = ['IdTenant','Nome','Slug','Status','Plano','DataCadastro','DataUpdate'].map((dataIndex) => {
    const colObj: any = {
      title: titleMap[dataIndex] || dataIndex.toUpperCase(),
      dataIndex,
      align: centerCols.has(dataIndex) ? 'center' : 'left',
      sorter: (a: any, b: any) => {
        const av = a[dataIndex]
        const bv = b[dataIndex]
        if (av === undefined || av === null) return -1
        if (bv === undefined || bv === null) return 1
        if (dataIndex === 'IdTenant') return Number(bv) - Number(av)
        if (dataIndex.includes('Data')) return new Date(av).getTime() - new Date(bv).getTime()
        return String(av).toUpperCase().localeCompare(String(bv).toUpperCase())
      },
      sortDirections: ['ascend','descend'] as any,
      render: (v: any) => {
        if (v === null || v === undefined) return ''
        if (dataIndex.includes('Data')) {
          const d = new Date(v)
          if (!isNaN(d.getTime())) return d.toLocaleString('pt-BR', { hour12: false })
        }
        return String(v).toUpperCase()
      },
      onHeaderCell: () => ({
        draggable: true,
        onDragStart: (e: any) => { e.dataTransfer.setData('text/plain', dataIndex) },
        onDragOver: (e: any) => { e.preventDefault() },
        onDrop: (e: any) => {
          const from = e.dataTransfer.getData('text/plain')
          const to = dataIndex
          if (!from || from === to) return
          setOrderedKeys((prev) => {
            const next = prev.filter(k => k !== from)
            const idx = next.indexOf(to)
            if (idx === -1) return prev
            next.splice(idx, 0, from)
            const orderKey = `tenants.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      })
    }
    if (dataIndex === 'IdTenant') colObj.defaultSortOrder = 'descend'
    return colObj
  })

  const extraColumns: any[] = [
    { 
      title: 'DB', 
      dataIndex: '__db__', 
      align: 'center',
      sorter: (a: any, b: any) => (a.__db__ === b.__db__) ? 0 : (a.__db__ ? -1 : 1),
      sortDirections: ['ascend','descend'] as any,
      onHeaderCell: () => ({
        draggable: true,
        onDragStart: (e: any) => { e.dataTransfer.setData('text/plain', '__db__') },
        onDragOver: (e: any) => { e.preventDefault() },
        onDrop: (e: any) => {
          const from = e.dataTransfer.getData('text/plain')
          const to = '__db__'
          if (!from || from === to) return
          setOrderedKeys((prev) => {
            const next = prev.filter(k => k !== from)
            const idx = next.indexOf(to)
            if (idx === -1) return prev
            next.splice(idx, 0, from)
            const orderKey = `tenants.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      }),
      onCell: () => ({ title: 'Estado do DSN do Tenant' }),
      render: (v: any) => (v ? <Tag color="green">CRIADO</Tag> : <Tag>NAO CRIADO</Tag>) 
    },
    { 
      title: 'DB CRIADO', 
      dataIndex: '__db_created_at__', 
      align: 'center',
      sorter: (a: any, b: any) => {
        const av = a.__db_created_at__
        const bv = b.__db_created_at__
        if (!av && !bv) return 0
        if (!av) return 1
        if (!bv) return -1
        return new Date(av).getTime() - new Date(bv).getTime()
      },
      sortDirections: ['ascend','descend'] as any,
      onHeaderCell: () => ({
        draggable: true,
        onDragStart: (e: any) => { e.dataTransfer.setData('text/plain', '__db_created_at__') },
        onDragOver: (e: any) => { e.preventDefault() },
        onDrop: (e: any) => {
          const from = e.dataTransfer.getData('text/plain')
          const to = '__db_created_at__'
          if (!from || from === to) return
          setOrderedKeys((prev) => {
            const next = prev.filter(k => k !== from)
            const idx = next.indexOf(to)
            if (idx === -1) return prev
            next.splice(idx, 0, from)
            const orderKey = `tenants.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      }),
      render: (v: any) => (v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—') 
    },
    {
      title: 'AÇÕES',
      dataIndex: '__actions__',
      align: 'center',
      onHeaderCell: () => ({
        draggable: true,
        onDragStart: (e: any) => { e.dataTransfer.setData('text/plain', '__actions__') },
        onDragOver: (e: any) => { e.preventDefault() },
        onDrop: (e: any) => {
          const from = e.dataTransfer.getData('text/plain')
          const to = '__actions__'
          if (!from || from === to) return
          setOrderedKeys((prev) => {
            const next = prev.filter(k => k !== from)
            const idx = next.indexOf(to)
            if (idx === -1) return prev
            next.splice(idx, 0, from)
            const orderKey = `tenants.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      }),
      render: (_: any, record: any) => {
        const slug = String(record.Slug ?? record.slug ?? '').toLowerCase()
        const isSystemTenant = slug === 'captar'
        if (isSystemTenant) {
          return <Tag color="geekblue">TENANT PADRÃO DO SISTEMA</Tag>
        }
        return (
          <Space>
            <Button type="text" onClick={() => { setEditing(record); setModalOpen(true) }}>EDITAR</Button>
            <Button type="text" danger onClick={() => {
              setDeleteChoice({ open: true, record })
            }}>DELETAR</Button>
            <Button type="text" onClick={() => { setDsnView(String(record.Dsn || '—')); setDsnViewOpen(true) }}>VER DSN</Button>
            {record.__db__ ? (
              <Button danger onClick={() => {
                modal.confirm({
                  title: 'Deseja realmente apagar o banco e recriá-lo?',
                  okText: 'Sobrescrever',
                  okButtonProps: { danger: true },
                  cancelText: 'Cancelar',
                  onOk: async () => {
                    try {
                      const s = String(record.Slug || '').toLowerCase()
                      const res = await api.recreateTenantDb(s)
                      message.success(`Banco recriado: ${res.dsn}`)
                      await refresh()
                    } catch (e: any) {
                      message.error(e?.response?.data?.detail || 'Erro ao sobrescrever banco')
                    }
                  }
                })
              }}>SOBRESCREVER O BANCO DE DADOS</Button>
            ) : (
              <Button type="primary" onClick={() => {
                const id = record.IdTenant
                const s = String(record.Slug || '').toLowerCase()
                const nome = String(record.Nome || '')
                const db_name = `captar_t${String(id).padStart(2,'0')}_${s}`
                setProvInit({ nome, slug: s, db_name, db_host: 'postgres', db_port: '5432', db_user: 'captar', db_password: 'captar' })
                setProvOpen(true)
              }}>CRIAR BANCO DE DADOS</Button>
            )}
          </Space>
        )
      }
    }
  ]

  const allColumns = [...baseColumns, ...extraColumns]
  const orderedVisible = orderedKeys.length ? orderedKeys : allColumns.map(c => c.dataIndex)
  const visibleColumns = orderedVisible
    .map(k => allColumns.find(c => c.dataIndex === k))
    .filter(Boolean)
    .filter((c: any) => visibleCols[(c as any).dataIndex])

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Space>
          <Dropdown placement="bottomRight" trigger={["click"]} menu={{ items: [] }} popupRender={() => (
            <div style={{ padding: 12 }}>
              {Object.keys(visibleCols).map(k => (
                <div key={k} style={{ marginBottom: 6 }}>
                  <Checkbox checked={!!visibleCols[k]} onChange={(e) => {
                    const next = { ...visibleCols, [k]: e.target.checked }
                    setVisibleCols(next)
                    const visKey = `tenants.columns.visible.${(user as any)?.usuario || 'default'}`
                    localStorage.setItem(visKey, JSON.stringify(next))
                  }}>{k.toUpperCase()}</Checkbox>
                </div>
              ))}
            </div>
          )}>
            <Button shape="circle" style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} title="VISUALIZAÇÃO DE COLUNAS" />
          </Dropdown>
          <Button shape="circle" style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} onClick={() => { setEditing(null); setModalOpen(true) }} title="NOVO TENANT" />
        </Space>
      </div>
      <style>{`
        .tenants-table .ant-table-thead > tr > th{ background:#FFD700; color:#000; font-family: 'Arimo', Arial, sans-serif; }
        .tenants-table .ant-table-thead > tr > th .ant-table-column-title{ display:flex; justify-content:center; align-items:center; text-align:center; }
        .tenants-table .ant-table-tbody > tr > td{ font-family: 'Roboto Condensed', Arial, sans-serif; padding:2px 6px; line-height:0.95; height:22px; }
      `}</style>
      <Table rowKey={(r) => r.IdTenant || JSON.stringify(r)} loading={loading} dataSource={data} columns={visibleColumns as any} bordered size="small" className="ant-table-striped tenants-table" />
      <TenantsModal
        open={modalOpen}
        initial={editing || undefined}
        onCancel={() => setModalOpen(false)}
        onSaved={async (row) => {
          setModalOpen(false)
          setEditing(null)
          const nextRow = { __db__: false, __db_created_at__: '', ...row }
          setData((prev) => {
            const filtered = (prev || []).filter((v) => Number((v as any).IdTenant) !== Number((nextRow as any).IdTenant))
            return [nextRow, ...filtered]
          })
          window.setTimeout(() => { refresh() }, nextRow.__new__ ? 1200 : 0)
        }}
      />
      <TenantProvisionModal
        open={provOpen}
        initial={provInit}
        onCancel={() => setProvOpen(false)}
        onSaved={async () => { setProvOpen(false); await refresh() }}
      />
      <DsnViewModal open={dsnViewOpen} dsn={dsnView} onCancel={() => setDsnViewOpen(false)} />
      <Modal
        open={deleteChoice.open}
        title={'Apagar Tenant'}
        onCancel={() => setDeleteChoice({ open: false })}
        footer={null}
      >
        <style>{`.tenants-delete-modal .ant-modal-header{ border-bottom: 1px solid #e8e8e8; } .tenants-delete-modal .ant-modal-content{ border-radius: 0 !important; }`}</style>
        <div style={{ marginBottom: 16, fontSize: 14 }}>
          Esta ação pode remover o tenant e opcionalmente o seu banco de dados.
        </div>
        <Space style={{ display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
          <Button onClick={() => setDeleteChoice({ open: false })}>Cancelar</Button>
          <Button danger style={{ borderRadius: 20 }} onClick={async () => {
            try {
              const rec = deleteChoice.record
              if (!rec) return
              await api.deleteTenant(Number(rec.IdTenant))
              setData((prev) => prev.filter(r => Number(r.IdTenant) !== Number(rec.IdTenant)))
              message.success('Tenant apagado (banco mantido)')
              setDeleteChoice({ open: false })
              await refresh()
            } catch (e: any) {
              message.error(e?.response?.data?.detail || 'Erro ao deletar tenant')
            }
          }}>Deletar somente o tenant (manter banco)</Button>
          <Button danger type="primary" style={{ borderRadius: 20 }} onClick={async () => {
            try {
              const rec = deleteChoice.record
              if (!rec) return
              const slug = String(rec.Slug || '').toLowerCase()
              await api.deleteTenantAndDb(slug)
              setData((prev) => prev.filter(r => Number(r.IdTenant) !== Number(rec.IdTenant)))
              message.success('Tenant e banco apagados')
              setDeleteChoice({ open: false })
              await refresh()
            } catch (e: any) {
              message.error(e?.response?.data?.detail || 'Erro ao deletar tenant e banco')
            }
          }}>Deletar tenant e banco de dados</Button>
        </Space>
      </Modal>
    </motion.div>
  )
}
