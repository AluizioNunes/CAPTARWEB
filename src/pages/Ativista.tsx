import { motion } from 'framer-motion'

export default function Ativista() {
  return (
    <motion.div className="page-container" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      
      <p>Página de gerenciamento de ativistas</p>
    </motion.div>
  )
}
