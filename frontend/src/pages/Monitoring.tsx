import { Box, Typography, Card, CardContent, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, BarChart, Bar , CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'

const driftData = Array.from({ length: 14 }, (_, i) => ({
  date: `Sep ${i + 11}`,
  price: 0.04 + Math.random() * 0.06 + (i > 10 ? 0.08 : 0),
  demand: 0.03 + Math.random() * 0.05,
  pageViews: 0.05 + Math.random() * 0.04,
  inventory: 0.02 + Math.random() * 0.03,
}))

const performanceData = Array.from({ length: 14 }, (_, i) => ({
  date: `Sep ${i + 11}`,
  demandMAPE: 7.5 + Math.random() * 2 + (i > 10 ? 3 : 0),
  pricingMAPE: 5.5 + Math.random() * 1.5,
  revenueMAPE: 10 + Math.random() * 3 + (i > 11 ? 4 : 0),
}))

const featureDistribution = [
  { bucket: '$0-50', baseline: 1200, current: 1350 },
  { bucket: '$50-100', baseline: 3400, current: 3200 },
  { bucket: '$100-150', baseline: 2800, current: 2600 },
  { bucket: '$150-200', baseline: 1500, current: 1700 },
  { bucket: '$200-250', baseline: 800, current: 950 },
  { bucket: '$250-300', baseline: 400, current: 380 },
  { bucket: '$300+', baseline: 200, current: 320 },
]

const alerts = [
  { time: 'Sep 24 14:32', severity: 'Critical', model: 'Revenue Predictor', message: 'MAPE exceeded 15% threshold (16.2%) — retrain recommended', status: 'Active' },
  { time: 'Sep 24 10:15', severity: 'Warning', model: 'Demand Forecast', message: 'PSI for price feature = 0.18 (approaching 0.2 threshold)', status: 'Active' },
  { time: 'Sep 23 09:00', severity: 'Info', model: 'Price Sensitivity', message: 'Daily validation passed — champion v2.1 stable', status: 'Resolved' },
  { time: 'Sep 22 16:45', severity: 'Warning', model: 'Anomaly Detector', message: 'Unusual demand spike detected for Oct 4 Padres game (+2.8σ)', status: 'Acknowledged' },
  { time: 'Sep 22 08:30', severity: 'Info', model: 'Demand Forecast', message: 'Challenger v3.3 submitted for validation — MAPE 7.8%', status: 'Resolved' },
  { time: 'Sep 21 11:20', severity: 'Critical', model: 'Revenue Predictor', message: 'Data quality check failed: 12 NULL price records in raw.pricing', status: 'Resolved' },
  { time: 'Sep 20 14:00', severity: 'Info', model: 'Demand Forecast', message: 'Model v3.2 promoted to Production — MAPE improved 8.9%→8.2%', status: 'Resolved' },
]

function severityColor(severity: string): 'error' | 'warning' | 'info' | 'default' {
  if (severity === 'Critical') return 'error'
  if (severity === 'Warning') return 'warning'
  return 'info'
}

export default function Monitoring() {
  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 800 }}>Monitoring</Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 0.5, fontWeight: 600 }}>Data Drift (PSI)</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                  Population Stability Index per feature — threshold: 0.1 (warning), 0.2 (critical)
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={driftData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" stroke="#A0A0B8" fontSize={11} />
                    <YAxis stroke="#A0A0B8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} />
                    <Legend />
                    <Line type="monotone" dataKey="price" stroke="#FD5A1E" strokeWidth={2} name="Price" dot={false} />
                    <Line type="monotone" dataKey="demand" stroke="#EFD19F" strokeWidth={2} name="Demand" dot={false} />
                    <Line type="monotone" dataKey="pageViews" stroke="#29B6F6" strokeWidth={2} name="Page Views" dot={false} />
                    <Line type="monotone" dataKey="inventory" stroke="#4CAF50" strokeWidth={2} name="Inventory" dot={false} />
                    {/* Threshold lines */}
                    <Line type="monotone" dataKey={() => 0.1} stroke="rgba(255,152,0,0.5)" strokeDasharray="8 4" strokeWidth={1} name="Warning" dot={false} />
                    <Line type="monotone" dataKey={() => 0.2} stroke="rgba(244,67,54,0.5)" strokeDasharray="8 4" strokeWidth={1} name="Critical" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 0.5, fontWeight: 600 }}>Model Performance (MAPE %)</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                  Rolling 7-day MAPE — retrain trigger at 15%
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performanceData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" stroke="#A0A0B8" fontSize={11} />
                    <YAxis stroke="#A0A0B8" fontSize={11} unit="%" />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} />
                    <Legend />
                    <Line type="monotone" dataKey="demandMAPE" stroke="#FD5A1E" strokeWidth={2} name="Demand" dot={false} />
                    <Line type="monotone" dataKey="pricingMAPE" stroke="#EFD19F" strokeWidth={2} name="Pricing" dot={false} />
                    <Line type="monotone" dataKey="revenueMAPE" stroke="#F44336" strokeWidth={2} name="Revenue" dot={false} />
                    <Line type="monotone" dataKey={() => 15} stroke="rgba(244,67,54,0.5)" strokeDasharray="8 4" strokeWidth={1} name="Retrain Threshold" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
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
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Feature Distribution: Price (Baseline vs Current)</Typography>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={featureDistribution} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="bucket" stroke="#A0A0B8" fontSize={11} />
                    <YAxis stroke="#A0A0B8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} />
                    <Legend />
                    <Bar dataKey="baseline" fill="rgba(239,209,159,0.3)" name="Baseline (Training)" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="current" fill="rgba(253,90,30,0.6)" name="Current" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Alert Log</Typography>
                <TableContainer sx={{ maxHeight: 320 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary', bgcolor: 'background.paper' }}>Time</TableCell>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary', bgcolor: 'background.paper' }}>Severity</TableCell>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary', bgcolor: 'background.paper' }}>Model</TableCell>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary', bgcolor: 'background.paper' }}>Message</TableCell>
                        <TableCell sx={{ fontWeight: 600, color: 'text.secondary', bgcolor: 'background.paper' }} align="center">Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {alerts.map((a, i) => (
                        <TableRow key={i} sx={{ '&:hover': { bgcolor: 'rgba(253,90,30,0.04)' } }}>
                          <TableCell sx={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>{a.time}</TableCell>
                          <TableCell>
                            <Chip label={a.severity} size="small" color={severityColor(a.severity)} sx={{ fontSize: '0.6rem', height: 18, fontWeight: 600 }} />
                          </TableCell>
                          <TableCell sx={{ fontWeight: 500, fontSize: '0.8rem' }}>{a.model}</TableCell>
                          <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary', maxWidth: 300 }}>{a.message}</TableCell>
                          <TableCell align="center">
                            <Chip
                              label={a.status} size="small" variant="outlined"
                              sx={{ fontSize: '0.6rem', height: 18, borderColor: a.status === 'Active' ? 'error.main' : a.status === 'Acknowledged' ? 'warning.main' : 'text.secondary' }}
                            />
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
    </Box>
  )
}
