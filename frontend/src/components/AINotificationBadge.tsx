import { useState } from 'react'
import { Badge, IconButton, Popover, List, ListItem, ListItemText, Typography, Box, Chip } from '@mui/material'
import { AutoAwesome } from '@mui/icons-material'
import { useAsyncAI } from '../contexts/AsyncAIContext'

export default function AINotificationBadge() {
  const { pendingRequests, readyRequests, totalUnseen, markSeen } = useAsyncAI()
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null)

  const allRequests = [
    ...pendingRequests.map((r) => ({ ...r, seen: false })),
    ...readyRequests.filter((r) => !r.seen),
  ]

  return (
    <>
      <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ color: 'text.secondary' }}>
        <Badge badgeContent={totalUnseen} color={pendingRequests.length > 0 ? 'warning' : 'success'} max={99}>
          <AutoAwesome fontSize="small" />
        </Badge>
      </IconButton>
      <Popover
        open={Boolean(anchorEl)} anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{ sx: { width: 320, bgcolor: 'background.paper', border: '1px solid rgba(239,209,159,0.1)', borderRadius: 2, mt: 1 } }}
      >
        <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>AI Requests</Typography>
        </Box>
        {allRequests.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">No pending requests</Typography>
          </Box>
        ) : (
          <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
            {allRequests.map((req) => (
              <ListItem
                key={req.id}
                onClick={() => req.status === 'completed' && markSeen(req.id)}
                sx={{ cursor: req.status === 'completed' ? 'pointer' : 'default', '&:hover': { bgcolor: 'rgba(255,255,255,0.03)' } }}
              >
                <ListItemText
                  primary={req.title}
                  secondary={req.status}
                  primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                />
                <Chip
                  label={req.status}
                  size="small"
                  color={req.status === 'completed' ? 'success' : req.status === 'failed' ? 'error' : 'warning'}
                  sx={{ fontSize: '0.65rem', height: 20 }}
                />
              </ListItem>
            ))}
          </List>
        )}
      </Popover>
    </>
  )
}
