import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Table, Button, Space, Dropdown, Checkbox, App } from 'antd'
import { useAuthStore } from '../store/authStore'
import { useApi } from '../context/ApiContext'
import MetaModal from '../components/MetaModal'

export default function Metas() {
  const api = useApi()
  const { user } = useAuthStore()
  const { message } = App.useApp()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [columnsMeta, setColumnsMeta] = useState<{ name: string; type: string; nullable: boolean; maxLength?: number }[]>([])
  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({})
  const [orderedKeys, setOrderedKeys] = useState<string[]>([])

  const IconColumns = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 4h6v16H3V4zm12 0h6v16h-6V4z" fill="currentColor"/></svg>
  )
  const IconAdd = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
  )

  const load = async () => {
    try {
      setLoading(true)
      const res = await api.listMetas()
      const rows = res.rows || []
      let candidates: any[] = []
      let elections: any[] = []
      try { const cs = await api.listCandidatos(); candidates = cs.rows || [] } catch {}
      try { const es = await api.listEleicoes(); elections = es.rows || [] } catch {}
      const cmap = new Map<number, string>()
      for (const c of candidates) {
        const id = Number(c.IdCandidato ?? c.idCandidato ?? c.Id ?? c.ID)
        const nm = String(c.Nome ?? c.nome ?? '')
        if (!isNaN(id)) cmap.set(id, nm)
      }
      const emap = new Map<number, string>()
      for (const e of elections) {
        const id = Number(e.IdEleicao ?? e.idEleicao ?? e.Id ?? e.ID)
        const nm = String(e.Nome ?? e.nome ?? '')
        if (!isNaN(id)) emap.set(id, nm)
      }
      const withNames = rows.map((r: any) => {
        const cid = Number(r.IdCandidato ?? r.idCandidato)
        const eid = Number(r.IdEleicao ?? r.idEleicao)
        const candidato = cmap.get(cid) || (r.CandidatoNome ?? '')
        const eleicao = emap.get(eid) || (r.EleicaoNome ?? '')
        const votos = Number(r.VotosAtual ?? r.votosAtual ?? 0)
        const meta = Number(r.MetaVotos ?? 0)
        const prog = meta > 0 ? Math.min(100, Math.round((votos / meta) * 100)) : 0
        return { ...r, Candidato: candidato, Eleicao: eleicao, ProgressoVotos: prog }
      })
      setData(withNames)
      const defaultOrder = ['IdMeta','Candidato','Numero','Partido','Cargo','Eleicao','DataInicio','DataFim','MetaVotos','ProgressoVotos','MetaDisparos','MetaAprovacao','MetaRejeicao','TenantLayer']
      const inferType = (k: string) => {
        const sample = withNames.find(r => r[k] !== undefined && r[k] !== null)
        const v = sample ? sample[k] : ''
        const t = typeof v
        if (t === 'number') return 'int'
        if (t === 'boolean') return 'bool'
        if (String(k).toLowerCase().includes('data')) return 'timestamp'
        return 'text'
      }
      const allKeys = Array.from(new Set(withNames.flatMap(r => Object.keys(r))))
      const byName: Record<string, { name: string; type: string; nullable: boolean }> = {}
      for (const n of allKeys) byName[n] = { name: n, type: inferType(n), nullable: true }
      const ordered = defaultOrder.filter(n => byName[n]).map(n => byName[n])
      const rest = allKeys.filter(n => !defaultOrder.includes(n)).map(n => byName[n])
      setColumnsMeta([...ordered, ...rest])
      const visDefault: Record<string, boolean> = {}
      for (const n of defaultOrder) if (byName[n]) visDefault[n] = true
      for (const c of rest) visDefault[c.name] = false
      const visKey = `metas.columns.visible.${(user as any)?.usuario || 'default'}`
      const savedVis = localStorage.getItem(visKey)
      setVisibleCols(savedVis ? JSON.parse(savedVis) : visDefault)
      const orderKey = `metas.columns.order.${(user as any)?.usuario || 'default'}`
      const savedOrder = localStorage.getItem(orderKey)
      setOrderedKeys(savedOrder ? JSON.parse(savedOrder) : defaultOrder.filter(n => byName[n]))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar metas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const baseColumns = columnsMeta.map(col => {
    const dataIndex = col.name
    const uniqueValues = Array.from(new Set((data || []).map(r => r[dataIndex]).filter(v => v !== undefined && v !== null)))
    const filters = uniqueValues.slice(0, 20).map(v => ({ text: Array.isArray(v) ? String(v.join(', ')).toUpperCase() : String(v).toUpperCase(), value: Array.isArray(v) ? String(v.join(', ')).toUpperCase() : String(v).toUpperCase() }))
    const type = (col.type || '').toLowerCase()
    const sorter = (a: any, b: any) => {
      const av = a[dataIndex]
      const bv = b[dataIndex]
      if (av === undefined || av === null) return -1
      if (bv === undefined || bv === null) return 1
      if (Array.isArray(av) || Array.isArray(bv)) {
        const sa = Array.isArray(av) ? av.join(', ') : String(av)
        const sb = Array.isArray(bv) ? bv.join(', ') : String(bv)
        return sa.toUpperCase().localeCompare(sb.toUpperCase())
      }
      if (type.includes('int') || type.includes('numeric')) return Number(av) - Number(bv)
      if (type.includes('date') || type.includes('timestamp')) return new Date(av).getTime() - new Date(bv).getTime()
      return String(av).toUpperCase().localeCompare(String(bv).toUpperCase())
    }
    const titleMap: Record<string, string> = {
      IdMeta: 'ID', Candidato: 'CANDIDATO', Numero: 'NÚMERO', Partido: 'PARTIDO', Cargo: 'CARGO', Eleicao: 'ELEIÇÃO', DataInicio: 'DATA INÍCIO', DataFim: 'DATA FIM', MetaVotos: 'META VOTOS', ProgressoVotos: 'PROGRESSO (%)', MetaDisparos: 'DISPAROS', MetaAprovacao: 'APROVAÇÃO', MetaRejeicao: 'REJEIÇÃO', TenantLayer: 'TENANT LAYER'
    }
    const centerCols = new Set(['IdMeta','Numero','MetaVotos','ProgressoVotos','MetaDisparos','MetaAprovacao','MetaRejeicao','DataInicio','DataFim','TenantLayer'])
    const colObj: any = {
      title: titleMap[dataIndex] || dataIndex.toUpperCase(),
      dataIndex,
      align: centerCols.has(dataIndex) ? 'center' : 'left',
      filters,
      onFilter: (value: any, record: any) => String(record[dataIndex]).toUpperCase() === String(value).toUpperCase(),
      sorter,
      sortDirections: ['ascend', 'descend'] as any,
      render: (v: any) => {
        if (typeof v === 'boolean') return v ? 'SIM' : 'NÃO'
        if (v === null || v === undefined) return ''
        if (Array.isArray(v)) return v.map(x => String(x).toUpperCase()).join(' | ')
        if (type.includes('date') || type.includes('timestamp')) {
          const d = new Date(v)
          if (!isNaN(d.getTime())) return d.toLocaleString('pt-BR', { hour12: false })
        }
        if (dataIndex === 'ProgressoVotos') return `${Number(v || 0)}%`
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
            const orderKey = `metas.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      })
    }
    if (dataIndex === 'IdMeta') colObj.defaultSortOrder = 'ascend'
    return colObj
  })

  const actionColumn: any = {
    title: 'AÇÕES',
    dataIndex: '__actions__',
    render: (_: any, record: any) => (
      <Space>
        <Button type="text" title="EDITAR" onClick={() => { setEditing(record); setModalOpen(true) }}>EDITAR</Button>
        <Button type="text" danger title="DELETAR" onClick={async () => {
          try {
            if (!record.IdMeta) { message.info('REGISTRO SEM ID'); return }
            await api.deleteMeta(record.IdMeta)
            message.success('META DELETADA')
            await load()
          } catch (e: any) {
            message.error(e?.response?.data?.detail || 'ERRO AO DELETAR META')
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
              const visKey = `metas.columns.visible.${(user as any)?.usuario || 'default'}`
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
          <Button shape="circle" icon={<IconAdd />} style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} onClick={() => { setEditing(null); setModalOpen(true) }} title="NOVA META" />
        </Space>
      </div>
      <style>{`
        .metas-table .ant-table-thead > tr > th{ background:#FFD700; color:#000; font-family: 'Arimo', Arial, sans-serif; }
        .metas-table .ant-table-thead > tr > th .ant-table-column-title{ display:flex; justify-content:center; align-items:center; text-align:center; }
        .metas-table .ant-table-tbody > tr > td{ font-family: 'Roboto Condensed', Arial, sans-serif; padding:2px 6px; line-height:0.95; height:22px; }
      `}</style>
      <Table
        loading={loading}
        dataSource={data}
        columns={visibleColumns as any}
        rowKey={(r, idx) => String((r as any).IdMeta ?? (r as any).id ?? idx)}
        bordered
        size="small"
        className="ant-table-striped metas-table"
        scroll={{ y: 520 }}
        locale={{ emptyText: 'Nenhuma meta cadastrada' }}
      />
      <MetaModal
        open={modalOpen}
        initial={editing || undefined}
        onCancel={() => setModalOpen(false)}
        onSaved={async () => { setModalOpen(false); await load() }}
      />
    </motion.div>
  )
}
