import { Box, Typography, Card, CardContent } from '@mui/material'
import { motion } from 'framer-motion'
import { ReactNode } from 'react'

interface KPICardProps {
  icon: ReactNode
  title: string
  value: string
  change: number
  sparkline?: number[]
  delay?: number
}

export default function KPICard({ icon, title, value, change, sparkline, delay = 0 }: KPICardProps) {
  const positive = change >= 0
  const spark = sparkline || []
  const max = Math.max(...spark, 1)
  const min = Math.min(...spark, 0)
  const range = max - min || 1

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ scale: 1.02 }}
    >
      <Card sx={{
        background: 'linear-gradient(135deg, rgba(22,33,62,0.9) 0%, rgba(13,17,23,0.95) 100%)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(239,209,159,0.1)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, color: 'text.secondary' }}>
                {icon}
                <Typography variant="body2" sx={{ fontWeight: 500, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.08em' }}>
                  {title}
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>{value}</Typography>
              <Typography variant="body2" sx={{ color: positive ? 'success.main' : 'error.main', fontWeight: 600, fontSize: '0.8rem' }}>
                {positive ? '+' : ''}{change}% vs last month
              </Typography>
            </Box>
            {spark.length > 1 && (
              <Box sx={{ width: 80, height: 40, display: 'flex', alignItems: 'flex-end', gap: '2px' }}>
                {spark.map((v, i) => (
                  <Box key={i} sx={{
                    flex: 1,
                    height: `${((v - min) / range) * 100}%`,
                    minHeight: 2,
                    bgcolor: positive ? 'rgba(76,175,80,0.5)' : 'rgba(244,67,54,0.5)',
                    borderRadius: '2px 2px 0 0',
                  }} />
                ))}
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  )
}
