import { Modal, Form, Input, InputNumber, Select, DatePicker, Button, Space, Upload, App } from 'antd'
import { useState } from 'react'
import { useEffect } from 'react'
import { useApi } from '../context/ApiContext'
import { UploadOutlined } from '@ant-design/icons'

interface Props {
  open: boolean
  initial?: any
  onCancel: () => void
  onSaved: () => void
}

export default function MetaModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const api = useApi()
  const { message } = App.useApp()
  const [candidatos, setCandidatos] = useState<any[]>([] as any)
  const [eleicoes, setEleicoes] = useState<any[]>([] as any)
  useEffect(() => {
    if (initial) form.setFieldsValue(initial)
    else form.resetFields()
  }, [initial, open])
  useEffect(() => {
    ;(async () => {
      try { const cs = await api.listCandidatos(); setCandidatos(cs.rows || []) } catch {}
      try { const es = await api.listEleicoes(); setEleicoes(es.rows || []) } catch {}
    })()
  }, [open])

  const onOk = async () => {
    try {
      const values = await form.validateFields()
      const di = values.DataInicio
      const df = values.DataFim
      if (di && df && di.isAfter(df)) {
        message.error('Data Início deve ser menor ou igual à Data Fim')
        return
      }
      const payload = {
        IdCandidato: values.IdCandidato,
        Numero: values.Numero,
        Partido: values.Partido,
        Cargo: values.Cargo,
        IdEleicao: values.IdEleicao,
        DataInicio: values.DataInicio?.format('YYYY-MM-DD HH:mm:ss'),
        DataFim: values.DataFim?.format('YYYY-MM-DD HH:mm:ss'),
        MetaVotos: values.MetaVotos,
        MetaDisparos: values.MetaDisparos,
        MetaAprovacao: values.MetaAprovacao,
        MetaRejeicao: values.MetaRejeicao,
        Ativo: true
      }
      if (initial && initial.IdMeta) await api.updateMeta(Number(initial.IdMeta), payload)
      else await api.createMeta(payload)
      message.success('Meta salva')
      onSaved()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Erro ao salvar meta')
    }
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
    return false
  }

  return (
    <Modal title={initial ? 'Editar Meta' : 'Nova Meta'} open={open} onCancel={onCancel} onOk={onOk} okText="Salvar">
      <Form layout="vertical" form={form}>
        <Space style={{ marginBottom: 8 }}>
          <Button onClick={() => form.resetFields()}>Limpar</Button>
        </Space>
        <Form.Item name="IdCandidato" label="Candidato" rules={[{ required: true }]}>
          <Select placeholder="Selecione" options={(candidatos || []).map((c: any) => ({ label: String(c.Nome || c.nome), value: Number(c.IdCandidato || c.idCandidato), extra: c }))} onChange={(val, opt: any) => {
            const extra = (opt as any)?.extra || {}
            form.setFieldsValue({ Numero: extra.Numero || extra.numero || undefined, Partido: extra.Partido || extra.partido || undefined, Cargo: extra.Cargo || extra.cargo || undefined })
          }} />
        </Form.Item>
        <Form.Item name="IdEleicao" label="Eleição" rules={[{ required: true }]}>
          <Select placeholder="Selecione" options={(eleicoes || []).map((e: any) => ({ label: String(e.Nome || e.nome), value: Number(e.IdEleicao || e.idEleicao) }))} />
        </Form.Item>
        <Form.Item name="Numero" label="Número">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
        <Form.Item name="Partido" label="Partido">
          <Input />
        </Form.Item>
        <Form.Item name="Cargo" label="Cargo">
          <Input />
        </Form.Item>
        <Form.Item name="DataInicio" label="Data Início">
          <DatePicker showTime style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="DataFim" label="Data Fim" rules={[{ validator: (_, v) => {
          const di = form.getFieldValue('DataInicio')
          if (di && v && di.isAfter(v)) return Promise.reject(new Error('Data Início deve ser menor ou igual à Data Fim'))
          return Promise.resolve()
        } }]}>
          <DatePicker showTime style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="MetaVotos" label="Meta Votos">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
        <Form.Item name="MetaDisparos" label="Disparos">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
        <Form.Item name="MetaAprovacao" label="Aprovação">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
        <Form.Item name="MetaRejeicao" label="Rejeição">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
        <Form.Item label="Imagem (opcional)">
          <Upload beforeUpload={beforeUpload} maxCount={1} accept="image/*">
            <Button icon={<UploadOutlined />}>Selecionar imagem</Button>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  )
}
