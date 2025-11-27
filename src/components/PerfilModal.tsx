import { Modal, Form, Input, Checkbox, Button, Space, message, InputNumber, DatePicker } from 'antd'
import { useEffect, useState } from 'react'
import { useApi } from '../context/ApiContext'

interface Props {
  open: boolean
  initial?: any
  onCancel: () => void
  onSaved: () => void
}

export default function PerfilModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const [schema, setSchema] = useState<{ name: string; type: string; nullable: boolean }[]>([])
  const api = useApi()

  useEffect(() => {
    const loadSchema = async () => {
      try {
        const s = await api.getPerfilSchema()
        setSchema(s.columns || [])
      } catch {}
    }
    if (open) {
      loadSchema()
      if (initial) form.setFieldsValue(initial)
      else form.resetFields()
    }
  }, [open, initial])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if (initial?.IdPerfil) {
        await api.updatePerfil(initial.IdPerfil, values)
        message.success('Perfil atualizado')
      } else {
        await api.createPerfil(values)
        message.success('Perfil criado')
      }
      onSaved()
    } catch {}
  }

  const renderField = (col: { name: string; type: string; nullable: boolean }) => {
    if (col.name === 'IdPerfil') return null
    const required = !col.nullable
    const type = col.type.toLowerCase()
    if (type.includes('boolean')) {
      return (
        <Form.Item key={col.name} name={col.name} valuePropName="checked" label={col.name}>
          <Checkbox />
        </Form.Item>
      )
    }
    if (type.includes('date')) {
      const showTime = type.includes('timestamp')
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}>
          <DatePicker style={{ width: '100%' }} showTime={showTime} />
        </Form.Item>
      )
    }
    if (type.includes('int') || type.includes('numeric')) {
      return (
        <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}>
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
      )
    }
    return (
      <Form.Item key={col.name} name={col.name} label={col.name} rules={[{ required }]}>
        <Input />
      </Form.Item>
    )
  }

  return (
    <Modal open={open} title={initial?.id ? 'Editar Perfil' : 'Novo Perfil'} onCancel={onCancel} footer={null} destroyOnHidden>
      <Form form={form} layout="vertical">
        {schema.map(renderField)}
        <Space style={{ marginTop: 16 }}>
          <Button onClick={onCancel}>Cancelar</Button>
          <Button type="primary" onClick={handleOk}>Salvar</Button>
        </Space>
      </Form>
    </Modal>
  )
}