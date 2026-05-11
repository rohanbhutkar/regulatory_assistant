"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Sparkles, Save, Plus, Trash2, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface Objective {
  id: string
  type: "primary" | "secondary" | "exploratory"
  description: string
}

interface ObjectivesTabProps {
  trials?: any[]
  referenceInfo?: string
}

export function ObjectivesTab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: ObjectivesTabProps = {}) {
  // Use context data with props as fallback
  const {
    objectives: contextObjectives,
    setObjectives: setContextObjectives,
    selectedTrials,
    studyContext
  } = useStudyDesigner()
  
  // Extract indication and phase from studyContext
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''

  // Use context data if available, otherwise use local state
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials

  // Extract reference info from the actual selected trials, not global context
  // This ensures we generate objectives for the trials that are actually selected
  const referenceInfo = propsReferenceInfo !== undefined
    ? propsReferenceInfo
    : extractReferenceInfoFromTrials(trials, { indication, phase })

  // Local state (only used if not from context)
  const [localObjectives, setLocalObjectives] = useState<Objective[]>([{ id: "1", type: "primary", description: "" }])

  // Use context or local objectives
  const objectives = contextObjectives.length > 0 ? contextObjectives : localObjectives
  const setObjectives = contextObjectives.length > 0 || propsTrials === undefined ? setContextObjectives : setLocalObjectives

  const { generateObjectives, isGenerating, error } = useProtocolGeneration()

  console.log("🔍 Objectives Tab:", {
    contextObjectives: contextObjectives.length,
    localObjectives: localObjectives.length,
    usingCondescription: contextObjectives.length > 0 || propsTrials === undefined,
    indication,
    phase,
    selectedTrials: trials.length
  })

  const handleSave = () => {
    // Explicitly save objectives to context
    setObjectives([...objectives])
    console.log('💾 Saved objectives to context:', {
      primary: objectives.filter(o => o.type === 'primary').length,
      secondary: objectives.filter(o => o.type === 'secondary').length,
      exploratory: objectives.filter(o => o.type === 'exploratory').length
    })
    toast.success('Objectives saved successfully!')
  }

  const handleAIGenerate = async () => {
    console.log("🎬 handleAIGenerate called for objectives")
    
    // Validate we have necessary data
    if (!indication || !phase) {
      console.log("❌ Validation failed: missing indication or phase")
      toast.error('Please fill in Basic Info (indication and phase) before generating objectives')
      return
    }
    
    if (trials.length === 0) {
      console.log("❌ Validation failed: no trials selected")
      toast.error('Please select at least one reference trial before generating objectives')
      return
    }
    
    try {
      console.log("🔍 Objectives Tab - Generating with trials:", {
        trialsCount: trials.length,
        indication,
        phase,
        referenceInfo: referenceInfo ? referenceInfo.substring(0, 100) + '...' : '(empty)',
        firstTrial: trials[0],
        indications: trials.map(t => t.indication || t.Disease).filter(Boolean),
        phases: trials.map(t => t.phase || t.Trial_Phase).filter(Boolean),
        diseases: trials.map(t => t.Disease).filter(Boolean)
      })

      const response = await generateObjectives({
        trials: trials,
        reference_info: referenceInfo
      })

      if (response && response.content) {
        // Parse the content to extract objectives
        // Backend returns structured content like:
        // **Primary Objective(s):**
        // 1. To evaluate...
        // **Secondary Objectives:**
        // 1. To assess...
        // 2. To evaluate...
        
        const content = response.content
        const objectivesArray: Objective[] = []
        
        // Split content into sections
        const lines = content.split('\n').filter(line => line.trim())
        
        let currentType: "primary" | "secondary" | null = null
        
        for (const line of lines) {
          const trimmedLine = line.trim()
          
          // Check for section headers
          if (trimmedLine.match(/^\*\*Primary Objective/i)) {
            currentType = "primary"
            continue
          } else if (trimmedLine.match(/^\*\*Secondary Objective/i)) {
            currentType = "secondary"
            continue
          }
          
          // Parse numbered objectives (e.g., "1. To evaluate...")
          const numberedMatch = trimmedLine.match(/^\d+\.\s+(.+)/)
          if (numberedMatch && currentType) {
            objectivesArray.push({
              id: Date.now().toString() + Math.random(),
              type: currentType,
              description: numberedMatch[1]
            })
            continue
          }
          
          // If it's a non-numbered line after a header and we have a type, treat it as an objective
          if (currentType && trimmedLine.length > 20 && !trimmedLine.startsWith('**')) {
            objectivesArray.push({
              id: Date.now().toString() + Math.random(),
              type: currentType,
              description: trimmedLine
            })
          }
        }
        
        // If no objectives were parsed, try a fallback approach
        if (objectivesArray.length === 0) {
          // Split by double newlines to get paragraphs
          const paragraphs = content.split(/\n\n+/).filter(p => p.trim())
          
          for (let i = 0; i < paragraphs.length && objectivesArray.length < 5; i++) {
            const para = paragraphs[i].trim()
            // Skip headers
            if (para.startsWith('**') && para.endsWith('**')) continue
            
            // Determine type based on content or position
            const type = para.toLowerCase().includes('primary') || i === 0 ? "primary" : "secondary"
            
            objectivesArray.push({
              id: Date.now().toString() + Math.random(),
              type: type,
              description: para.replace(/^\d+\.\s*/, '') // Remove leading numbers
            })
          }
        }
        
        console.log("📋 Parsed objectives:", objectivesArray)
        
        setObjectives(objectivesArray)
        toast.success(`Generated ${objectivesArray.length} study objectives!`)
      } else {
        toast.error('Failed to generate study objectives. Please try again.')
      }
    } catch (err) {
      console.error('Error generating objectives:', err)
      toast.error('Error generating study objectives. Please try again.')
    }
  }

  const addObjective = (type: "primary" | "secondary") => {
    setObjectives([...objectives, { id: Date.now().toString(), type, description: "" }])
  }

  const removeObjective = (id: string) => {
    setObjectives(objectives.filter((obj) => obj.id !== id))
  }

  const updateObjective = (id: string, description: string) => {
    setObjectives(objectives.map((obj) => (obj.id === id ? { ...obj, description } : obj)))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Study Objectives</h2>
          <p className="text-sm text-muted-foreground mt-1">Define primary and secondary objectives</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleAIGenerate} disabled={isGenerating} className="gap-2 bg-primary hover:bg-primary/90">
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
          <Button variant="outline" className="gap-2 bg-transparent" onClick={handleSave}>
            <Save className="h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      <div className="space-y-6 max-w-4xl">
        {/* Primary Objectives */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-lg font-semibold">Primary Objectives</Label>
            <Button variant="outline" size="sm" onClick={() => addObjective("primary")} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Primary
            </Button>
          </div>
          {objectives
            .filter((obj) => obj.type === "primary")
            .map((objective, index) => (
              <div key={objective.id} className="flex gap-3">
                <div className="flex-1 space-y-2">
                  <Label className="text-sm text-muted-foreground">Primary Objective {index + 1}</Label>
                  <Textarea
                    placeholder="Enter primary objective..."
                    value={objective.description}
                    onChange={(e) => updateObjective(objective.id, e.target.value)}
                    className="bg-card border-border/50 min-h-[100px]"
                  />
                </div>
                {objectives.filter((o) => o.type === "primary").length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeObjective(objective.id)}
                    className="mt-7 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
        </div>

        {/* Secondary Objectives */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-lg font-semibold">Secondary Objectives</Label>
            <Button variant="outline" size="sm" onClick={() => addObjective("secondary")} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Secondary
            </Button>
          </div>
          {objectives
            .filter((obj) => obj.type === "secondary")
            .map((objective, index) => (
              <div key={objective.id} className="flex gap-3">
                <div className="flex-1 space-y-2">
                  <Label className="text-sm text-muted-foreground">Secondary Objective {index + 1}</Label>
                  <Textarea
                    placeholder="Enter secondary objective..."
                    value={objective.description}
                    onChange={(e) => updateObjective(objective.id, e.target.value)}
                    className="bg-card border-border/50 min-h-[100px]"
                  />
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeObjective(objective.id)}
                  className="mt-7 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
