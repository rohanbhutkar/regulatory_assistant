"use client"

import { Operation, OperationType } from '../contexts/activity-context'

interface ActivityEvent {
  type: 'activity_event'
  event_type: string
  operation_id: string
  operation_type: string
  context: {
    asset_id?: string
    study_id?: string
    tab?: string
  }
  step: string
  progress: number
  message: string
  timestamp: string
  metadata: Record<string, any>
  operation?: {
    id: string
    type: string
    status: string
    progress: number
    current_step: string
    steps: any[]
    start_time: string
    end_time?: string
    duration?: number
  }
}

function getActivityWsUrl(clientId: string): string {
  const explicit = process.env.NEXT_PUBLIC_AGENT_WS_URL?.trim()
  if (explicit) {
    const root = explicit.replace(/\/$/, "")
    return `${root}/${clientId}`
  }
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001"
  const wsUrl = apiUrl.replace("http://", "ws://").replace("https://", "wss://").replace(/\/$/, "")
  return `${wsUrl}/ws/${clientId}`
}

export class ActivityWebSocketClient {
  private ws: WebSocket | null = null
  private clientId: string
  private reconnectAttempts = 0
  private reconnectDelayMs = 800
  private maxReconnectDelayMs = 30_000
  private eventHandlers: Map<string, Set<(event: ActivityEvent) => void>> = new Map()
  private isConnecting = false
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private lastOnEvent: ((event: ActivityEvent) => void) | null = null
  private allowReconnect = true

  constructor(clientId?: string) {
    this.clientId = clientId || `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  connect(onEvent: (event: ActivityEvent) => void) {
    this.allowReconnect = true
    this.lastOnEvent = onEvent
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true
    const wsUrl = getActivityWsUrl(this.clientId)

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.isConnecting = false
        this.reconnectAttempts = 0
        if (this.pingTimer) clearInterval(this.pingTimer)
        this.pingTimer = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 25_000)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'pong') return

          // Handle activity events
          if (data.type === 'activity_event') {
            const activityEvent = data as ActivityEvent
            onEvent(activityEvent)

            // Also call registered handlers
            const handlers = this.eventHandlers.get('activity_event')
            if (handlers) {
              handlers.forEach(handler => handler(activityEvent))
            }
          }
        } catch {
          /* ignore malformed frames */
        }
      }

      this.ws.onerror = () => {
        this.isConnecting = false
      }

      this.ws.onclose = () => {
        this.isConnecting = false
        if (this.pingTimer) {
          clearInterval(this.pingTimer)
          this.pingTimer = null
        }
        this.ws = null

        if (!this.allowReconnect || !this.lastOnEvent) return

        this.reconnectAttempts++
        const delay = Math.min(
          this.maxReconnectDelayMs,
          Math.round(this.reconnectDelayMs * Math.pow(1.6, Math.min(this.reconnectAttempts - 1, 14))),
        )
        setTimeout(() => {
          if (!this.allowReconnect || !this.lastOnEvent) return
          this.connect(this.lastOnEvent)
        }, delay)
      }
    } catch {
      this.isConnecting = false
    }
  }

  disconnect() {
    this.allowReconnect = false
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  subscribe(eventType: string, handler: (event: ActivityEvent) => void) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set())
    }
    this.eventHandlers.get(eventType)!.add(handler)
  }

  unsubscribe(eventType: string, handler: (event: ActivityEvent) => void) {
    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Singleton instance
let activityWebSocketClient: ActivityWebSocketClient | null = null

export function getActivityWebSocketClient(): ActivityWebSocketClient {
  if (!activityWebSocketClient) {
    activityWebSocketClient = new ActivityWebSocketClient()
  }
  return activityWebSocketClient
}
