import { Modal, Form, Input, Button, Space, message, Switch, Select } from 'antd'
import { useEffect, useState } from 'react'
import { useApi } from '../context/ApiContext'

interface Props {
  open: boolean
  initial?: { id?: number; funcao?: string; descricao?: string } | null
  onCancel: () => void
  onSaved: () => void
}

export default function FuncoesModal({ open, initial, onCancel, onSaved }: Props) {
  const [form] = Form.useForm()
  const api = useApi()
  const [perfis, setPerfis] = useState<any[]>([])

  useEffect(() => {
    if (open) {
      ;(async () => {
        try {
          const res = await api.listPerfil()
          setPerfis(res.rows || [])
        } catch {}
      })()
      if (initial) form.setFieldsValue(initial)
      else form.resetFields()
    }
  }, [open, initial])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if ((initial as any)?.IdFuncao) {
        await api.updateFuncao((initial as any).IdFuncao, values)
        message.success('Função atualizada')
      } else {
        await api.createFuncao(values)
        message.success('Função criada')
      }
      onSaved()
    } catch {}
  }

  return (
    <Modal open={open} title={(initial as any)?.IdFuncao ? 'Editar Função' : 'Nova Função'} onCancel={onCancel} footer={null} destroyOnHidden>
      <Form form={form} layout="vertical">
        <Form.Item name="Funcao" label="Funcao" rules={[{ required: true }]}> 
          <Input />
        </Form.Item>
        <Form.Item name="Perfil" label="Perfil" rules={[{ required: true }]}> 
          <Select
            placeholder="Selecione um perfil"
            showSearch
            options={(perfis || []).map((p: any) => {
              const label = p.Perfil ?? p.Nome ?? p.Descricao ?? String(p.IdPerfil ?? '')
              const value = p.Perfil ?? String(p.IdPerfil ?? '')
              return { label, value }
            })}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
          />
        </Form.Item>
        <Form.Item name="Cadastrante" label="Cadastrante"> 
          <Input />
        </Form.Item>
        <Form.Item name="Candidato" label="Candidato"> 
          <Input />
        </Form.Item>
        <Form.Item name="TenantLayer" label="TenantLayer"> 
          <Input />
        </Form.Item>
        <Form.Item name="Ativo" label="Ativo" valuePropName="checked"> 
          <Switch />
        </Form.Item>
        <Space style={{ marginTop: 16 }}>
          <Button onClick={onCancel}>Cancelar</Button>
          <Button type="primary" onClick={handleOk}>Salvar</Button>
        </Space>
      </Form>
    </Modal>
  )
}
