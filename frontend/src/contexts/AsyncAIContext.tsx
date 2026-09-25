import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'

interface AIRequest {
  id: string
  type: string
  title: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  result?: unknown
  seen: boolean
}

interface AsyncAIContextType {
  pendingRequests: AIRequest[]
  readyRequests: AIRequest[]
  totalUnseen: number
  submitRequest: (type: string, title: string, payload: Record<string, unknown>) => Promise<string>
  getResult: (requestId: string) => Promise<unknown>
  markSeen: (requestId: string) => void
  isPolling: boolean
}

const AsyncAIContext = createContext<AsyncAIContextType | null>(null)

export function useAsyncAI() {
  const ctx = useContext(AsyncAIContext)
  if (!ctx) throw new Error('useAsyncAI must be used within AsyncAIProvider')
  return ctx
}

export function AsyncAIProvider({ children }: { children: React.ReactNode }) {
  const [pendingRequests, setPendingRequests] = useState<AIRequest[]>([])
  const [readyRequests, setReadyRequests] = useState<AIRequest[]>([])
  const [isPolling, setIsPolling] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const totalUnseen = pendingRequests.length + readyRequests.filter((r) => !r.seen).length

  const pollForUpdates = useCallback(async () => {
    try {
      const response = await fetch('/api/ai/async/pending')
      if (!response.ok) return
      const data = await response.json()
      if (data.status === 'success') {
        setPendingRequests(data.data.pending || [])
        const newReady: AIRequest[] = data.data.ready || []
        setReadyRequests((prev) => {
          const ids = new Set(prev.map((r) => r.id))
          return [...prev, ...newReady.filter((r) => !ids.has(r.id))]
        })
      }
    } catch {
      // backend not available
    }
  }, [])

  useEffect(() => {
    const hasPending = pendingRequests.length > 0
    setIsPolling(hasPending)
    if (intervalRef.current) clearInterval(intervalRef.current)
    intervalRef.current = setInterval(pollForUpdates, hasPending ? 2000 : 30000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [pendingRequests.length, pollForUpdates])

  useEffect(() => { pollForUpdates() }, [pollForUpdates])

  const submitRequest = useCallback(async (type: string, title: string, payload: Record<string, unknown>) => {
    const response = await fetch('/api/ai/async/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_type: type, title, payload }),
    })
    const data = await response.json()
    if (data.status === 'success') {
      pollForUpdates()
      return data.data.request_id as string
    }
    throw new Error(data.message || 'Failed to submit')
  }, [pollForUpdates])

  const getResult = useCallback(async (requestId: string) => {
    const response = await fetch(`/api/ai/async/result/${requestId}`)
    const data = await response.json()
    if (data.status === 'success') return data.data.result
    return null
  }, [])

  const markSeen = useCallback((requestId: string) => {
    setReadyRequests((prev) => prev.map((r) => r.id === requestId ? { ...r, seen: true } : r))
  }, [])

  return (
    <AsyncAIContext.Provider value={{ pendingRequests, readyRequests, totalUnseen, submitRequest, getResult, markSeen, isPolling }}>
      {children}
    </AsyncAIContext.Provider>
  )
}
