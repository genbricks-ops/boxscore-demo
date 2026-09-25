import { useState } from 'react'
import { Box, Typography, Chip } from '@mui/material'
import { motion } from 'framer-motion'

interface SectionData {
  id: string
  name: string
  capacity: number
  sold: number
  sellThrough: number
  path: string
}

const SECTIONS: SectionData[] = [
  { id: 'fc', name: 'Field Club', capacity: 2800, sold: 2660, sellThrough: 0.95, path: 'M 200 280 L 280 280 L 300 320 L 180 320 Z' },
  { id: 'cl1', name: 'Club Level 1B', capacity: 3200, sold: 2720, sellThrough: 0.85, path: 'M 140 240 L 200 240 L 200 280 L 140 270 Z' },
  { id: 'cl3', name: 'Club Level 3B', capacity: 3200, sold: 2880, sellThrough: 0.90, path: 'M 280 240 L 340 240 L 340 270 L 280 280 Z' },
  { id: 'vl1', name: 'View Level LF', capacity: 4500, sold: 3150, sellThrough: 0.70, path: 'M 90 180 L 140 180 L 140 240 L 90 220 Z' },
  { id: 'vl2', name: 'View Level RF', capacity: 4500, sold: 3375, sellThrough: 0.75, path: 'M 340 180 L 390 180 L 390 220 L 340 240 Z' },
  { id: 'bl', name: 'Bleachers', capacity: 5600, sold: 3360, sellThrough: 0.60, path: 'M 70 120 L 180 100 L 200 140 L 90 160 Z' },
  { id: 'ar', name: 'Arcade', capacity: 3000, sold: 2400, sellThrough: 0.80, path: 'M 300 100 L 410 120 L 390 160 L 280 140 Z' },
  { id: 'ub', name: 'Upper Box', capacity: 6000, sold: 3600, sellThrough: 0.60, path: 'M 60 90 L 130 70 L 160 100 L 70 120 Z' },
  { id: 'ur', name: 'Upper Reserved', capacity: 5500, sold: 2750, sellThrough: 0.50, path: 'M 350 70 L 420 90 L 410 120 L 320 100 Z' },
]

function sectionColor(sellThrough: number): string {
  if (sellThrough >= 0.9) return 'rgba(244,67,54,0.7)'
  if (sellThrough >= 0.75) return 'rgba(253,90,30,0.6)'
  if (sellThrough >= 0.5) return 'rgba(255,152,0,0.5)'
  return 'rgba(76,175,80,0.5)'
}

export default function SeatMap() {
  const [selected, setSelected] = useState<SectionData | null>(null)

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Oracle Park Seat Map</Typography>
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 300px' }}>
          <svg viewBox="40 50 400 300" style={{ width: '100%', maxWidth: 500, height: 'auto' }}>
            <rect x="180" y="310" width="120" height="30" rx="4" fill="rgba(76,175,80,0.3)" stroke="rgba(76,175,80,0.5)" strokeWidth="1" />
            <text x="240" y="330" textAnchor="middle" fill="#4CAF50" fontSize="10" fontWeight="600">FIELD</text>
            {SECTIONS.map((sec) => (
              <motion.path
                key={sec.id}
                d={sec.path}
                fill={sectionColor(sec.sellThrough)}
                stroke={selected?.id === sec.id ? '#FD5A1E' : 'rgba(255,255,255,0.2)'}
                strokeWidth={selected?.id === sec.id ? 2 : 1}
                style={{ cursor: 'pointer' }}
                whileHover={{ scale: 1.03, originX: '50%', originY: '50%' }}
                onClick={() => setSelected(sec)}
              />
            ))}
            {SECTIONS.map((sec) => {
              const match = sec.path.match(/M\s+([\d.]+)\s+([\d.]+)/)
              if (!match) return null
              const coords = sec.path.split(/[MLQCZ\s]+/).filter(Boolean).map(Number)
              const xs = coords.filter((_, i) => i % 2 === 0)
              const ys = coords.filter((_, i) => i % 2 === 1)
              const cx = xs.reduce((a, b) => a + b, 0) / xs.length
              const cy = ys.reduce((a, b) => a + b, 0) / ys.length
              return <text key={`lbl-${sec.id}`} x={cx} y={cy} textAnchor="middle" fill="white" fontSize="8" fontWeight="500">{Math.round(sec.sellThrough * 100)}%</text>
            })}
          </svg>
          <Box sx={{ display: 'flex', gap: 2, mt: 1, justifyContent: 'center' }}>
            <Chip label="Available" size="small" sx={{ bgcolor: 'rgba(76,175,80,0.3)' }} />
            <Chip label="Selling" size="small" sx={{ bgcolor: 'rgba(255,152,0,0.3)' }} />
            <Chip label="Near Sold Out" size="small" sx={{ bgcolor: 'rgba(244,67,54,0.3)' }} />
          </Box>
        </Box>
        {selected && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} style={{ flex: '0 0 220px' }}>
            <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid rgba(239,209,159,0.1)' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>{selected.name}</Typography>
              <Typography variant="body2" sx={{ mb: 0.5 }}>Capacity: {selected.capacity.toLocaleString()}</Typography>
              <Typography variant="body2" sx={{ mb: 0.5 }}>Sold: {selected.sold.toLocaleString()}</Typography>
              <Typography variant="body2" sx={{ mb: 0.5 }}>Available: {(selected.capacity - selected.sold).toLocaleString()}</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600, color: selected.sellThrough > 0.8 ? 'error.main' : 'success.main' }}>
                Sell-Through: {Math.round(selected.sellThrough * 100)}%
              </Typography>
            </Box>
          </motion.div>
        )}
      </Box>
    </Box>
  )
}
