import { Box, Typography, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, LinearProgress } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, LineChart, Line , CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'
import SeatMap from '../components/SeatMap'

const sectionData = [
  { section: 'Field Club', capacity: 2800, sold: 2660, available: 100, masked: 40, tier1: 1200, tier2: 800, tier3: 660 },
  { section: 'Club Level 1B', capacity: 3200, sold: 2720, available: 320, masked: 160, tier1: 900, tier2: 1000, tier3: 820 },
  { section: 'Club Level 3B', capacity: 3200, sold: 2880, available: 220, masked: 100, tier1: 950, tier2: 1050, tier3: 880 },
  { section: 'View Level LF', capacity: 4500, sold: 3150, available: 1050, masked: 300, tier1: 800, tier2: 1200, tier3: 1150 },
  { section: 'View Level RF', capacity: 4500, sold: 3375, available: 825, masked: 300, tier1: 900, tier2: 1300, tier3: 1175 },
  { section: 'Bleachers', capacity: 5600, sold: 3360, available: 1740, masked: 500, tier1: 600, tier2: 1200, tier3: 1560 },
  { section: 'Arcade', capacity: 3000, sold: 2400, available: 400, masked: 200, tier1: 700, tier2: 900, tier3: 800 },
  { section: 'Upper Box', capacity: 6000, sold: 3600, available: 1800, masked: 600, tier1: 500, tier2: 1400, tier3: 1700 },
  { section: 'Upper Reserved', capacity: 5500, sold: 2750, available: 2150, masked: 600, tier1: 400, tier2: 1100, tier3: 1250 },
]

const allocationData = sectionData.map((s) => ({
  section: s.section.replace('Level ', '').replace('Reserved', 'Res'),
  'Tier 1 (Premium)': s.tier1,
  'Tier 2 (Standard)': s.tier2,
  'Tier 3 (Value)': s.tier3,
}))

const sellThroughTimeline = Array.from({ length: 14 }, (_, i) => ({
  day: `Day ${i + 1}`,
  fieldClub: Math.min(100, 45 + i * 4 + Math.random() * 3),
  clubLevel: Math.min(100, 35 + i * 3.5 + Math.random() * 4),
  viewLevel: Math.min(100, 25 + i * 3 + Math.random() * 5),
  bleachers: Math.min(100, 20 + i * 2.5 + Math.random() * 4),
}))

const recommendations = [
  { section: 'Bleachers', action: 'Release 200 masked seats', reason: 'Sell-through below target, 14 days to game', priority: 'High' },
  { section: 'Upper Box', action: 'Release 300 masked seats', reason: 'Low velocity, consider price reduction', priority: 'High' },
  { section: 'View Level LF', action: 'Mask 100 premium seats', reason: 'High demand expected for Dodgers series', priority: 'Medium' },
  { section: 'Field Club', action: 'Hold current allocation', reason: 'On track for sellout', priority: 'Low' },
  { section: 'Upper Reserved', action: 'Reduce Tier 1 by 150, add to Tier 3', reason: 'Tier 1 not selling, Tier 3 demand strong', priority: 'Medium' },
]

export default function InventoryOptimizer() {
  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 800 }}>Inventory Optimizer</Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardContent>
                <SeatMap />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Section Summary</Typography>
                <Box sx={{ maxHeight: 380, overflow: 'auto' }}>
                  {sectionData.map((s) => {
                    const pct = Math.round((s.sold / s.capacity) * 100)
                    return (
                      <Box key={s.section} sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>{s.section}</Typography>
                          <Typography variant="caption" sx={{ color: pct > 85 ? 'error.main' : pct > 65 ? 'warning.main' : 'success.main', fontWeight: 600 }}>{pct}%</Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={pct}
                          sx={{
                            height: 6, borderRadius: 3,
                            bgcolor: 'rgba(255,255,255,0.06)',
                            '& .MuiLinearProgress-bar': {
                              bgcolor: pct > 85 ? 'error.main' : pct > 65 ? 'warning.main' : 'success.main',
                              borderRadius: 3,
                            },
                          }}
                        />
                        <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">Sold: {s.sold.toLocaleString()}</Typography>
                          <Typography variant="caption" color="text.secondary">Avail: {s.available.toLocaleString()}</Typography>
                          <Typography variant="caption" color="text.secondary">Masked: {s.masked}</Typography>
                        </Box>
                      </Box>
                    )
                  })}
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 0 }}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Allocation by Price Tier</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={allocationData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="section" stroke="#A0A0B8" fontSize={10} angle={-20} textAnchor="end" />
                    <YAxis stroke="#A0A0B8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} />
                    <Legend />
                    <Bar dataKey="Tier 1 (Premium)" stackId="a" fill="#FD5A1E" />
                    <Bar dataKey="Tier 2 (Standard)" stackId="a" fill="#EFD19F" />
                    <Bar dataKey="Tier 3 (Value)" stackId="a" fill="rgba(255,255,255,0.2)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Sell-Through Timeline</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={sellThroughTimeline} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="day" stroke="#A0A0B8" fontSize={11} />
                    <YAxis stroke="#A0A0B8" fontSize={11} unit="%" />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} />
                    <Legend />
                    <Line type="monotone" dataKey="fieldClub" stroke="#FD5A1E" strokeWidth={2} name="Field Club" dot={false} />
                    <Line type="monotone" dataKey="clubLevel" stroke="#EFD19F" strokeWidth={2} name="Club Level" dot={false} />
                    <Line type="monotone" dataKey="viewLevel" stroke="#29B6F6" strokeWidth={2} name="View Level" dot={false} />
                    <Line type="monotone" dataKey="bleachers" stroke="#4CAF50" strokeWidth={2} name="Bleachers" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Allocation Recommendations</Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Section</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Action</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Reason</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Priority</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recommendations.map((r) => (
                    <TableRow key={r.section} sx={{ '&:hover': { bgcolor: 'rgba(253,90,30,0.04)' } }}>
                      <TableCell sx={{ fontWeight: 500 }}>{r.section}</TableCell>
                      <TableCell>{r.action}</TableCell>
                      <TableCell sx={{ color: 'text.secondary' }}>{r.reason}</TableCell>
                      <TableCell align="center">
                        <Chip label={r.priority} size="small" color={r.priority === 'High' ? 'error' : r.priority === 'Medium' ? 'warning' : 'success'} sx={{ fontSize: '0.65rem', height: 20, fontWeight: 600 }} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  )
}
