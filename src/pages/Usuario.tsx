import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Table, Button, Space, message, Dropdown, Checkbox, Tag } from 'antd'
import { useAuthStore } from '../store/authStore'
import { useApi } from '../context/ApiContext'
import UsuariosModal from '../components/UsuariosModal'

export default function Usuario() {
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
  const IconUserAdd = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
      <path d="M4 20c0-3.866 3.582-7 8-7s8 3.134 8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <path d="M18 6h3M19.5 4.5v3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )

  const load = async () => {
    try {
      setLoading(true)
      const schema = await api.getUsuariosSchema()
      const defaultOrder = [
        'IdUsuario',
        'Nome',
        'CPF',
        'Usuario',
        'Funcao',
        'Perfil',
        'Email',
        'DataCadastro',
        'Cadastrante',
        'TenantLayer',
        'Ativo',
      ]
      const byName: Record<string, { name: string; type: string; nullable: boolean }> = {}
      for (const c of schema.columns || []) byName[c.name] = c
      const ordered = defaultOrder.filter(n => byName[n]).map(n => byName[n])
      const rest = (schema.columns || []).filter(c => !defaultOrder.includes(c.name))
      setColumnsMeta([...ordered, ...rest])
      const res = await api.listUsuarios()
      let rows = res.rows || []
      try {
        const perfis = await api.listPerfil()
        const pRows: any[] = perfis.rows || []
        const idKey = (r: any) => r.IdPerfil ?? r.id ?? r.Id ?? r.ID
        const labelKey = (r: any) => r.Perfil ?? r.perfil
        const pmap = new Map<number, string>()
        for (const r of pRows) {
          const id = idKey(r)
          const label = labelKey(r)
          if (id !== undefined && label !== undefined) pmap.set(Number(id), String(label))
        }
        const funcoes = await api.listFuncoes()
        const fRows: any[] = funcoes.rows || []
        const fmap = new Map<number, string>()
        for (const fr of fRows) {
          const fid = fr.IdFuncao ?? fr.id ?? fr.Id ?? fr.ID
          const flabel = fr.Funcao ?? fr.Descricao
          if (fid !== undefined && flabel !== undefined) fmap.set(Number(fid), String(flabel))
        }
        rows = rows.map((r: any) => {
          const pid = r.IdPerfil ?? r.idPerfil ?? r.id_perfil
          const plabel = pid !== undefined ? pmap.get(Number(pid)) : (r.Perfil ?? r.perfil)
          const fid = r.IdFuncao ?? r.idFuncao ?? r.id_funcao
          let flabel = fid !== undefined ? fmap.get(Number(fid)) : undefined
          if (!flabel) {
            const fval = r.Funcao
            const fnum = Number(fval)
            const isNum = !isNaN(fnum) && String(fnum) === String(fval)
            flabel = isNum ? fmap.get(fnum) : fval
          }
          return { ...r, Perfil: plabel ?? r.Perfil, Funcao: flabel ?? r.Funcao }
        })
      } catch {}
      setData(rows)
      const visDefault: Record<string, boolean> = {}
      for (const n of defaultOrder) if (byName[n]) visDefault[n] = true
      for (const c of rest) visDefault[c.name] = false
      if (byName['IdPerfil']) visDefault['IdPerfil'] = false
      const visKey = `usuarios.columns.visible.${(user as any)?.usuario || 'default'}`
      const savedVis = localStorage.getItem(visKey)
      setVisibleCols(savedVis ? JSON.parse(savedVis) : visDefault)
      const orderKey = `usuarios.columns.order.${(user as any)?.usuario || 'default'}`
      const savedOrder = localStorage.getItem(orderKey)
      setOrderedKeys(savedOrder ? JSON.parse(savedOrder) : defaultOrder.filter(n => byName[n]))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao carregar usuários')
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
      IdUsuario: 'ID',
      Nome: 'NOME',
      CPF: 'CPF',
      Usuario: 'USUÁRIO',
      Funcao: 'FUNÇÃO',
      Perfil: 'PERFIL',
      Email: 'EMAIL',
      DataCadastro: 'DATA E HORA DE CADASTRO',
      Cadastrante: 'CADASTRANTE',
      TenantLayer: 'TENANT LAYER',
      Ativo: 'ATIVO',
    }
    const centerCols = new Set(['IdUsuario','Ativo','CPF','Funcao','Perfil','DataCadastro','TenantLayer','DataUpdate','UltimoAcesso','TokenExpiracao'])
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
        const timeOnlyCols = new Set(['DataUpdate','UltimoAcesso','TokenExpiracao'])
        if (type.includes('date') || type.includes('timestamp')) {
          const d = new Date(v)
          if (!isNaN(d.getTime())) {
            if (dataIndex === 'DataCadastro') {
              return d.toLocaleString('pt-BR', { hour12: false })
            }
            if (timeOnlyCols.has(dataIndex)) {
              return d.toLocaleTimeString('pt-BR', { hour12: false })
            }
          }
        }
        if (dataIndex === 'Ativo') {
          const yes = String(v).toLowerCase() === 'true' || v === 1 || String(v).toUpperCase() === 'SIM'
          return <Tag color={yes ? 'green' : 'red'}>{yes ? 'SIM' : 'NÃO'}</Tag>
        }
        if (dataIndex === 'Email') {
          return String(v).toLowerCase()
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
            const orderKey = `usuarios.columns.order.${(user as any)?.usuario || 'default'}`
            localStorage.setItem(orderKey, JSON.stringify(next))
            return next
          })
        }
      })
    }
    if (dataIndex === 'IdUsuario') colObj.defaultSortOrder = 'ascend'
    return colObj
  })

  const actionColumn: any = {
    title: 'AÇÕES',
    dataIndex: '__actions__',
    render: (_: any, record: any) => (
      <Space>
        <Button type="text" icon={<IconEdit />} title="EDITAR" onClick={() => { setEditing(record); setModalOpen(true) }} />
        <Button type="text" danger icon={<IconDelete />} title="DELETAR" onClick={async () => {
          try {
            if (!record.IdUsuario) { message.info('REGISTRO SEM ID'); return }
            await api.deleteUsuario(record.IdUsuario)
            message.success('USUÁRIO DELETADO')
            await load()
          } catch (e: any) {
            message.error(e?.response?.data?.detail || 'ERRO AO DELETAR USUÁRIO')
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
              const visKey = `usuarios.columns.visible.${(user as any)?.usuario || 'default'}`
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
          <Button shape="circle" icon={<IconUserAdd />} style={{ background: '#FFD700', borderColor: '#FFD700', color: '#000' }} onClick={() => { setEditing(null); setModalOpen(true) }} title="NOVO USUÁRIO" />
        </Space>
      </div>
      <style>{`
        .usuarios-table .ant-table-thead > tr > th{ background:#FFD700; color:#000; font-family: 'Arimo', Arial, sans-serif; }
        .usuarios-table .ant-table-thead > tr > th .ant-table-column-title{ display:flex; justify-content:center; align-items:center; text-align:center; }
        .usuarios-table .ant-table-tbody > tr > td{ font-family: 'Roboto Condensed', Arial, sans-serif; padding:2px 6px; line-height:0.95; height:22px; }
      `}</style>
      <Table
        loading={loading}
        dataSource={data}
        columns={visibleColumns as any}
        rowKey={(r) => r.IdUsuario ?? r.id ?? r.ID ?? r.id_usuario ?? JSON.stringify(r)}
        bordered
        size="small"
        className="ant-table-striped usuarios-table"
      />
      <UsuariosModal
        open={modalOpen}
        initial={editing || undefined}
        onCancel={() => setModalOpen(false)}
        onSaved={async () => { setModalOpen(false); await load() }}
      />
    </motion.div>
  )
}
