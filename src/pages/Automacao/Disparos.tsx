import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Button, Space, Tag, Table } from 'antd'
import { ThunderboltOutlined, SendOutlined, ReloadOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'


export default function Disparos() {
  const [loading, setLoading] = useState(false)
  const [dados, setDados] = useState<any[]>([])
  const columns = [
    { title: 'ID', dataIndex: 'id', align: 'center', sorter: (a: any, b: any) => Number(a.id) - Number(b.id) },
    { title: 'CANAL', dataIndex: 'canal', align: 'center', render: (v: any) => String(v || '').toUpperCase() },
    { title: 'DESTINO', dataIndex: 'destino', align: 'left' },
    { title: 'STATUS', dataIndex: 'status', align: 'center', render: (v: any) => <Tag color={String(v).toUpperCase()==='PENDENTE'?'orange':String(v).toUpperCase()==='ENVIADO'?'green':'default'}>{String(v || '').toUpperCase()}</Tag> },
    { title: 'DATA', dataIndex: 'datahora', align: 'center', render: (v: any) => v ? new Date(v).toLocaleString('pt-BR', { hour12: false }) : '—', sorter: (a: any, b: any) => new Date(a.datahora || 0).getTime() - new Date(b.datahora || 0).getTime() },
  ]
  const load = async () => {
    try {
      setLoading(true)
      setDados([])
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Row gutter={[16,16]}>
        <Col span={24}>
          <Card>
            <Space style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
              <Space>
                <ThunderboltOutlined />
                <Typography.Title level={4} style={{ margin: 0 }}>AUTOMAÇÃO • DISPAROS</Typography.Title>
              </Space>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={load}>Atualizar</Button>
                <Button type="primary" icon={<SendOutlined />}>Novo Disparo</Button>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col span={24}>
          <Card>
            <Table rowKey={(r) => r.id || JSON.stringify(r)} loading={loading} dataSource={dados} columns={columns as any} size="small" bordered />
          </Card>
        </Col>
      </Row>
    </motion.div>
  )
}
