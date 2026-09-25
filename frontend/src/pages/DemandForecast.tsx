import { useState } from 'react'
import Grid from '@mui/material/Grid2'
import { Box, Typography, Card, CardContent, FormControl, InputLabel, Select, MenuItem, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer , CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'
import DemandChart from '../components/DemandChart'
import KPICard from '../components/KPICard'
import { TrendingUp, Speed, TrackChanges } from '@mui/icons-material'

const games = [
  { id: 'g1', label: 'Sep 26 — vs LA Dodgers', opponent: 'Dodgers' },
  { id: 'g2', label: 'Sep 27 — vs LA Dodgers', opponent: 'Dodgers' },
  { id: 'g3', label: 'Sep 28 — vs LA Dodgers', opponent: 'Dodgers' },
  { id: 'g4', label: 'Oct 1 — vs AZ Diamondbacks', opponent: 'D-backs' },
  { id: 'g5', label: 'Oct 2 — vs AZ Diamondbacks', opponent: 'D-backs' },
  { id: 'g6', label: 'Oct 4 — vs SD Padres', opponent: 'Padres' },
  { id: 'g7', label: 'Oct 5 — vs SD Padres', opponent: 'Padres' },
  { id: 'g8', label: 'Oct 8 — vs Colorado Rockies', opponent: 'Rockies' },
  { id: 'g9', label: 'Oct 11 — vs SEA Mariners', opponent: 'Mariners' },
  { id: 'g10', label: 'Oct 12 — vs SEA Mariners', opponent: 'Mariners' },
]

const timeSeriesData = Array.from({ length: 30 }, (_, i) => {
  const predicted = 28000 + Math.sin(i / 4) * 5000 + i * 200
  return {
    date: `Sep ${i + 1}`,
    actual: i < 24 ? predicted + (Math.random() - 0.5) * 3000 : undefined,
    predicted: Math.round(predicted),
    upper: Math.round(predicted + 3000),
    lower: Math.round(predicted - 3000),
  }
})

const sectionDemand = [
  { section: 'Field Club', demand: 2600, capacity: 2800 },
  { section: 'Club 1B', demand: 2700, capacity: 3200 },
  { section: 'Club 3B', demand: 2900, capacity: 3200 },
  { section: 'View LF', demand: 3100, capacity: 4500 },
  { section: 'View RF', demand: 3400, capacity: 4500 },
  { section: 'Bleachers', demand: 3400, capacity: 5600 },
  { section: 'Arcade', demand: 2400, capacity: 3000 },
  { section: 'Upper Box', demand: 3500, capacity: 6000 },
  { section: 'Upper Res', demand: 2700, capacity: 5500 },
]

const featureImportance = [
  { feature: 'Opponent Strength', importance: 0.28 },
  { feature: 'Days to Event', importance: 0.21 },
  { feature: 'Page Views (7d avg)', importance: 0.16 },
  { feature: 'Day of Week', importance: 0.12 },
  { feature: 'Promotion Flag', importance: 0.09 },
  { feature: 'Season Win %', importance: 0.07 },
  { feature: 'Secondary Mkt Premium', importance: 0.04 },
  { feature: 'Weather Score', importance: 0.03 },
]

export default function DemandForecast() {
  const [selectedGame, setSelectedGame] = useState('g1')

  return (
    <Box sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>Demand Forecast</Typography>
        <FormControl size="small" sx={{ minWidth: 280 }}>
          <InputLabel>Select Game</InputLabel>
          <Select value={selectedGame} label="Select Game" onChange={(e) => setSelectedGame(e.target.value)}>
            {games.map((g) => <MenuItem key={g.id} value={g.id}>{g.label}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <KPICard icon={<TrendingUp fontSize="small" />} title="Forecast Demand" value="38,200" change={12.4} sparkline={[32, 33, 35, 34, 36, 37, 38]} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <KPICard icon={<Speed fontSize="small" />} title="MAPE" value="8.2%" change={-2.1} sparkline={[12, 11, 10, 9, 9, 8, 8]} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <KPICard icon={<TrackChanges fontSize="small" />} title="RMSE" value="1,240" change={-5.3} sparkline={[1500, 1400, 1350, 1300, 1280, 1260, 1240]} />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardContent>
                <DemandChart data={timeSeriesData} title="Demand: Actual vs Predicted (with Confidence Bands)" showConfidence />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Demand Drivers</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Feature</TableCell>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="right">Importance</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {featureImportance.map((f) => (
                        <TableRow key={f.feature}>
                          <TableCell>{f.feature}</TableCell>
                          <TableCell align="right">
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
                              <Box sx={{ width: 60, height: 6, bgcolor: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
                                <Box sx={{ width: `${f.importance * 100 / 0.28}%`, height: '100%', bgcolor: 'primary.main', borderRadius: 3 }} />
                              </Box>
                              <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 32 }}>{(f.importance * 100).toFixed(0)}%</Typography>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Section-Level Demand Breakdown</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sectionDemand} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="section" stroke="#A0A0B8" fontSize={11} />
                <YAxis stroke="#A0A0B8" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} />
                <Bar dataKey="demand" fill="#FD5A1E" radius={[4, 4, 0, 0]} name="Predicted Demand" />
                <Bar dataKey="capacity" fill="rgba(239,209,159,0.2)" radius={[4, 4, 0, 0]} name="Capacity" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  )
}
