import { Box, Typography, Card, CardContent, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Divider } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { motion } from 'framer-motion'
import { CheckCircle, Warning, Archive, Science } from '@mui/icons-material'

interface ModelInfo {
  name: string
  displayName: string
  version: string
  stage: 'Production' | 'Staging' | 'Archived'
  metrics: { label: string; value: string }[]
  lastTrained: string
  challenger?: { version: string; metrics: { label: string; value: string }[] }
}

const models: ModelInfo[] = [
  {
    name: 'boxscore-demand-forecast', displayName: 'Demand Forecast', version: 'v3.2', stage: 'Production',
    metrics: [{ label: 'MAPE', value: '8.2%' }, { label: 'RMSE', value: '1,240' }, { label: 'R²', value: '0.89' }],
    lastTrained: 'Sep 20, 2026',
    challenger: { version: 'v3.3', metrics: [{ label: 'MAPE', value: '7.8%' }, { label: 'RMSE', value: '1,180' }, { label: 'R²', value: '0.91' }] },
  },
  {
    name: 'boxscore-price-sensitivity', displayName: 'Price Sensitivity', version: 'v2.1', stage: 'Production',
    metrics: [{ label: 'MAPE', value: '6.4%' }, { label: 'R²', value: '0.92' }, { label: 'AUC', value: '0.87' }],
    lastTrained: 'Sep 18, 2026',
  },
  {
    name: 'boxscore-revenue-predictor', displayName: 'Revenue Predictor', version: 'v1.8', stage: 'Staging',
    metrics: [{ label: 'MAPE', value: '12.1%' }, { label: 'R²', value: '0.78' }, { label: 'Bias', value: '+2.3%' }],
    lastTrained: 'Sep 15, 2026',
    challenger: { version: 'v1.9', metrics: [{ label: 'MAPE', value: '10.5%' }, { label: 'R²', value: '0.82' }, { label: 'Bias', value: '+1.1%' }] },
  },
  {
    name: 'boxscore-anomaly-detector', displayName: 'Anomaly Detector', version: 'v1.3', stage: 'Production',
    metrics: [{ label: 'Precision', value: '0.91' }, { label: 'Recall', value: '0.85' }, { label: 'F1', value: '0.88' }],
    lastTrained: 'Sep 12, 2026',
  },
  {
    name: 'boxscore-inventory-optimizer', displayName: 'Inventory Optimizer', version: 'v2.0', stage: 'Production',
    metrics: [{ label: 'Obj Value', value: '$4.2M' }, { label: 'Fill Rate', value: '94%' }, { label: 'Coverage', value: '98%' }],
    lastTrained: 'Sep 19, 2026',
  },
]

const validationHistory = [
  { date: 'Sep 20', model: 'Demand Forecast', champion: 'v3.1', challenger: 'v3.2', result: 'Promoted', metric: 'MAPE 8.2% < 8.9%' },
  { date: 'Sep 18', model: 'Price Sensitivity', champion: 'v2.0', challenger: 'v2.1', result: 'Promoted', metric: 'R² 0.92 > 0.89' },
  { date: 'Sep 15', model: 'Revenue Predictor', champion: 'v1.7', challenger: 'v1.8', result: 'Rejected', metric: 'MAPE 12.1% > 11.5%' },
  { date: 'Sep 12', model: 'Anomaly Detector', champion: 'v1.2', challenger: 'v1.3', result: 'Promoted', metric: 'F1 0.88 > 0.84' },
  { date: 'Sep 10', model: 'Demand Forecast', champion: 'v3.0', challenger: 'v3.1', result: 'Promoted', metric: 'RMSE 1280 < 1350' },
]

function stageIcon(stage: string) {
  if (stage === 'Production') return <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
  if (stage === 'Staging') return <Science sx={{ fontSize: 16, color: 'warning.main' }} />
  return <Archive sx={{ fontSize: 16, color: 'text.secondary' }} />
}

function stageColor(stage: string): 'success' | 'warning' | 'default' {
  if (stage === 'Production') return 'success'
  if (stage === 'Staging') return 'warning'
  return 'default'
}

export default function ModelRegistry() {
  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 800 }}>Model Registry</Typography>

      <Grid container spacing={2.5}>
        {models.map((m, i) => (
          <Grid key={m.name} size={{ xs: 12, sm: 6, lg: 4 }}>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                    <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{m.displayName}</Typography>
                      <Typography variant="caption" color="text.secondary">{m.name}</Typography>
                    </Box>
                    <Chip icon={stageIcon(m.stage)} label={m.stage} size="small" color={stageColor(m.stage)} sx={{ fontSize: '0.65rem', fontWeight: 600, height: 24 }} />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip label={m.version} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center' }}>Trained {m.lastTrained}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    {m.metrics.map((metric) => (
                      <Box key={metric.label}>
                        <Typography variant="caption" color="text.secondary">{metric.label}</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{metric.value}</Typography>
                      </Box>
                    ))}
                  </Box>

                  {m.challenger && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Box sx={{ p: 1.5, bgcolor: 'rgba(255,152,0,0.08)', borderRadius: 1.5, border: '1px solid rgba(255,152,0,0.15)' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                          <Warning sx={{ fontSize: 14, color: 'warning.main' }} />
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'warning.main' }}>Challenger {m.challenger.version}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          {m.challenger.metrics.map((metric) => (
                            <Box key={metric.label}>
                              <Typography variant="caption" color="text.secondary">{metric.label}</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem' }}>{metric.value}</Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    </>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        ))}
      </Grid>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Validation History</Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Date</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Model</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Champion</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Challenger</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Metric</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }} align="center">Result</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {validationHistory.map((v, i) => (
                    <TableRow key={i} sx={{ '&:hover': { bgcolor: 'rgba(253,90,30,0.04)' } }}>
                      <TableCell>{v.date}</TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>{v.model}</TableCell>
                      <TableCell>{v.champion}</TableCell>
                      <TableCell>{v.challenger}</TableCell>
                      <TableCell sx={{ fontSize: '0.8rem' }}>{v.metric}</TableCell>
                      <TableCell align="center">
                        <Chip label={v.result} size="small" color={v.result === 'Promoted' ? 'success' : 'error'} sx={{ fontSize: '0.65rem', height: 20, fontWeight: 600 }} />
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
