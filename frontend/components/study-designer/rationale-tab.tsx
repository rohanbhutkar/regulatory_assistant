"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Sparkles, Save, Plus, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface RationaleTabProps {
  trials?: any[]
  referenceInfo?: string
}

export function RationaleTab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: RationaleTabProps = {}) {
  // Use context data with props as fallback
  const {
    protocolSections,
    updateProtocolSection,
    selectedTrials,
    studyContext
  } = useStudyDesigner()
  
  // Extract indication and phase from studyContext
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''
  
  // Use context data if available, otherwise use props
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials
  
  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined 
    ? propsReferenceInfo 
    : extractReferenceInfoFromTrials(trials, { indication, phase })
  
  // Get protocol rationale section from context (protocolSections is a Record<string, string>)
  const rationaleContent = protocolSections?.rationale || ""
  
  const [content, setContent] = useState(rationaleContent)
  
  // Update content when rationaleContent changes (e.g., from agent)
  React.useEffect(() => {
    if (rationaleContent && rationaleContent !== content) {
      console.log("📝 Rationale content updated from context:", rationaleContent.substring(0, 100))
      setContent(rationaleContent)
      
      // Update the contentEditable div
      const contentDiv = document.querySelector('[contenteditable="true"]')
      if (contentDiv) {
        contentDiv.innerHTML = rationaleContent
      }
    }
  }, [rationaleContent])

  const { generateProtocolSection, isGenerating, error } = useProtocolGeneration()
  
  console.log("🔍 Rationale Tab:", {
    rationaleContent,
    usingContext: propsTrials === undefined,
    indication,
    phase,
    selectedTrials: trials.length
  })

  const handleSave = () => {
    // Always save current content to context
    updateProtocolSection('rationale', content)
    console.log('💾 Saved rationale to context:', content.substring(0, 100) + '...')
    toast.success('Rationale saved successfully!')
  }

  const handleGenerate = async () => {
    try {
      const response = await generateProtocolSection({
        section_type: 'rationale',
        trials: trials,
        reference_info: referenceInfo
      })

      if (response && response.content) {
        const contentDiv = document.querySelector('[contenteditable="true"]')
        if (contentDiv) {
          contentDiv.innerHTML = response.content
          setContent(response.content)
        }
        
        // Save to context if available
        if (propsTrials === undefined) {
          updateProtocolSection('rationale', response.content)
        }
        
        toast.success('Study rationale generated successfully!')
      } else {
        toast.error('Failed to generate study rationale. Please try again.')
      }
    } catch (err) {
      console.error('Error generating rationale:', err)
      toast.error('Error generating study rationale. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Study Rationale</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Provide scientific and clinical justification for the study
          </p>
        </div>
        <div className="flex gap-2">
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
          <Button variant="outline" className="gap-2 bg-transparent" onClick={handleSave}>
            <Save className="h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      <div className="border border-border/50 rounded-lg bg-card">
        <div className="border-b border-border/50 p-3 flex items-center gap-2 bg-secondary/30">
          <Button variant="ghost" size="sm" className="h-8 px-2">
            <Plus className="h-4 w-4" />
          </Button>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" className="h-8 px-3 text-xs font-semibold">
              B
            </Button>
            <Button variant="ghost" size="sm" className="h-8 px-3 text-xs italic">
              I
            </Button>
            <Button variant="ghost" size="sm" className="h-8 px-3 text-xs underline">
              U
            </Button>
          </div>
        </div>
        <div
          contentEditable
          className="p-6 min-h-[500px] focus:outline-none text-foreground leading-relaxed prose prose-invert max-w-none"
          suppressContentEditableWarning
          onInput={(e) => setContent(e.currentTarget.textContent || "")}
          dangerouslySetInnerHTML={{
            __html: content || '<p class="text-muted-foreground">Start typing or use AI to generate content...</p>'
          }}
        />
      </div>

      <div className="bg-info-bg border border-info rounded-lg p-4">
        <h3 className="font-semibold text-info mb-2">Suggested Structure</h3>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
          <li>Disease background and unmet medical need</li>
          <li>Current treatment landscape and limitations</li>
          <li>Mechanism of action and preclinical data</li>
          <li>Prior clinical experience with the investigational product</li>
          <li>Rationale for study design and endpoints</li>
        </ul>
      </div>
    </div>
  )
}
