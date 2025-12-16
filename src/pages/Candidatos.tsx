import { useEffect, useState } from 'react'
import { Card, Space, Button, Table, Modal, Form, Input, Upload, Image, App } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useApi } from '../context/ApiContext'

export default function Candidatos() {
  const api = useApi()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const [foto, setFoto] = useState<string>('')

  const load = async () => {
    try {
      setLoading(true)
      const res = await api.listCandidatos()
      setRows(res.rows || [])
    } catch {
      message.error('Erro ao carregar candidatos')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  const colsDef = [
    { title: 'Id', dataIndex: 'IdCandidato', key: 'IdCandidato', width: 80 },
    { title: 'Nome', dataIndex: 'Nome', key: 'Nome' },
    { title: 'Numero', dataIndex: 'Numero', key: 'Numero', width: 120 },
    { title: 'Partido', dataIndex: 'Partido', key: 'Partido', width: 160 },
    { title: 'Cargo', dataIndex: 'Cargo', key: 'Cargo', width: 160 },
    { title: 'Foto', dataIndex: 'Foto', key: 'Foto', render: (v: any) => v ? <Image src={v} width={48} fallback="" /> : <span style={{ color: '#999' }}>Sem foto</span>, width: 120 },
  ]
  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values, Foto: foto }
      const r = await api.createCandidato(payload)
      if (r && r.id) {
        message.success('Candidato criado')
        setOpen(false)
        form.resetFields()
        setFoto('')
        load()
      }
    } catch {}
  }
  const beforeUpload = async (file: File) => {
    if (!String(file.type || '').startsWith('image/')) {
      message.error('Apenas imagens são permitidas')
      return Upload.LIST_IGNORE as any
    }
    if (file.size > 2 * 1024 * 1024) {
      message.error('Imagem acima de 2MB')
      return Upload.LIST_IGNORE as any
    }
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = String(reader.result || '')
      setFoto(base64)
    }
    reader.readAsDataURL(file)
    return false
  }
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>CANDIDATOS</h3>
        <Space>
          <Button type="primary" onClick={() => setOpen(true)}>NOVO CANDIDATO</Button>
        </Space>
      </div>
      <Card>
        <Table
          loading={loading}
          dataSource={rows}
          columns={colsDef as any}
          rowKey={r => r.IdCandidato ?? JSON.stringify(r)}
          pagination={{ pageSize: 10 }}
          scroll={{ y: 480 }}
          locale={{ emptyText: 'Nenhum candidato' }}
        />
      </Card>
      <Modal title="Novo Candidato" open={open} onCancel={() => setOpen(false)} onOk={handleOk} okText="Salvar">
        <Form layout="vertical" form={form}>
          <Form.Item name="Nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="Numero" label="Número">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="Partido" label="Partido">
            <Input />
          </Form.Item>
          <Form.Item name="Cargo" label="Cargo">
            <Input />
          </Form.Item>
          <Form.Item label="Foto">
            <Upload beforeUpload={beforeUpload} maxCount={1} accept="image/*">
              <Button icon={<UploadOutlined />}>Selecionar imagem</Button>
            </Upload>
            {foto && <div style={{ marginTop: 8 }}><Image src={foto} width={96} /></div>}
          </Form.Item>
        </Form>
      </Modal>
    </motion.div>
  )
}
