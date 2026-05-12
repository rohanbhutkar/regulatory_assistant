"use client"

import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatTime } from '@/lib/utils/time'
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  ThumbsUp, 
  ThumbsDown,
  MoreVertical,
  Trash2,
  Edit3,
  Check,
  X
} from 'lucide-react'
import toast from 'react-hot-toast'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  type?: 'text' | 'image' | 'file'
  metadata?: {
    fileName?: string
    fileSize?: string
    imageUrl?: string
  }
}

interface ChatInterfaceProps {
  className?: string
  onSendMessage?: (message: string) => Promise<string>
  initialMessages?: Message[]
  placeholder?: string
  title?: string
}

export function ChatInterface({ 
  className, 
  onSendMessage,
  initialMessages = [],
  placeholder = "Ask me anything about clinical research...",
  title = "Clinical Knowledge Assistant"
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [editingMessage, setEditingMessage] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      role: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      let response = ''
      if (onSendMessage) {
        response = await onSendMessage(input.trim())
      } else {
        // Try WebSocket connection first
        try {
          const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8001/ws"
          const clientId = `client-${Date.now()}`
          const ws = new WebSocket(`${wsUrl}/${clientId}`)
          
          const wsPromise = new Promise<string>((resolve, reject) => {
            const timeout = setTimeout(() => {
              ws.close()
              reject(new Error("WebSocket timeout"))
            }, 5000)
            
            ws.onopen = () => {
              const queryMessage = {
                type: "query",
                data: {
                  query: input.trim(),
                  conversation_history: messages.slice(-3).map(msg => ({
                    role: msg.role,
                    content: msg.content,
                    timestamp: msg.timestamp
                  }))
                }
              }
              ws.send(JSON.stringify(queryMessage))
            }
            
            ws.onmessage = (event) => {
              try {
                const data = JSON.parse(event.data)
                if (data.type === "query_completed") {
                  clearTimeout(timeout)
                  ws.close()
                  const synthesis = data.data?.synthesis
                  resolve(synthesis?.answer || "I've processed your query.")
                } else if (data.type === "error") {
                  clearTimeout(timeout)
                  ws.close()
                  reject(new Error(data.message || "WebSocket error"))
                }
              } catch (error) {
                clearTimeout(timeout)
                ws.close()
                reject(error)
              }
            }
            
            ws.onerror = () => {
              clearTimeout(timeout)
              ws.close()
              reject(new Error("WebSocket connection failed"))
            }
          })
          
          response = await wsPromise
        } catch {
          // Fall through to HTTP API below
          const apiResponse = await fetch('http://localhost:8001/api/data/trialtrove', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: input.trim(),
              limit: 5
            })
          })
          
          if (apiResponse.ok) {
            const data = await apiResponse.json()
            if (data.trials && data.trials.length > 0) {
              response = `I found ${data.total_count} trials related to "${input.trim()}". Here are some examples:\n\n`
              data.trials.slice(0, 3).forEach((trial: { trial_name?: string; phase?: string; therapeutic_area?: string; status?: string }, index: number) => {
                response += `${index + 1}. ${trial.trial_name || 'Unnamed Trial'}\n`
                response += `   Phase: ${trial.phase || 'Unknown'}\n`
                response += `   Therapeutic Area: ${trial.therapeutic_area || 'Unknown'}\n`
                response += `   Status: ${trial.status || 'Unknown'}\n\n`
              })
              response += `Would you like me to search for more specific information about any of these trials?`
            } else {
              response = `I searched our database of 80,249 clinical trials but didn't find specific matches for "${input.trim()}". Try asking about:\n\n• Specific therapeutic areas (Oncology, Cardiology, Neurology)\n• Trial phases (Phase I, Phase II, Phase III)\n• Drug names or indications\n• Trial status or sponsors\n\nWhat would you like to know more about?`
            }
          } else {
            response = `I understand you're asking about "${input.trim()}". This is a demo response. In a real implementation, this would connect to your clinical knowledge AI system with access to 80,249 trials and 40,777 research sites.`
          }
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        role: 'assistant',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch {
      toast.error("Failed to send message")
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I encountered an error while searching our database. Please try again or ask about:\n\n• Clinical trial information\n• Research site data\n• Therapeutic areas\n• Trial phases\n\nOur database contains 80,249 trials and 40,777 research sites.`,
        role: 'assistant',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const deleteMessage = (messageId: string) => {
    setMessages(prev => prev.filter(msg => msg.id !== messageId))
    toast.success('Message deleted')
  }

  const startEdit = (message: Message) => {
    setEditingMessage(message.id)
    setEditContent(message.content)
  }

  const saveEdit = () => {
    if (!editingMessage) return
    
    setMessages(prev => prev.map(msg => 
      msg.id === editingMessage 
        ? { ...msg, content: editContent }
        : msg
    ))
    setEditingMessage(null)
    setEditContent('')
    toast.success('Message updated')
  }

  const cancelEdit = () => {
    setEditingMessage(null)
    setEditContent('')
  }

  return (
    <div className={cn("flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm", className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">{title}</h2>
            <p className="text-sm text-gray-500">AI-powered clinical research assistant</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="ghost" size="icon">
            <MoreVertical className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Welcome to Clinical Knowledge Assistant</h3>
            <p className="text-gray-500 max-w-md">
              Ask me anything about clinical research, trial design, regulatory requirements, or data analysis.
              I have access to 80,249 trials and 40,777 research sites.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex items-start space-x-3",
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}
              
              <div className={cn(
                "max-w-[70%] rounded-lg px-4 py-2",
                message.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-900'
              )}>
                {editingMessage === message.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded resize-none"
                      rows={3}
                    />
                    <div className="flex space-x-2">
                      <Button size="sm" onClick={saveEdit}>
                        <Check className="w-4 h-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={cancelEdit}>
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    {message.role === 'assistant' && (
                      <p className="mt-2 pt-2 border-t border-gray-200 text-[11px] leading-snug text-gray-500">
                        This is a proof-of-concept response from a Lotor Lab agent
                      </p>
                    )}
                    <div className={cn(
                      "text-xs mt-1 flex items-center justify-between",
                      message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                    )}>
                      <span>{formatTime(message.timestamp)}</span>
                      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {message.role === 'user' && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="w-6 h-6"
                              onClick={() => startEdit(message)}
                            >
                              <Edit3 className="w-3 h-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="w-6 h-6"
                              onClick={() => deleteMessage(message.id)}
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </>
                        )}
                        {message.role === 'assistant' && (
                          <div className="flex space-x-1">
                            <Button variant="ghost" size="icon" className="w-6 h-6">
                              <ThumbsUp className="w-3 h-3" />
                            </Button>
                            <Button variant="ghost" size="icon" className="w-6 h-6">
                              <ThumbsDown className="w-3 h-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-white" />
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-gray-600">Searching database...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-end space-x-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholder}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={1}
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>Press Enter to send, Shift+Enter for new line</span>
          <span>{input.length}/2000</span>
        </div>
      </div>
    </div>
  )
}

// Demo component with sample data
export function ClinicalChatDemo() {
  const sampleMessages: Message[] = [
    {
      id: '1',
      content: 'Welcome! I can help you with clinical research questions, trial design, regulatory requirements, and data analysis. I have access to 80,249 clinical trials and 40,777 research sites. What would you like to know?',
      role: 'assistant',
      timestamp: new Date(Date.now() - 60000)
    },
    {
      id: '2',
      content: 'What oncology trials are currently active?',
      role: 'user',
      timestamp: new Date(Date.now() - 30000)
    },
    {
      id: '3',
      content: 'I found several active oncology trials in our database. Here are some examples:\n\n1. Phase III Breast Cancer Study\n   Phase: Phase III\n   Therapeutic Area: Oncology\n   Status: Active\n\n2. Lung Cancer Immunotherapy Trial\n   Phase: Phase II\n   Therapeutic Area: Oncology\n   Status: Active\n\n3. Pediatric Oncology Study\n   Phase: Phase I\n   Therapeutic Area: Oncology\n   Status: Active\n\nWould you like me to search for more specific information about any of these trials?',
      role: 'assistant',
      timestamp: new Date(Date.now() - 15000)
    }
  ]

  return (
    <div className="h-[600px]">
      <ChatInterface
        initialMessages={sampleMessages}
        placeholder="Ask me anything..."
        title="Clinical Research Assistant"
      />
    </div>
  )
}











