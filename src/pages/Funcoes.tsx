import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Table, Button, Space, message, Dropdown, Checkbox } from 'antd'
import { useApi } from '../context/ApiContext'
import FuncoesModal from '../components/FuncoesModal'

export default function Funcoes() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [columnsMeta, setColumnsMeta] = useState<{ name: string; type: string; nullable: boolean }[]>([])
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({})
  const api = useApi()

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

  const baseColumns: any[] = (columnsMeta || []).map(c => ({ title: c.name, dataIndex: c.name }))

  const load = async () => {
    try {
      setLoading(true)
      const schema = await api.getFuncoesSchema()
      setColumnsMeta(schema.columns || [])
      const res = await api.listFuncoes()
      setData(res.rows || [])
      const vis: Record<string, boolean> = {}
      for (const c of schema.columns || []) vis[c.name] = true
      setVisibleCols(vis)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar funções')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const actionColumn = {
    title: 'Ações',
    key: 'actions',
    render: (_: any, record: any) => (
      <Space>
        <Button type="text" icon={<IconEdit />} onClick={() => { setEditing(record); setModalOpen(true) }} />
        <Button type="text" danger icon={<IconDelete />} onClick={async () => {
          try {
            if (!record.IdFuncao) { message.info('REGISTRO SEM ID'); return }
            await api.deleteFuncao(record.IdFuncao)
            message.success('Função deletada')
            await load()
          } catch (e: any) {
            message.error(e?.response?.data?.detail || 'Erro ao deletar função')
          }
        }} />
      </Space>
    )
  }

  const visibleColumns: any[] = baseColumns.filter((c: any) => visibleCols[c.dataIndex as string]).concat([actionColumn])

  const columnChooser = (
    <div style={{ padding: 12 }}>
      {baseColumns.map(c => (
        <div key={c.dataIndex as string} style={{ marginBottom: 6 }}>
          <Checkbox
            checked={!!visibleCols[c.dataIndex as string]}
            onChange={(e) => setVisibleCols({ ...visibleCols, [c.dataIndex as string]: e.target.checked })}
          >{c.title}</Checkbox>
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
          <Button type="primary" icon={<IconPlus />} onClick={() => { setEditing(null); setModalOpen(true) }}>NOVA FUNÇÃO</Button>
        </Space>
      </div>

      <Table
        bordered
        size="small"
        loading={loading}
        columns={visibleColumns as any[]}
        dataSource={data}
        rowKey={(r) => r.IdFuncao}
      />

      <FuncoesModal
        open={modalOpen}
        initial={editing}
        onCancel={() => setModalOpen(false)}
        onSaved={async () => { setModalOpen(false); await load() }}
      />
    </motion.div>
  )
}