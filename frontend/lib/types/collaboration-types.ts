export interface Change {
  id: string
  type: "addition" | "deletion" | "modification"
  content: string
  originalContent?: string
  author: string
  timestamp: Date
  position: { start: number; end: number }
  status: "pending" | "accepted" | "rejected"
}

export interface Comment {
  id: string
  content: string
  author: string
  timestamp: Date
  position: { start: number; end: number }
  resolved: boolean
  replies: CommentReply[]
}

export interface CommentReply {
  id: string
  content: string
  author: string
  timestamp: Date
}

export interface EditorMode {
  type: "editing" | "suggesting"
  showChanges: boolean
  showComments: boolean
}
