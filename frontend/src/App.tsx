import { useState } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import {
  AppBar, Toolbar, Typography, IconButton, Box, Drawer, List,
  ListItemButton, ListItemIcon, ListItemText, Tooltip,
} from '@mui/material'
import {
  Menu as MenuIcon, Api as ApiIcon,
  Dashboard as DashboardIcon, TrendingUp, AttachMoney,
  Inventory2, Hub, MonitorHeart, CompareArrows,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { AsyncAIProvider } from './contexts/AsyncAIContext'
import AINotificationBadge from './components/AINotificationBadge'
import FloatingAIAssistant from './components/FloatingAIAssistant'
import Dashboard from './pages/Dashboard'
import DemandForecast from './pages/DemandForecast'
import PricingScience from './pages/PricingScience'
import InventoryOptimizer from './pages/InventoryOptimizer'
import ModelRegistry from './pages/ModelRegistry'
import Monitoring from './pages/Monitoring'
import ChampionChallenger from './pages/ChampionChallenger'

const DRAWER_WIDTH = 240
const DRAWER_COLLAPSED = 64

const navItems = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { label: 'Demand Forecast', icon: <TrendingUp />, path: '/demand' },
  { label: 'Pricing Science', icon: <AttachMoney />, path: '/pricing' },
  { label: 'Inventory', icon: <Inventory2 />, path: '/inventory' },
  { label: 'Model Registry', icon: <Hub />, path: '/models' },
  { label: 'Monitoring', icon: <MonitorHeart />, path: '/monitoring' },
  { label: 'Champion/Challenger', icon: <CompareArrows />, path: '/champion' },
]

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()
  const width = drawerOpen ? DRAWER_WIDTH : DRAWER_COLLAPSED

  return (
    <AsyncAIProvider>
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1, bgcolor: '#0D1117', borderBottom: '1px solid rgba(239,209,159,0.08)' }}>
          <Toolbar>
            <IconButton edge="start" color="inherit" onClick={() => setDrawerOpen(!drawerOpen)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 800, letterSpacing: '-0.03em' }}>
              <Box component="span" sx={{ color: 'primary.main' }}>Box</Box>score
            </Typography>
            <AINotificationBadge />
            <Tooltip title="API Docs">
              <IconButton color="inherit" href="/docs" target="_blank" sx={{ ml: 1 }}>
                <ApiIcon />
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        <Drawer
          variant="permanent"
          sx={{
            width,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width,
              transition: 'width 0.25s ease',
              overflowX: 'hidden',
              bgcolor: '#0D1117',
              borderRight: '1px solid rgba(239,209,159,0.08)',
            },
          }}
        >
          <Toolbar />
          <List sx={{ pt: 2 }}>
            {navItems.map((item) => {
              const active = location.pathname === item.path
              return (
                <Tooltip key={item.path} title={drawerOpen ? '' : item.label} placement="right">
                  <ListItemButton
                    onClick={() => navigate(item.path)}
                    sx={{
                      mx: 1, mb: 0.5, borderRadius: 2,
                      bgcolor: active ? 'rgba(253, 90, 30, 0.12)' : 'transparent',
                      '&:hover': { bgcolor: active ? 'rgba(253, 90, 30, 0.18)' : 'rgba(255,255,255,0.04)' },
                      minHeight: 48,
                      justifyContent: drawerOpen ? 'initial' : 'center',
                      px: drawerOpen ? 2 : 1.5,
                    }}
                  >
                    <ListItemIcon sx={{ color: active ? 'primary.main' : 'text.secondary', minWidth: drawerOpen ? 40 : 0, justifyContent: 'center' }}>
                      {item.icon}
                    </ListItemIcon>
                    <AnimatePresence>
                      {drawerOpen && (
                        <motion.div initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }} exit={{ opacity: 0, width: 0 }} transition={{ duration: 0.2 }}>
                          <ListItemText primary={item.label} sx={{ '& .MuiTypography-root': { fontWeight: active ? 600 : 400, color: active ? 'primary.main' : 'text.primary', whiteSpace: 'nowrap' } }} />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </ListItemButton>
                </Tooltip>
              )
            })}
          </List>
        </Drawer>

        <Box component="main" sx={{ flexGrow: 1, p: 3, pt: 0, mt: '64px', minWidth: 0 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/demand" element={<DemandForecast />} />
            <Route path="/pricing" element={<PricingScience />} />
            <Route path="/inventory" element={<InventoryOptimizer />} />
            <Route path="/models" element={<ModelRegistry />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/champion" element={<ChampionChallenger />} />
          </Routes>
        </Box>

        <FloatingAIAssistant />
      </Box>
    </AsyncAIProvider>
  )
}
