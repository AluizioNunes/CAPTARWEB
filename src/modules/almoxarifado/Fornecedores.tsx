import { motion } from 'framer-motion'
import { Table, Card } from 'antd'

export default function AlmoxFornecedores() {
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card title="Fornecedores">
        <Table bordered size="small" dataSource={[]} columns={[{ title: 'NOME', dataIndex: 'nome' }, { title: 'CONTATO', dataIndex: 'contato' }]} />
      </Card>
    </motion.div>
  )
}

