import { useState } from 'react'
import {
  Box, Fab, Dialog, DialogTitle, DialogContent, IconButton,
  Typography, TextField, List, ListItem, Chip, Paper,
} from '@mui/material'
import { AutoAwesome, Close, Send } from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const SAMPLE_QUESTIONS = [
  "What's the demand forecast for the Dodgers game?",
  "Which sections need price adjustments?",
  "Show revenue for next 10 home games",
  "What is the price elasticity for Club Level?",
]

const MOCK_RESPONSES: Record<string, string> = {
  default: "Based on our latest model predictions, here's what I found:\n\n**Demand Index**: 8.2/10 (High)\n**Recommended Action**: Consider increasing prices in Field Club by 8-12% for this matchup.\n\nThe model shows strong confidence (92%) in these predictions based on historical data patterns.",
  dodgers: "**Dodgers @ Giants — Sep 28, 2026**\n\nDemand forecast: **38,200** (93% capacity)\n- Primary demand index: 9.1/10\n- Secondary market premium: +42%\n- Page views trending 2.3x above average\n\n**Recommendation**: This is a premium matchup. Field Club and Club Level should be at tier-1 pricing. Consider releasing masked inventory in View Level.",
  price: "**Sections Flagged for Price Adjustment:**\n\n| Section | Current | Recommended | Change |\n|---------|---------|-------------|--------|\n| Field Club | $285 | $310 | +8.8% |\n| Club 1B | $145 | $155 | +6.9% |\n| Bleachers | $42 | $38 | -9.5% |\n| View RF | $68 | $72 | +5.9% |\n\nBleachers are showing low sell-through (60%) — a price reduction could drive volume.",
}

export default function FloatingAIAssistant() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')

  function handleSend() {
    if (!input.trim()) return
    const userMsg = input.trim()
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setInput('')

    setTimeout(() => {
      let response = MOCK_RESPONSES.default
      if (userMsg.toLowerCase().includes('dodger')) response = MOCK_RESPONSES.dodgers
      else if (userMsg.toLowerCase().includes('price') || userMsg.toLowerCase().includes('section')) response = MOCK_RESPONSES.price
      setMessages((prev) => [...prev, { role: 'assistant', content: response }])
    }, 800)
  }

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1300 }}
          >
            <Fab
              onClick={() => setOpen(true)}
              sx={{
                width: 56, height: 56,
                background: 'linear-gradient(135deg, #FD5A1E 0%, #FF8A50 100%)',
                boxShadow: '0 4px 20px rgba(253,90,30,0.4)',
                '&:hover': { boxShadow: '0 6px 25px rgba(253,90,30,0.5)' },
              }}
            >
              <AutoAwesome sx={{ fontSize: 28, color: 'white' }} />
            </Fab>
          </motion.div>
        )}
      </AnimatePresence>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth
        PaperProps={{ sx: { borderRadius: 3, bgcolor: 'background.default', maxHeight: '80vh', height: '80vh' } }}
      >
        <DialogTitle sx={{ background: 'linear-gradient(135deg, #FD5A1E 0%, #C43E00 100%)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AutoAwesome />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>Boxscore AI</Typography>
          </Box>
          <IconButton onClick={() => setOpen(false)} sx={{ color: 'white' }}><Close /></IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            {messages.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <AutoAwesome sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" sx={{ mb: 1 }}>Ask anything about your ticket data</Typography>
                <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>I can query demand forecasts, pricing recommendations, and inventory status.</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
                  {SAMPLE_QUESTIONS.map((q) => (
                    <Chip key={q} label={q} variant="outlined" size="small"
                      onClick={() => { setInput(q) }}
                      sx={{ borderColor: 'rgba(253,90,30,0.3)', color: 'text.secondary', cursor: 'pointer', '&:hover': { borderColor: 'primary.main', color: 'primary.main' } }}
                    />
                  ))}
                </Box>
              </Box>
            )}
            <List disablePadding>
              {messages.map((msg, i) => (
                <ListItem key={i} sx={{ px: 0, mb: 1, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  <Paper sx={{
                    p: 1.5, maxWidth: '85%', borderRadius: 2,
                    bgcolor: msg.role === 'user' ? 'rgba(253,90,30,0.15)' : 'background.paper',
                    border: `1px solid ${msg.role === 'user' ? 'rgba(253,90,30,0.3)' : 'rgba(239,209,159,0.08)'}`,
                  }}>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{msg.content}</Typography>
                  </Paper>
                </ListItem>
              ))}
            </List>
          </Box>
          <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', gap: 1 }}>
            <TextField
              fullWidth size="small" placeholder="Ask about demand, pricing, inventory..."
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2, bgcolor: 'background.paper' } }}
            />
            <IconButton onClick={handleSend} color="primary" sx={{ bgcolor: 'rgba(253,90,30,0.15)' }}>
              <Send />
            </IconButton>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}
