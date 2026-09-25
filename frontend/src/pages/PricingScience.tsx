import { useState } from 'react'
import Grid from '@mui/material/Grid2'
import { Box, Typography, Card, CardContent, Slider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip } from '@mui/material'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer , CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'
import PriceHeatmap from '../components/PriceHeatmap'

const elasticityData = Array.from({ length: 40 }, (_, i) => {
  const price = 30 + i * 7
  const conversion = Math.max(0.05, 0.95 - (price / 350) + (Math.random() - 0.5) * 0.12)
  return { price, conversion: parseFloat(conversion.toFixed(3)) }
})

const priceRecommendations = [
  { section: 'Field Club', current: 285, recommended: 310, lift: 8.8, confidence: 'High', elasticity: -0.42 },
  { section: 'Club Level 1B', current: 145, recommended: 155, lift: 6.9, confidence: 'High', elasticity: -0.55 },
  { section: 'Club Level 3B', current: 150, recommended: 160, lift: 6.7, confidence: 'High', elasticity: -0.51 },
  { section: 'View Level LF', current: 65, recommended: 72, lift: 5.2, confidence: 'Medium', elasticity: -0.68 },
  { section: 'View Level RF', current: 68, recommended: 72, lift: 5.9, confidence: 'Medium', elasticity: -0.63 },
  { section: 'Bleachers', current: 42, recommended: 38, lift: -4.2, confidence: 'Medium', elasticity: -1.12 },
  { section: 'Arcade', current: 55, recommended: 60, lift: 4.5, confidence: 'Medium', elasticity: -0.72 },
  { section: 'Upper Box', current: 38, recommended: 35, lift: -3.1, confidence: 'Low', elasticity: -1.25 },
  { section: 'Upper Reserved', current: 28, recommended: 25, lift: -5.2, confidence: 'Low', elasticity: -1.45 },
]

const heatmapSections = ['Field Club', 'Club 1B', 'Club 3B', 'View LF', 'View RF', 'Bleachers', 'Arcade', 'Upper Box']
const heatmapTypes = ['Weekday', 'Weekend', 'Promo Night', 'Rivalry']
const heatmapData = [
  [{ price: 250 }, { price: 285, recommended: 310 }, { price: 310 }, { price: 350 }],
  [{ price: 120 }, { price: 145, recommended: 155 }, { price: 160 }, { price: 185 }],
  [{ price: 125 }, { price: 150, recommended: 160 }, { price: 165 }, { price: 190 }],
  [{ price: 50 }, { price: 65, recommended: 72 }, { price: 75 }, { price: 95 }],
  [{ price: 52 }, { price: 68, recommended: 72 }, { price: 78 }, { price: 98 }],
  [{ price: 32 }, { price: 42, recommended: 38 }, { price: 48 }, { price: 62 }],
  [{ price: 42 }, { price: 55, recommended: 60 }, { price: 62 }, { price: 78 }],
  [{ price: 28 }, { price: 38, recommended: 35 }, { price: 42 }, { price: 55 }],
]

export default function PricingScience() {
  const [priceChange, setPriceChange] = useState(0)
  const baseRevenue = 12400000
  const elasticity = -0.65
  const projectedLift = priceChange * elasticity * -1 + priceChange
  const projectedRevenue = baseRevenue * (1 + projectedLift / 100)

  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 800 }}>Pricing Science</Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Price Elasticity Curve</Typography>
                <ResponsiveContainer width="100%" height={320}>
                  <ScatterChart margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis type="number" dataKey="price" name="Price ($)" stroke="#A0A0B8" fontSize={11} label={{ value: 'Price ($)', position: 'bottom', fill: '#A0A0B8', fontSize: 11 }} />
                    <YAxis type="number" dataKey="conversion" name="Conversion" stroke="#A0A0B8" fontSize={11} label={{ value: 'Conversion Rate', angle: -90, position: 'insideLeft', fill: '#A0A0B8', fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} formatter={(v: number, name: string) => [name === 'price' ? `$${v}` : `${(v * 100).toFixed(1)}%`, name === 'price' ? 'Price' : 'Conversion']} />
                    <Scatter data={elasticityData} fill="#FD5A1E" fillOpacity={0.7} />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Revenue Impact Simulator</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Adjust average price change to see projected revenue impact</Typography>
                <Box sx={{ px: 2 }}>
                  <Slider
                    value={priceChange}
                    onChange={(_, v) => setPriceChange(v as number)}
                    min={-20} max={20} step={1}
                    marks={[{ value: -20, label: '-20%' }, { value: 0, label: '0%' }, { value: 20, label: '+20%' }]}
                    sx={{ color: priceChange >= 0 ? 'success.main' : 'error.main' }}
                  />
                </Box>
                <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(253,90,30,0.08)', borderRadius: 2, border: '1px solid rgba(253,90,30,0.2)' }}>
                  <Typography variant="body2" color="text.secondary">Price Change</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700, color: priceChange >= 0 ? 'success.main' : 'error.main' }}>
                    {priceChange >= 0 ? '+' : ''}{priceChange}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Projected Revenue</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    ${(projectedRevenue / 1000000).toFixed(2)}M
                  </Typography>
                  <Typography variant="body2" sx={{ color: projectedLift >= 0 ? 'success.main' : 'error.main', fontWeight: 600, mt: 0.5 }}>
                    {projectedLift >= 0 ? '+' : ''}{projectedLift.toFixed(1)}% revenue lift
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Price Recommendations by Section</Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Section</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="right">Current</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="right">Recommended</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="right">Lift</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Elasticity</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Confidence</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {priceRecommendations.map((r) => (
                    <TableRow key={r.section} sx={{ '&:hover': { bgcolor: 'rgba(253,90,30,0.04)' } }}>
                      <TableCell sx={{ fontWeight: 500 }}>{r.section}</TableCell>
                      <TableCell align="right">${r.current}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600, color: r.recommended > r.current ? 'success.main' : 'error.main' }}>${r.recommended}</TableCell>
                      <TableCell align="right" sx={{ color: r.lift > 0 ? 'success.main' : 'error.main', fontWeight: 600 }}>{r.lift > 0 ? '+' : ''}{r.lift}%</TableCell>
                      <TableCell align="center">{r.elasticity.toFixed(2)}</TableCell>
                      <TableCell align="center">
                        <Chip label={r.confidence} size="small" color={r.confidence === 'High' ? 'success' : r.confidence === 'Medium' ? 'warning' : 'default'} sx={{ fontSize: '0.65rem', height: 20, fontWeight: 600 }} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <PriceHeatmap sections={heatmapSections} gameTypes={heatmapTypes} data={heatmapData} />
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  )
}
