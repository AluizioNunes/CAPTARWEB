import { motion } from 'framer-motion'
import { Card } from 'antd'

export default function AlmoxRelatorios() {
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card title="Relatórios">
        Em breve: relatórios de estoque, movimentações e fornecedores
      </Card>
    </motion.div>
  )
}

