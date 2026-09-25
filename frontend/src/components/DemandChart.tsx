import { Box, Typography } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart } from 'recharts'

interface DataPoint {
  date: string
  actual?: number
  predicted: number
  lower?: number
  upper?: number
}

interface DemandChartProps {
  data: DataPoint[]
  title: string
  showConfidence?: boolean
}

export default function DemandChart({ data, title, showConfidence = false }: DemandChartProps) {
  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>{title}</Typography>
      <ResponsiveContainer width="100%" height={320}>
        {showConfidence ? (
          <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="date" stroke="#A0A0B8" fontSize={11} />
            <YAxis stroke="#A0A0B8" fontSize={11} />
            <Tooltip
              contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }}
              labelStyle={{ color: '#EFD19F', fontWeight: 600 }}
            />
            <Area type="monotone" dataKey="upper" stroke="none" fill="rgba(253,90,30,0.1)" />
            <Area type="monotone" dataKey="lower" stroke="none" fill="#16213E" />
            <Line type="monotone" dataKey="actual" stroke="#4CAF50" strokeWidth={2} dot={{ r: 3 }} name="Actual" />
            <Line type="monotone" dataKey="predicted" stroke="#FD5A1E" strokeWidth={2} strokeDasharray="6 3" dot={false} name="Predicted" />
          </ComposedChart>
        ) : (
          <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="date" stroke="#A0A0B8" fontSize={11} />
            <YAxis stroke="#A0A0B8" fontSize={11} />
            <Tooltip contentStyle={{ backgroundColor: '#16213E', border: '1px solid rgba(239,209,159,0.2)', borderRadius: 8 }} labelStyle={{ color: '#EFD19F' }} />
            <Line type="monotone" dataKey="actual" stroke="#4CAF50" strokeWidth={2} dot={{ r: 3 }} name="Actual" />
            <Line type="monotone" dataKey="predicted" stroke="#FD5A1E" strokeWidth={2} strokeDasharray="6 3" dot={false} name="Predicted" />
          </LineChart>
        )}
      </ResponsiveContainer>
    </Box>
  )
}
