import { motion } from 'framer-motion'
import { Table, Card } from 'antd'

export default function AlmoxEntradas() {
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card title="Entradas">
        <Table bordered size="small" dataSource={[]} columns={[{ title: 'DATA', dataIndex: 'data' }, { title: 'ITEM', dataIndex: 'item' }, { title: 'QTD', dataIndex: 'qtd' }]} />
      </Card>
    </motion.div>
  )
}

