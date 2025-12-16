import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Button, Space, Table } from 'antd'
import { ThunderboltOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'

export default function Campanha() {
  const [loading, setLoading] = useState(false)
  const [dados, setDados] = useState<any[]>([])

  const columns = [
    { title: 'ID', dataIndex: 'id', align: 'center', width: 80 },
    { title: 'NOME DA CAMPANHA', dataIndex: 'nome', align: 'left' },
    { title: 'STATUS', dataIndex: 'status', align: 'center', width: 120 },
    { title: 'DATA CRIAÇÃO', dataIndex: 'created_at', align: 'center', width: 180 },
  ]

  const load = async () => {
    try {
      setLoading(true)
      // TODO: Implementar chamada de API
      setDados([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Space style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
              <Space>
                <ThunderboltOutlined />
                <Typography.Title level={4} style={{ margin: 0 }}>AUTOMAÇÃO • CAMPANHA</Typography.Title>
              </Space>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={load}>Atualizar</Button>
                <Button type="primary" icon={<PlusOutlined />}>Nova Campanha</Button>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col span={24}>
          <Card>
            <Table 
              rowKey="id" 
              loading={loading} 
              dataSource={dados} 
              columns={columns as any} 
              size="small" 
              bordered 
              locale={{ emptyText: 'Nenhuma campanha encontrada' }}
            />
          </Card>
        </Col>
      </Row>
    </motion.div>
  )
}
