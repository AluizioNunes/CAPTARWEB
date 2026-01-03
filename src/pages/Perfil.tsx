import { useEffect, useState } from 'react'
import { Table, Button, Space, Dropdown, Checkbox, App } from 'antd'
import { useApi } from '../context/ApiContext'
import PerfilModal from '../components/PerfilModal'
import { motion } from 'framer-motion'

// grid dinâmico para tabela perfil

export default function Perfil() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [columnsMeta, setColumnsMeta] = useState<{ name: string; type: string; nullable: boolean }[]>([])
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({})
  const api = useApi()
  const { message } = App.useApp()

  const IconEdit = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z" fill="currentColor"/><path d="M20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" fill="currentColor"/></svg>
  )
  const IconDelete = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M6 7h12M9 7v10m6-10v10M4 7h16l-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
  )
  const IconColumns = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 4h6v16H3V4zm12 0h6v16h-6V4z" fill="currentColor"/></svg>
  )
  const IconPlus = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
  )

  const load = async () => {
    try {
      setLoading(true)
      const schema = await api.getPerfilSchema()
      setColumnsMeta(schema.columns || [])
      const res = await api.listPerfil()
      setData(res.rows || [])
      const vis: Record<string, boolean> = {}
      for (const c of schema.columns || []) vis[c.name] = true
      setVisibleCols(vis)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar perfil')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const baseColumns = columnsMeta.map(col => {
    const dataIndex = col.name
    const uniqueValues = Array.from(new Set((data || []).map(r => r[dataIndex]).filter(v => v !== undefined && v !== null)))
    const filters = uniqueValues.slice(0, 20).map(v => ({ text: String(v).toUpperCase(), value: String(v).toUpperCase() }))
    const type = (col.type || '').toLowerCase()
    const sorter = (a: any, b: any) => {
      const av = a[dataIndex]
      const bv = b[dataIndex]
      if (av === undefined || av === null) return -1
      if (bv === undefined || bv === null) return 1
      if (type.includes('int') || type.includes('numeric')) return Number(av) - Number(bv)
      if (type.includes('date') || type.includes('timestamp')) return new Date(av).getTime() - new Date(bv).getTime()
      return String(av).toUpperCase().localeCompare(String(bv).toUpperCase())
    }
    return {
      title: dataIndex.toUpperCase(),
      dataIndex,
      filters,
      onFilter: (value: any, record: any) => String(record[dataIndex]).toUpperCase() === String(value).toUpperCase(),
      sorter,
      sortDirections: ['ascend', 'descend'] as any,
      render: (v: any) => (typeof v === 'boolean' ? (v ? 'SIM' : 'NÃO') : (v === null || v === undefined ? '' : String(v).toUpperCase())),
    }
  })

  const actionColumn: any = {
    title: 'AÇÕES',
    dataIndex: '__actions__',
    render: (_: any, record: any) => (
      <Space>
        <Button type="text" icon={<IconEdit />} onClick={() => { setEditing(record); setModalOpen(true) }} />
        <Button type="text" danger icon={<IconDelete />} onClick={async () => {
          try {
            if (!record.IdPerfil) { message.info('REGISTRO SEM ID'); return }
            await api.deletePerfil(record.IdPerfil)
            message.success('PERFIL DELETADO')
            await load()
          } catch (e: any) {
            message.error(e?.response?.data?.detail || 'ERRO AO DELETAR PERFIL')
          }
        }} />
      </Space>
    )
  }

  const visibleColumns = baseColumns.filter(c => visibleCols[c.dataIndex]).concat([actionColumn])

  const columnChooser = (
    <div style={{ padding: 12 }}>
      {columnsMeta.map(c => (
        <div key={c.name} style={{ marginBottom: 6 }}>
          <Checkbox
            checked={!!visibleCols[c.name]}
            onChange={(e) => setVisibleCols({ ...visibleCols, [c.name]: e.target.checked })}
          >{c.name}</Checkbox>
        </div>
      ))}
    </div>
  )

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Space>
          <Dropdown placement="bottomRight" trigger={["click"]} menu={{ items: [] }} popupRender={() => columnChooser}>
            <Button icon={<IconColumns />}>COLUNAS</Button>
          </Dropdown>
          <Button type="primary" icon={<IconPlus />} onClick={() => { setEditing(null); setModalOpen(true) }}>NOVO PERFIL</Button>
        </Space>
      </div>
      <Table
        loading={loading}
        dataSource={data}
        columns={visibleColumns as any}
        rowKey={(r, idx) => String((r as any).IdPerfil ?? idx)}
        bordered
        size="middle"
        className="ant-table-striped"
      />
      <PerfilModal
        open={modalOpen}
        initial={editing || undefined}
        onCancel={() => setModalOpen(false)}
        onSaved={async () => { setModalOpen(false); await load() }}
      />
    </motion.div>
  )
}
