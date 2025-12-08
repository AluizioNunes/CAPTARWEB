import { motion } from 'framer-motion'
import { Table, Card } from 'antd'

export default function AlmoxPedidos() {
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card title="Pedidos">
        <Table bordered size="small" dataSource={[]} columns={[{ title: 'NÚMERO', dataIndex: 'numero' }, { title: 'STATUS', dataIndex: 'status' }]} />
      </Card>
    </motion.div>
  )
}

