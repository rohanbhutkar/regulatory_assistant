"use client"

import { useEffect, useRef, useState } from "react"
import { WebSocketClient } from "@/lib/api/websocket"

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const wsClient = useRef<WebSocketClient | null>(null)

  useEffect(() => {
    wsClient.current = new WebSocketClient(url)

    wsClient.current.connect(
      (data) => {
        setLastMessage(data)
        setIsConnected(true)
      },
      (error) => {
        console.error("[v0] WebSocket error:", error)
        setIsConnected(false)
      },
    )

    return () => {
      wsClient.current?.disconnect()
    }
  }, [url])

  const sendMessage = (data: any) => {
    wsClient.current?.send(data)
  }

  return { isConnected, lastMessage, sendMessage }
}
