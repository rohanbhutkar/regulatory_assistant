"use client"

import { useState, useRef } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Sparkles, Save, FileDown, Loader2, MessageSquare, Check, X, Eye, EyeOff, Edit3, FileEdit } from "lucide-react"
import type { Change, Comment, EditorMode } from "@/lib/types/collaboration-types"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { toast } from "sonner"

interface CollaborativeEditorProps {
  title: string
  content: string
  onContentChange: (content: string) => void
  changes?: Change[]
  comments?: Comment[]
  onChangesUpdate?: (changes: Change[]) => void
  onCommentsUpdate?: (comments: Comment[]) => void
  trials?: any[]
  referenceInfo?: string
}

export function CollaborativeEditor({
  title,
  content,
  onContentChange,
  changes = [],
  comments = [],
  onChangesUpdate,
  onCommentsUpdate,
  trials = [],
  referenceInfo = '',
}: CollaborativeEditorProps) {
  const [localContent, setLocalContent] = useState(content)
  const [mode, setMode] = useState<EditorMode>({
    type: "editing",
    showChanges: true,
    showComments: true,
  })
  const [selectedText, setSelectedText] = useState<{ start: number; end: number } | null>(null)
  const [newComment, setNewComment] = useState("")
  const [showCommentInput, setShowCommentInput] = useState(false)
  const editorRef = useRef<HTMLTextAreaElement>(null)

  const { generateProtocolSection, isGenerating, error } = useProtocolGeneration()

  const handleGenerate = async () => {
    try {
      // Determine section type based on title
      let sectionType = 'introduction'
      if (title.toLowerCase().includes('rationale')) sectionType = 'rationale'
      else if (title.toLowerCase().includes('objective')) sectionType = 'primary_objectives'
      else if (title.toLowerCase().includes('endpoint')) sectionType = 'primary_endpoints'
      else if (title.toLowerCase().includes('eligibility') || title.toLowerCase().includes('criteria')) sectionType = 'inclusion_criteria'
      else if (title.toLowerCase().includes('schedule') || title.toLowerCase().includes('activities')) sectionType = 'schedule_of_activities'
      else if (title.toLowerCase().includes('design')) sectionType = 'study_design'
      else if (title.toLowerCase().includes('schema')) sectionType = 'schema'

      const response = await generateProtocolSection({
        section_type: sectionType,
        trials: trials,
        reference_info: referenceInfo
      })

      if (response && response.content) {
        setLocalContent(response.content)
        onContentChange(response.content)
        toast.success(`Generated ${title} successfully!`)
      } else {
        toast.error('Failed to generate content. Please try again.')
      }
    } catch (err) {
      console.error('Error generating protocol section:', err)
      toast.error('Error generating content. Please check your connection.')
    }
  }

  const handleSave = () => {
    onContentChange(localContent)
  }

  const handleTextSelection = () => {
    if (editorRef.current) {
      const start = editorRef.current.selectionStart
      const end = editorRef.current.selectionEnd
      if (start !== end) {
        setSelectedText({ start, end })
      }
    }
  }

  const addComment = () => {
    if (!selectedText || !newComment.trim()) return

    const comment: Comment = {
      id: `comment-${Date.now()}`,
      content: newComment,
      author: "Current User",
      timestamp: new Date(),
      position: selectedText,
      resolved: false,
      replies: [],
    }

    onCommentsUpdate?.([...comments, comment])
    setNewComment("")
    setShowCommentInput(false)
    setSelectedText(null)
  }

  const acceptChange = (changeId: string) => {
    const updatedChanges = changes.map((change) =>
      change.id === changeId ? { ...change, status: "accepted" as const } : change,
    )
    onChangesUpdate?.(updatedChanges)
  }

  const rejectChange = (changeId: string) => {
    const updatedChanges = changes.map((change) =>
      change.id === changeId ? { ...change, status: "rejected" as const } : change,
    )
    onChangesUpdate?.(updatedChanges)
  }

  const resolveComment = (commentId: string) => {
    const updatedComments = comments.map((comment) =>
      comment.id === commentId ? { ...comment, resolved: true } : comment,
    )
    onCommentsUpdate?.(updatedComments)
  }

  const pendingChanges = changes.filter((c) => c.status === "pending")
  const activeComments = comments.filter((c) => !c.resolved)

  return (
    <div className="flex gap-4 h-full">
      {/* Main Editor */}
      <Card className="flex-1 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-foreground">{title}</h2>
          <div className="flex gap-2">
            <Button
              variant={mode.type === "editing" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode({ ...mode, type: "editing" })}
              className="gap-2"
            >
              <Edit3 className="h-4 w-4" />
              Editing
            </Button>
            <Button
              variant={mode.type === "suggesting" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode({ ...mode, type: "suggesting" })}
              className="gap-2"
            >
              <FileEdit className="h-4 w-4" />
              Suggesting
            </Button>
            <div className="w-px bg-border mx-2" />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMode({ ...mode, showChanges: !mode.showChanges })}
              className="gap-2"
            >
              {mode.showChanges ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              Changes
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMode({ ...mode, showComments: !mode.showComments })}
              className="gap-2"
            >
              <MessageSquare className="h-4 w-4" />
              Comments ({activeComments.length})
            </Button>
          </div>
        </div>

        <div className="flex gap-2 mb-4">
          <Button onClick={handleGenerate} disabled={isGenerating} className="gap-2 bg-primary hover:bg-primary/90">
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate with AI
              </>
            )}
          </Button>
          <Button onClick={handleSave} variant="outline" className="gap-2 bg-transparent">
            <Save className="h-4 w-4" />
            Save
          </Button>
          <Button variant="outline" className="gap-2 bg-transparent">
            <FileDown className="h-4 w-4" />
            Export
          </Button>
          {selectedText && (
            <Button variant="outline" size="sm" onClick={() => setShowCommentInput(true)} className="gap-2 ml-auto">
              <MessageSquare className="h-4 w-4" />
              Add Comment
            </Button>
          )}
        </div>

        {showCommentInput && selectedText && (
          <Card className="p-4 mb-4 bg-secondary/30">
            <div className="space-y-2">
              <Input
                placeholder="Add a comment..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    addComment()
                  }
                }}
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={addComment}>
                  Add Comment
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowCommentInput(false)
                    setNewComment("")
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        )}

        <div className="space-y-4">
          <Textarea
            ref={editorRef}
            value={localContent}
            onChange={(e) => setLocalContent(e.target.value)}
            onSelect={handleTextSelection}
            placeholder={`Enter ${title.toLowerCase()} content here... You can also use AI to generate this section.`}
            className="min-h-[500px] font-mono text-sm"
          />

          <div className="text-xs text-muted-foreground">
            Tip: Select text to add comments. Use {mode.type === "editing" ? "Suggesting" : "Editing"} mode to track
            changes.
          </div>
        </div>
      </Card>

      {/* Sidebar for Changes and Comments */}
      <div className="w-80 space-y-4">
        {/* Pending Changes */}
        {mode.showChanges && pendingChanges.length > 0 && (
          <Card className="p-4">
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <FileEdit className="h-4 w-4" />
              Pending Changes ({pendingChanges.length})
            </h3>
            <div className="space-y-3">
              {pendingChanges.map((change) => (
                <div key={change.id} className="border border-border/50 rounded-lg p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <Badge
                      variant="outline"
                      className={
                        change.type === "addition"
                          ? "border-success text-success"
                          : change.type === "deletion"
                            ? "border-error text-error"
                            : "border-warning text-warning"
                      }
                    >
                      {change.type}
                    </Badge>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-success hover:text-success"
                        onClick={() => acceptChange(change.id)}
                      >
                        <Check className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-error hover:text-error"
                        onClick={() => rejectChange(change.id)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  <div className="text-sm">
                    {change.type === "deletion" && change.originalContent && (
                      <div className="line-through text-error/70">{change.originalContent}</div>
                    )}
                    {change.type === "addition" && <div className="text-success">{change.content}</div>}
                    {change.type === "modification" && (
                      <>
                        <div className="line-through text-error/70 text-xs">{change.originalContent}</div>
                        <div className="text-success text-xs mt-1">{change.content}</div>
                      </>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {change.author} • {change.timestamp.toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Active Comments */}
        {mode.showComments && activeComments.length > 0 && (
          <Card className="p-4">
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Comments ({activeComments.length})
            </h3>
            <div className="space-y-3">
              {activeComments.map((comment) => (
                <div key={comment.id} className="border border-border/50 rounded-lg p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm font-medium text-foreground">{comment.author}</div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      onClick={() => resolveComment(comment.id)}
                    >
                      <Check className="h-3 w-3" />
                    </Button>
                  </div>
                  <div className="text-sm text-muted-foreground">{comment.content}</div>
                  <div className="text-xs text-muted-foreground">{comment.timestamp.toLocaleDateString()}</div>
                  {comment.replies.length > 0 && (
                    <div className="pl-3 border-l-2 border-border/50 space-y-2 mt-2">
                      {comment.replies.map((reply) => (
                        <div key={reply.id} className="text-sm">
                          <div className="font-medium text-foreground">{reply.author}</div>
                          <div className="text-muted-foreground">{reply.content}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Empty State */}
        {mode.showChanges && pendingChanges.length === 0 && mode.showComments && activeComments.length === 0 && (
          <Card className="p-6 text-center">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No pending changes or comments</p>
          </Card>
        )}
      </div>
    </div>
  )
}
