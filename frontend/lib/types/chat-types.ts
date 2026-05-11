export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  agentName?: string
  agentType?: string
  metadata?: {
    references?: Reference[]
    progress?: ProgressUpdate
    attachments?: Attachment[]
    // Allow additional properties for agent actions
    action?: string
    criteria?: string
    isRefinement?: boolean
    /** Structured citations from synthesis (text + optional url) */
    citations?: Array<{ text: string; url?: string }>
    [key: string]: unknown
  }
}

export interface Reference {
  id: string
  title: string
  source: string
  url?: string
  snippet?: string
}

export interface ProgressUpdate {
  currentStep: number
  totalSteps: number
  stepName: string
  status: "pending" | "in-progress" | "completed" | "error"
}

export interface Attachment {
  id: string
  name: string
  type: string
  size: number
  url: string
}

export interface Agent {
  id: string
  name: string
  description: string
  type: string
  capabilities: string[]
  status: "available" | "busy" | "offline"
}

export interface ChatSession {
  id: string
  personaId: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}
