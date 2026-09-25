import { useState, useEffect } from 'react'
import {
  Box, Typography, Paper, Chip, Button, CircularProgress, LinearProgress,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Snackbar,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import {
  CheckCircle, Cancel, TrendingUp, TrendingDown, SwapHoriz, Star,
  EmojiEvents, ScienceOutlined, CompareArrows,
} from '@mui/icons-material'
import { motion } from 'framer-motion'

interface MetricDiff {
  champion: number
  challenger: number
  diff: number
  diff_pct: number
}

interface Comparison {
  model_name: string
  uc_name: string
  endpoint: string
  primary_metric: string
  improvement_pct: number
  challenger_wins: boolean
  champion: { version: number; confidence_score: number; metrics: Record<string, number> }
  challenger: {
    version: number; confidence_score: number; metrics: Record<string, number>
    features_added: string[]; features_removed: string[]
  }
  metric_diffs: Record<string, MetricDiff>
  threshold: number
  meets_threshold: boolean
  evaluation_status: string
}

const ConfidenceGauge = ({ score, label }: { score: number; label: string }) => {
  const color = score >= 0.9 ? '#4caf50' : score >= 0.8 ? '#ff9800' : '#f44336'
  return (
    <Box sx={{ textAlign: 'center' }}>
      <Box sx={{ position: 'relative', display: 'inline-flex' }}>
        <CircularProgress variant="determinate" value={score * 100} size={56}
          sx={{ color, '& .MuiCircularProgress-circle': { strokeLinecap: 'round' } }} />
        <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="caption" fontWeight={700} color={color}>
            {(score * 100).toFixed(0)}%
          </Typography>
        </Box>
      </Box>
      <Typography variant="caption" display="block" color="text.secondary" mt={0.5}>{label}</Typography>
    </Box>
  )
}

const MetricBar = ({ name, champion, challenger, lowerBetter }: {
  name: string; champion: number; challenger: number; lowerBetter: boolean
}) => {
  const maxVal = Math.max(Math.abs(champion), Math.abs(challenger)) * 1.2 || 1
  const champPct = (Math.abs(champion) / maxVal) * 100
  const challPct = (Math.abs(challenger) / maxVal) * 100
  const challWins = lowerBetter ? challenger < champion : challenger > champion
  const diff = challenger - champion
  const diffPct = champion !== 0 ? ((diff / Math.abs(champion)) * 100).toFixed(1) : '—'

  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="caption" fontWeight={600} textTransform="uppercase">{name}</Typography>
        <Chip
          size="small"
          label={`${Number(diffPct) > 0 ? '+' : ''}${diffPct}%`}
          icon={challWins ? <TrendingUp sx={{ fontSize: 14 }} /> : <TrendingDown sx={{ fontSize: 14 }} />}
          sx={{
            height: 20, fontSize: '0.65rem', fontWeight: 700,
            bgcolor: challWins ? 'rgba(76,175,80,0.15)' : 'rgba(244,67,54,0.15)',
            color: challWins ? '#4caf50' : '#f44336',
          }}
        />
      </Box>
      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
        <Typography variant="caption" sx={{ width: 60, textAlign: 'right', color: '#ff9800' }}>
          {typeof champion === 'number' && champion < 1 ? champion.toFixed(3) : champion}
        </Typography>
        <Box sx={{ flex: 1, display: 'flex', gap: 0.5, alignItems: 'center' }}>
          <LinearProgress variant="determinate" value={champPct}
            sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: 'rgba(255,152,0,0.1)',
              '& .MuiLinearProgress-bar': { bgcolor: '#ff9800', borderRadius: 3 } }} />
          <LinearProgress variant="determinate" value={challPct}
            sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: 'rgba(33,150,243,0.1)',
              '& .MuiLinearProgress-bar': { bgcolor: '#2196f3', borderRadius: 3 } }} />
        </Box>
        <Typography variant="caption" sx={{ width: 60, color: '#2196f3' }}>
          {typeof challenger === 'number' && challenger < 1 ? challenger.toFixed(3) : challenger}
        </Typography>
      </Box>
    </Box>
  )
}

export default function ChampionChallenger() {
  const [data, setData] = useState<{ comparisons: Comparison[]; summary: any } | null>(null)
  const [loading, setLoading] = useState(true)
  const [promoting, setPromoting] = useState<string | null>(null)
  const [dialogModel, setDialogModel] = useState<string | null>(null)
  const [dialogAction, setDialogAction] = useState<'accept' | 'reject'>('accept')
  const [reason, setReason] = useState('')
  const [snack, setSnack] = useState<{ open: boolean; msg: string; severity: 'success' | 'error' }>({ open: false, msg: '', severity: 'success' })

  const fetchData = () => {
    setLoading(true)
    fetch('/api/champion-challenger/compare')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  const handlePromote = async () => {
    if (!dialogModel) return
    setPromoting(dialogModel)
    try {
      const resp = await fetch('/api/champion-challenger/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: dialogModel, action: dialogAction, reason }),
      })
      const result = await resp.json()
      if (result.status === 'promoted') {
        setSnack({ open: true, msg: `${dialogModel} v${result.new_champion_version} promoted to Champion! Alias: ${result.alias_swapped ? 'Swapped' : 'Pending'} | Endpoint: ${result.endpoint_updated ? 'Updated' : 'Pending'}`, severity: 'success' })
      } else {
        setSnack({ open: true, msg: `${dialogModel} challenger rejected — champion retained`, severity: 'success' })
      }
      fetchData()
    } catch {
      setSnack({ open: true, msg: 'Failed to update model', severity: 'error' })
    }
    setPromoting(null)
    setDialogModel(null)
    setReason('')
  }

  const lowerBetterMetrics = new Set(['mape', 'rmse', 'mae'])

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}><CircularProgress /></Box>
  if (!data) return <Alert severity="error">Failed to load champion/challenger data</Alert>

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <CompareArrows sx={{ fontSize: 32, color: 'primary.main' }} />
        <Box>
          <Typography variant="h5" fontWeight={800}>Champion / Challenger</Typography>
          <Typography variant="body2" color="text.secondary">
            Compare model versions, evaluate improvements, and promote with a single click
          </Typography>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Models', value: data.summary.total_models, icon: <ScienceOutlined />, color: '#2196f3' },
          { label: 'Challengers Winning', value: data.summary.challengers_winning, icon: <TrendingUp />, color: '#4caf50' },
          { label: 'Promoted', value: data.summary.promoted, icon: <EmojiEvents />, color: '#ff9800' },
          { label: 'Rejected', value: data.summary.rejected, icon: <Cancel />, color: '#f44336' },
          { label: 'Pending Review', value: data.summary.pending, icon: <SwapHoriz />, color: '#9c27b0' },
        ].map((card) => (
          <Grid size={{ xs: 6, md: 2.4 }} key={card.label}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Box sx={{ color: card.color, mb: 0.5 }}>{card.icon}</Box>
              <Typography variant="h4" fontWeight={800} color={card.color}>{card.value}</Typography>
              <Typography variant="caption" color="text.secondary">{card.label}</Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Model Comparison Cards */}
      {data.comparisons.map((comp, idx) => (
        <motion.div key={comp.model_name} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1 }}>
          <Paper sx={{ p: 3, mb: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Typography variant="h6" fontWeight={700}>{comp.model_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</Typography>
                <Chip size="small" label={comp.uc_name} sx={{ fontSize: '0.65rem', bgcolor: 'rgba(255,255,255,0.05)' }} />
                {comp.evaluation_status === 'accept' && <Chip size="small" icon={<CheckCircle sx={{ fontSize: 14 }} />} label="Promoted" color="success" />}
                {comp.evaluation_status === 'reject' && <Chip size="small" icon={<Cancel sx={{ fontSize: 14 }} />} label="Rejected" color="error" />}
                {comp.evaluation_status === 'pending' && <Chip size="small" icon={<SwapHoriz sx={{ fontSize: 14 }} />} label="Pending Review" color="warning" />}
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {comp.evaluation_status === 'pending' && (
                  <>
                    <Button variant="contained" size="small" color="success" startIcon={<CheckCircle />}
                      onClick={() => { setDialogModel(comp.model_name); setDialogAction('accept') }}
                      disabled={!!promoting}>
                      Accept Challenger
                    </Button>
                    <Button variant="outlined" size="small" color="error" startIcon={<Cancel />}
                      onClick={() => { setDialogModel(comp.model_name); setDialogAction('reject') }}
                      disabled={!!promoting}>
                      Reject
                    </Button>
                  </>
                )}
              </Box>
            </Box>

            {/* Champion vs Challenger side by side */}
            <Grid container spacing={3}>
              {/* Champion */}
              <Grid size={{ xs: 12, md: 5 }}>
                <Paper sx={{ p: 2, bgcolor: 'rgba(255,152,0,0.05)', border: '1px solid rgba(255,152,0,0.2)' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <Star sx={{ color: '#ff9800', fontSize: 20 }} />
                    <Typography fontWeight={700} color="#ff9800">Champion v{comp.champion.version}</Typography>
                  </Box>
                  <ConfidenceGauge score={comp.champion.confidence_score} label="Confidence" />
                  <TableContainer sx={{ mt: 1.5 }}>
                    <Table size="small">
                      <TableBody>
                        {Object.entries(comp.champion.metrics).map(([k, v]) => (
                          <TableRow key={k}>
                            <TableCell sx={{ border: 0, py: 0.3, pl: 0, fontSize: '0.75rem', textTransform: 'uppercase', color: 'text.secondary' }}>{k}</TableCell>
                            <TableCell sx={{ border: 0, py: 0.3, pr: 0, textAlign: 'right', fontWeight: 600, fontSize: '0.8rem' }}>
                              {typeof v === 'number' && v < 1 ? v.toFixed(3) : v}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              </Grid>

              {/* Diff Column */}
              <Grid size={{ xs: 12, md: 2 }} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <CompareArrows sx={{ fontSize: 36, color: 'text.secondary', mb: 1 }} />
                <Chip
                  label={`${comp.improvement_pct > 0 ? '+' : ''}${comp.improvement_pct}%`}
                  sx={{
                    fontWeight: 800, fontSize: '1rem',
                    bgcolor: comp.challenger_wins ? 'rgba(76,175,80,0.15)' : 'rgba(244,67,54,0.15)',
                    color: comp.challenger_wins ? '#4caf50' : '#f44336',
                  }}
                />
                <Typography variant="caption" color="text.secondary" mt={0.5}>{comp.primary_metric}</Typography>
              </Grid>

              {/* Challenger */}
              <Grid size={{ xs: 12, md: 5 }}>
                <Paper sx={{ p: 2, bgcolor: 'rgba(33,150,243,0.05)', border: '1px solid rgba(33,150,243,0.2)' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <ScienceOutlined sx={{ color: '#2196f3', fontSize: 20 }} />
                    <Typography fontWeight={700} color="#2196f3">Challenger v{comp.challenger.version}</Typography>
                  </Box>
                  <ConfidenceGauge score={comp.challenger.confidence_score} label="Confidence" />
                  <TableContainer sx={{ mt: 1.5 }}>
                    <Table size="small">
                      <TableBody>
                        {Object.entries(comp.challenger.metrics).map(([k, v]) => (
                          <TableRow key={k}>
                            <TableCell sx={{ border: 0, py: 0.3, pl: 0, fontSize: '0.75rem', textTransform: 'uppercase', color: 'text.secondary' }}>{k}</TableCell>
                            <TableCell sx={{ border: 0, py: 0.3, pr: 0, textAlign: 'right', fontWeight: 600, fontSize: '0.8rem' }}>
                              {typeof v === 'number' && v < 1 ? v.toFixed(3) : v}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  {comp.challenger.features_added.length > 0 && (
                    <Box sx={{ mt: 1.5 }}>
                      <Typography variant="caption" color="text.secondary">New Features:</Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                        {comp.challenger.features_added.map(f => (
                          <Chip key={f} label={f} size="small" sx={{ fontSize: '0.6rem', bgcolor: 'rgba(76,175,80,0.1)', color: '#4caf50', height: 20 }} />
                        ))}
                      </Box>
                    </Box>
                  )}
                  {comp.challenger.features_removed.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">Removed:</Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                        {comp.challenger.features_removed.map(f => (
                          <Chip key={f} label={f} size="small" sx={{ fontSize: '0.6rem', bgcolor: 'rgba(244,67,54,0.1)', color: '#f44336', height: 20 }} />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Paper>
              </Grid>
            </Grid>

            {/* Metric Comparison Bars */}
            <Box sx={{ mt: 2.5 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" mb={1} display="block">
                METRIC COMPARISON &nbsp;
                <Chip size="small" label="Champion" sx={{ bgcolor: 'rgba(255,152,0,0.15)', color: '#ff9800', height: 18, fontSize: '0.6rem', mr: 0.5 }} />
                <Chip size="small" label="Challenger" sx={{ bgcolor: 'rgba(33,150,243,0.15)', color: '#2196f3', height: 18, fontSize: '0.6rem' }} />
              </Typography>
              {Object.entries(comp.metric_diffs).map(([metric, diff]) => (
                <MetricBar key={metric} name={metric} champion={diff.champion} challenger={diff.challenger}
                  lowerBetter={lowerBetterMetrics.has(metric)} />
              ))}
            </Box>
          </Paper>
        </motion.div>
      ))}

      {/* Confirm Dialog */}
      <Dialog open={!!dialogModel} onClose={() => setDialogModel(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {dialogAction === 'accept' ? '🏆 Promote Challenger to Champion' : '❌ Reject Challenger'}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" mb={2}>
            {dialogAction === 'accept'
              ? `This will swap the "champion" alias in Unity Catalog and update the serving endpoint to serve the challenger version.`
              : 'The current champion will continue serving. The challenger will remain for future evaluation.'}
          </Typography>
          <TextField fullWidth label="Reason (optional)" value={reason} onChange={e => setReason(e.target.value)}
            multiline rows={2} size="small" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogModel(null)}>Cancel</Button>
          <Button variant="contained" color={dialogAction === 'accept' ? 'success' : 'error'}
            onClick={handlePromote} disabled={!!promoting}>
            {promoting ? <CircularProgress size={20} /> : dialogAction === 'accept' ? 'Promote' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snack.open} autoHideDuration={6000} onClose={() => setSnack({ ...snack, open: false })}>
        <Alert severity={snack.severity} onClose={() => setSnack({ ...snack, open: false })}>{snack.msg}</Alert>
      </Snackbar>
    </Box>
  )
}
