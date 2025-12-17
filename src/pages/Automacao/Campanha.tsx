import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Table, Button, Space, message, Dropdown, Checkbox, Tag } from 'antd'
import { useAuthStore } from '../../store/authStore'
import { useApi } from '../../context/ApiContext'
import CampanhasModal from '../../components/CampanhasModal'

export default function Campanha() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [columnsMeta, setColumnsMeta] = useState<{ name: string; type: string; nullable: boolean; maxLength?: number }[]>([])
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({})
  const [orderedKeys, setOrderedKeys] = useState<string[]>([])
  const api = useApi()
  const { user } = useAuthStore()

  const IconEdit = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z" fill="currentColor"/><path d="M20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" fill="currentColor"/></svg>
  )
  const IconDelete = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M6 7h12M9 7v10m6-10v10M4 7h16l-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
  )
  const IconColumns = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 4h6v16H3V4zm12 0h6v16h-6V4z" fill="currentColor"/></svg>
  )
  const IconAdd = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )

  const load = async () => {
    try {
      setLoading(true)
      const schema = await api.getCampanhasSchema()
      const defaultOrder = [
        'id',
        'nome',
        'status',
        'meta',
        'enviados',
        'aguardando',
        'data_inicio',
        'data_fim',
        'created_at',
      ]
      const byName: Record<string, { name: string; type: string; nullable: boolean }> = {}
      for (const c of schema.columns || []) byName[c.name] = c
      const ordered = defaultOrder.filter(n => byName[n]).map(n => byName[n])
      const rest = (schema.columns || []).filter(c => !defaultOrder.includes(c.name))
      setColumnsMeta([...ordered, ...rest])
      
      const res = await api.getCampanhas()
      const rows = res.rows || []
      setData(rows)

      const visDefault: Record<string, boolean> = {}
      for (const n of defaultOrder) if (byName[n]) visDefault[n] = true
      for (const c of rest) visDefault[c.name] = false
      
      const visKey = `campanhas.columns.visible.${(user as any)?.usuario || 'default'}`
      const savedVis = localStorage.getItem(visKey)
      setVisibleCols(savedVis ? JSON.parse(savedVis) : visDefault)
      
      const orderKey = `campanhas.columns.order.${(user as any)?.usuario || 'default'}`
      const savedOrder = localStorage.getItem(orderKey)
      setOrderedKeys(savedOrder ? JSON.parse(savedOrder) : defaultOrder.filter(n => byName[n]))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar campanhas')
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
      if (type.includes('int') || type.includes('numeric') || type.includes('decimal')) return Number(av) - Number(bv)
      if (type.includes('date') || type.includes('timestamp')) return new Date(av).getTime() - new Date(bv).getTime()
      return String(av).toUpperCase().localeCompare(String(bv).toUpperCase())
    }

    const titleMap: Record<string, string> = {
      id: 'ID',
      nome: 'NOME DA CAMPANHA',
      descricao: 'DESCRIÇÃO',
      status: 'STATUS',
      data_inicio: 'INÍCIO',
      data_fim: 'FIM',
      meta: 'META',
      enviados: 'ENVIADOS',
      nao_enviados: 'NÃO ENVIADOS',
      positivos: 'POSITIVOS',
      negativos: 'NEGATIVOS',
      aguardando: 'AGUARDANDO',
      created_at: 'CRIADO EM',
    }

    const centerCols = new Set(['id', 'status', 'data_inicio', 'data_fim', 'created_at'])

    return {
      title: titleMap[dataIndex] || dataIndex.toUpperCase(),
      dataIndex,
      align: centerCols.has(dataIndex) ? 'center' : 'left',
      filters,
      onFilter: (value: any, record: any) => String(record[dataIndex]).toUpperCase() === String(value).toUpperCase(),
      sorter,
      render: (v: any) => {
          if (v === null || v === undefined) return ''
          if (type.includes('date') || type.includes('timestamp')) {
             const d = new Date(v)
             if (!isNaN(d.getTime())) return d.toLocaleDateString('pt-BR')
          }
          if (dataIndex === 'status') {
            let color = 'default'
            if (String(v).toUpperCase() === 'PLANEJAMENTO') color = 'blue'
            if (String(v).toUpperCase() === 'EM_ANDAMENTO') color = 'green'
            if (String(v).toUpperCase() === 'CONCLUIDA') color = 'orange'
            if (String(v).toUpperCase() === 'CANCELADA') color = 'red'
            return <Tag color={color}>{String(v).toUpperCase()}</Tag>
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
            const orderKey = `campanhas.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      })
    }
  })

  const actionColumn: any = {
    title: 'AÇÕES',
    dataIndex: '__actions__',
    align: 'center',
    render: (_: any, record: any) => (
      <Space>
        <Button type="text" icon={<IconEdit />} title="EDITAR" onClick={() => { setEditing(record); setModalOpen(true) }} />
        <Button type="text" danger icon={<IconDelete />} title="DELETAR" onClick={async () => {
          try {
            if (!record.id) { message.info('REGISTRO SEM ID'); return }
            await api.deleteCampanha(record.id)
            message.success('CAMPANHA DELETADA')
            await load()
          } catch (e: any) {
            message.error(e?.response?.data?.detail || 'ERRO AO DELETAR CAMPANHA')
          }
        }} />
      </Space>
    )
  }

  const orderedVisible = orderedKeys.length ? orderedKeys : baseColumns.map(c => c.dataIndex)
  const visibleColumns = orderedVisible
    .map(k => baseColumns.find(c => c.dataIndex === k))
    .filter(Boolean)
    .filter((c: any) => visibleCols[(c as any).dataIndex])
    .concat([actionColumn])

  const columnChooser = (
    <div style={{ padding: 12 }}>
      {columnsMeta.map(c => (
        <div key={c.name} style={{ marginBottom: 6 }}>
          <Checkbox
            checked={!!visibleCols[c.name]}
            onChange={(e) => {
              const next = { ...visibleCols, [c.name]: e.target.checked }
              setVisibleCols(next)
              const visKey = `campanhas.columns.visible.${(user as any)?.usuario || 'default'}`
              localStorage.setItem(visKey, JSON.stringify(next))
            }}
          >{c.name.toUpperCase()}</Checkbox>
        </div>
      ))}
    </div>
  )

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Space>
          <Dropdown placement="bottomRight" trigger={["click"]} menu={{ items: [] }} popupRender={() => columnChooser}>
            <Button shape="circle" icon={<IconColumns />} style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} title="VISUALIZAÇÃO DE COLUNAS" />
          </Dropdown>
          <Button shape="circle" icon={<IconAdd />} style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} onClick={() => { setEditing(null); setModalOpen(true) }} title="NOVA CAMPANHA" />
        </Space>
      </div>
      <style>{`
        .campanhas-table .ant-table-thead > tr > th{ background:#FFD700; color:#000; font-family: 'Arimo', Arial, sans-serif; }
        .campanhas-table .ant-table-thead > tr > th .ant-table-column-title{ display:flex; justify-content:center; align-items:center; text-align:center; }
        .campanhas-table .ant-table-tbody > tr > td{ font-family: 'Roboto Condensed', Arial, sans-serif; padding:2px 6px; line-height:0.95; height:22px; }
      `}</style>
      <Table
        loading={loading}
        dataSource={data}
        columns={visibleColumns as any}
        rowKey="id"
        bordered
        size="small"
        className="ant-table-striped campanhas-table"
      />
      <CampanhasModal
        open={modalOpen}
        initial={editing || undefined}
        onCancel={() => setModalOpen(false)}
        onSaved={async () => { setModalOpen(false); await load() }}
      />
    </motion.div>
  )
}
