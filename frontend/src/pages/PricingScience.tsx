import { useState } from 'react'
import Grid from '@mui/material/Grid2'
import { Box, Typography, Card, CardContent, Slider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, CircularProgress } from '@mui/material'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'
import PriceHeatmap from '../components/PriceHeatmap'

const elasticityData = Array.from({ length: 40 }, (_, i) => {
  const price = 30 + i * 7
  const conversion = Math.max(0.05, 0.95 - (price / 350) + (Math.random() - 0.5) * 0.12)
  return { price, conversion: parseFloat(conversion.toFixed(3)) }
})

const priceRecommendations = [
  { section: 'Field Club', current: 285, min: 295, mean: 310, max: 325, stdDev: 7.6, mlScore: 0.94, lift: 8.8, elasticity: -0.42 },
  { section: 'Club Level 1B', current: 145, min: 148, mean: 155, max: 162, stdDev: 3.6, mlScore: 0.91, lift: 6.9, elasticity: -0.55 },
  { section: 'Club Level 3B', current: 150, min: 152, mean: 160, max: 168, stdDev: 4.1, mlScore: 0.89, lift: 6.7, elasticity: -0.51 },
  { section: 'View Level LF', current: 65, min: 66, mean: 72, max: 78, stdDev: 3.1, mlScore: 0.82, lift: 5.2, elasticity: -0.68 },
  { section: 'View Level RF', current: 68, min: 67, mean: 72, max: 77, stdDev: 2.6, mlScore: 0.84, lift: 5.9, elasticity: -0.63 },
  { section: 'Bleachers', current: 42, min: 33, mean: 38, max: 43, stdDev: 2.6, mlScore: 0.72, lift: -4.2, elasticity: -1.12 },
  { section: 'Arcade', current: 55, min: 55, mean: 60, max: 65, stdDev: 2.6, mlScore: 0.78, lift: 4.5, elasticity: -0.72 },
  { section: 'Upper Box', current: 38, min: 30, mean: 35, max: 40, stdDev: 2.6, mlScore: 0.65, lift: -3.1, elasticity: -1.25 },
  { section: 'Upper Reserved', current: 28, min: 21, mean: 25, max: 29, stdDev: 2.0, mlScore: 0.58, lift: -5.2, elasticity: -1.45 },
]

const avgMlScore = parseFloat((priceRecommendations.reduce((s, r) => s + r.mlScore, 0) / priceRecommendations.length).toFixed(2))

function scoreColor(score: number) {
  if (score >= 0.85) return '#4CAF50'
  if (score >= 0.70) return '#FF9800'
  return '#F44336'
}

function MlScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = scoreColor(score)
  return (
    <Box sx={{ position: 'relative', display: 'inline-flex' }}>
      <CircularProgress
        variant="determinate"
        value={pct}
        size={38}
        thickness={3.5}
        sx={{ color, '& .MuiCircularProgress-circle': { strokeLinecap: 'round' } }}
      />
      <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.65rem', color }}>{pct}%</Typography>
      </Box>
    </Box>
  )
}

function PriceRangeBar({ current, min, mean, max }: { current: number; min: number; mean: number; max: number }) {
  const lo = Math.min(current, min) - 5
  const hi = Math.max(current, max) + 5
  const range = hi - lo
  const pctMin = ((min - lo) / range) * 100
  const pctMax = ((max - lo) / range) * 100
  const pctMean = ((mean - lo) / range) * 100
  const pctCurrent = ((current - lo) / range) * 100
  const goingUp = mean >= current
  const barColor = goingUp ? 'rgba(76,175,80,0.35)' : 'rgba(244,67,54,0.35)'
  const meanColor = goingUp ? '#4CAF50' : '#F44336'

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'baseline', mb: 0.5 }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>${min}</Typography>
        <Typography variant="caption" sx={{ mx: 'auto', fontWeight: 700, fontSize: '0.8rem', color: meanColor }}>
          ${mean}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>${max}</Typography>
      </Box>
      <Box sx={{ position: 'relative', height: 8, borderRadius: 4, bgcolor: 'rgba(255,255,255,0.06)', overflow: 'visible' }}>
        <Box sx={{
          position: 'absolute', left: `${pctMin}%`, width: `${pctMax - pctMin}%`,
          height: '100%', borderRadius: 4, bgcolor: barColor,
        }} />
        <Box sx={{
          position: 'absolute', left: `${pctMean}%`, top: -2, width: 6, height: 12,
          borderRadius: 3, bgcolor: meanColor, transform: 'translateX(-3px)',
        }} />
        <Box sx={{
          position: 'absolute', left: `${pctCurrent}%`, top: -1, width: 2, height: 10,
          bgcolor: 'rgba(239,209,159,0.8)', transform: 'translateX(-1px)',
        }} />
      </Box>
      <Box sx={{ display: 'flex', mt: 0.3 }}>
        <Typography variant="caption" sx={{ fontSize: '0.6rem', color: 'rgba(239,209,159,0.6)', ml: `${pctCurrent}%`, transform: 'translateX(-50%)' }}>
          cur
        </Typography>
      </Box>
    </Box>
  )
}

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
  const stdDevPct = 4.2
  const revStdDev = baseRevenue * (stdDevPct / 100) * Math.max(1, Math.abs(priceChange) / 5)
  const revLow = projectedRevenue - revStdDev
  const revHigh = projectedRevenue + revStdDev

  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 800 }}>Pricing Science</Typography>

      {/* ML Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: '16px !important' }}>
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                  <CircularProgress variant="determinate" value={avgMlScore * 100} size={56} thickness={4}
                    sx={{ color: scoreColor(avgMlScore), '& .MuiCircularProgress-circle': { strokeLinecap: 'round' } }} />
                  <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: scoreColor(avgMlScore) }}>
                      {Math.round(avgMlScore * 100)}%
                    </Typography>
                  </Box>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600 }}>Avg ML Confidence</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{avgMlScore.toFixed(2)}</Typography>
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <Card>
              <CardContent sx={{ py: '16px !important' }}>
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600 }}>Models Contributing</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>3 Models</Typography>
                <Typography variant="caption" color="text.secondary">Demand + Pricing + Inventory</Typography>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card>
              <CardContent sx={{ py: '16px !important' }}>
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600 }}>Prediction Interval</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>95% CI</Typography>
                <Typography variant="caption" color="text.secondary">±1.96σ from mean prediction</Typography>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
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
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Revenue Impact Simulator</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Adjust average price change to see projected revenue range</Typography>
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
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Projected Revenue (95% CI)</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    ${(projectedRevenue / 1000000).toFixed(2)}M
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                    <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                      Range: ${(revLow / 1000000).toFixed(2)}M — ${(revHigh / 1000000).toFixed(2)}M
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                    <Typography variant="body2" sx={{ color: projectedLift >= 0 ? 'success.main' : 'error.main', fontWeight: 600 }}>
                      {projectedLift >= 0 ? '+' : ''}{projectedLift.toFixed(1)}% revenue lift
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      (σ = ${(revStdDev / 1000000).toFixed(2)}M)
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Price Recommendations by Section</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', bgcolor: 'rgba(255,255,255,0.04)', px: 1.5, py: 0.5, borderRadius: 1, border: '1px solid rgba(255,255,255,0.08)' }}>
                95% Confidence Interval · ±1.96σ
              </Typography>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem' }}>Section</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem' }} align="right">Current</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem', minWidth: 180 }}>Recommended Range (95% CI)</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem' }} align="center">Std Dev</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem' }} align="center">ML Score</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem' }} align="right">Rev. Lift</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary', fontSize: '0.7rem' }} align="center">Elasticity</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {priceRecommendations.map((r) => (
                    <TableRow key={r.section} sx={{ '&:hover': { bgcolor: 'rgba(253,90,30,0.04)' } }}>
                      <TableCell sx={{ fontWeight: 500 }}>{r.section}</TableCell>
                      <TableCell align="right" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>${r.current}</TableCell>
                      <TableCell>
                        <PriceRangeBar current={r.current} min={r.min} mean={r.mean} max={r.max} />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>±${r.stdDev.toFixed(1)}</Typography>
                      </TableCell>
                      <TableCell align="center">
                        <MlScoreBadge score={r.mlScore} />
                      </TableCell>
                      <TableCell align="right" sx={{ color: r.lift > 0 ? 'success.main' : 'error.main', fontWeight: 600, fontSize: '0.8rem' }}>
                        {r.lift > 0 ? '+' : ''}{r.lift}%
                      </TableCell>
                      <TableCell align="center" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.elasticity.toFixed(2)}</TableCell>
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
