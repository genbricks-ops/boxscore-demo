import { Box, Typography, Tooltip as MuiTooltip } from '@mui/material'

interface HeatmapCell {
  price: number
  recommended?: number
}

interface PriceHeatmapProps {
  sections: string[]
  gameTypes: string[]
  data: HeatmapCell[][]
}

function cellColor(price: number, min: number, max: number): string {
  const ratio = (price - min) / (max - min || 1)
  if (ratio < 0.25) return 'rgba(76,175,80,0.4)'
  if (ratio < 0.5) return 'rgba(76,175,80,0.2)'
  if (ratio < 0.75) return 'rgba(253,90,30,0.25)'
  return 'rgba(244,67,54,0.35)'
}

export default function PriceHeatmap({ sections, gameTypes, data }: PriceHeatmapProps) {
  const allPrices = data.flat().map((c) => c.price)
  const min = Math.min(...allPrices)
  const max = Math.max(...allPrices)

  return (
    <Box sx={{ overflowX: 'auto' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Price Sensitivity by Section</Typography>
      <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr>
            <Box component="th" sx={{ p: 1, textAlign: 'left', color: 'text.secondary', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Section</Box>
            {gameTypes.map((gt) => (
              <Box component="th" key={gt} sx={{ p: 1, textAlign: 'center', color: 'text.secondary', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>{gt}</Box>
            ))}
          </tr>
        </thead>
        <tbody>
          {sections.map((section, si) => (
            <tr key={section}>
              <Box component="td" sx={{ p: 1, fontWeight: 500, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{section}</Box>
              {gameTypes.map((_, gi) => {
                const cell = data[si]?.[gi] || { price: 0 }
                return (
                  <MuiTooltip key={gi} title={`$${cell.price} ${cell.recommended ? `→ Rec: $${cell.recommended}` : ''}`}>
                    <Box component="td" sx={{
                      p: 1, textAlign: 'center',
                      bgcolor: cellColor(cell.price, min, max),
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}>
                      ${cell.price}
                    </Box>
                  </MuiTooltip>
                )
              })}
            </tr>
          ))}
        </tbody>
      </Box>
    </Box>
  )
}
