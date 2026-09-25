import { Box, Typography, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { AttachMoney, ConfirmationNumber, TrendingUp, Percent } from '@mui/icons-material'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer , CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'
import KPICard from '../components/KPICard'

const revenueData = Array.from({ length: 30 }, (_, i) => ({
  date: `Sep ${i + 1}`,
  revenue: 280000 + Math.random() * 180000 + (i > 20 ? 50000 : 0),
}))

const upcomingGames = [
  { date: 'Sep 26', opponent: 'LA Dodgers', demandIdx: 9.2, recPrice: '$142', sellThrough: 88, status: 'High' },
  { date: 'Sep 27', opponent: 'LA Dodgers', demandIdx: 9.0, recPrice: '$138', sellThrough: 85, status: 'High' },
  { date: 'Sep 28', opponent: 'LA Dodgers', demandIdx: 8.8, recPrice: '$135', sellThrough: 82, status: 'High' },
  { date: 'Oct 1', opponent: 'AZ Diamondbacks', demandIdx: 6.4, recPrice: '$89', sellThrough: 64, status: 'Medium' },
  { date: 'Oct 2', opponent: 'AZ Diamondbacks', demandIdx: 6.1, recPrice: '$85', sellThrough: 60, status: 'Medium' },
  { date: 'Oct 4', opponent: 'SD Padres', demandIdx: 7.5, recPrice: '$105', sellThrough: 72, status: 'High' },
  { date: 'Oct 5', opponent: 'SD Padres', demandIdx: 7.2, recPrice: '$98', sellThrough: 68, status: 'Medium' },
]

const modelStatus = [
  { name: 'Demand Forecast', version: 'v3.2', status: 'healthy', mape: '8.2%' },
  { name: 'Price Sensitivity', version: 'v2.1', status: 'healthy', mape: '6.4%' },
  { name: 'Revenue Predictor', version: 'v1.8', status: 'warning', mape: '12.1%' },
  { name: 'Anomaly Detector', version: 'v1.3', status: 'healthy', mape: 'N/A' },
  { name: 'Inventory Optimizer', version: 'v2.0', status: 'healthy', mape: '5.8%' },
]

export default function Dashboard() {
  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 800 }}>
        <Box component="span" sx={{ color: 'primary.main' }}>Box</Box>score Dashboard
      </Typography>

      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard icon={<AttachMoney fontSize="small" />} title="Total Revenue" value="$12.4M" change={8.3} sparkline={[82, 85, 78, 90, 95, 88, 102]} delay={0} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard icon={<ConfirmationNumber fontSize="small" />} title="Tickets Sold" value="142K" change={5.1} sparkline={[120, 125, 130, 128, 135, 138, 142]} delay={0.1} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard icon={<TrendingUp fontSize="small" />} title="Avg Price" value="$87" change={3.2} sparkline={[78, 80, 82, 84, 85, 86, 87]} delay={0.2} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard icon={<Percent fontSize="small" />} title="Sell-Through" value="78%" change={-1.4} sparkline={[80, 79, 81, 78, 77, 79, 78]} delay={0.3} />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Revenue Trend (30 Days)</Typography>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={revenueData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#FD5A1E" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#FD5A1E" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" stroke="#A0A0B8" fontSize={11} />
                    <YAxis stroke="#A0A0B8" fontSize={11} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} formatter={(v: number) => [`$${v.toLocaleString()}`, 'Revenue']} />
                    <Area type="monotone" dataKey="revenue" stroke="#FD5A1E" fill="url(#revGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Model Health</Typography>
                {modelStatus.map((m) => (
                  <Box key={m.name} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1, borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>{m.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{m.version} · MAPE {m.mape}</Typography>
                    </Box>
                    <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: m.status === 'healthy' ? 'success.main' : m.status === 'warning' ? 'warning.main' : 'error.main' }} />
                  </Box>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Upcoming Games</Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Date</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Opponent</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Demand</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Rec. Price</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Sell-Through</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {upcomingGames.map((g) => (
                    <TableRow key={g.date + g.opponent} sx={{ '&:hover': { bgcolor: 'rgba(253,90,30,0.04)' } }}>
                      <TableCell>{g.date}</TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>{g.opponent}</TableCell>
                      <TableCell align="center" sx={{ fontWeight: 600, color: g.demandIdx > 8 ? 'primary.main' : 'text.primary' }}>{g.demandIdx}</TableCell>
                      <TableCell align="center">{g.recPrice}</TableCell>
                      <TableCell align="center">{g.sellThrough}%</TableCell>
                      <TableCell align="center">
                        <Chip label={g.status} size="small" color={g.status === 'High' ? 'error' : 'warning'} sx={{ fontSize: '0.7rem', fontWeight: 600, height: 22 }} />
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
