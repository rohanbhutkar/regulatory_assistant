"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Sparkles, Save, Plus, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { toast } from "sonner"

interface ProtocolSectionEditorProps {
  title: string
  content: string
  onContentChange: (content: string) => void
  trials?: any[]
  referenceInfo?: string
}

// Section-specific configurations
const sectionConfig: Record<string, { description: string; structure: string[] }> = {
  'Introduction': {
    description: 'Provide context and overview for the clinical trial',
    structure: [
      'Disease overview and epidemiology',
      'Clinical manifestations and current burden',
      'Investigational product and mechanism of action',
      'Study design overview',
      'Expected contribution to the field'
    ]
  },
  'Background': {
    description: 'Establish the scientific and clinical foundation for the study',
    structure: [
      'Disease pathophysiology and natural history',
      'Current standard of care and treatment options',
      'Prior/concurrent therapies used in reference trials',
      'Investigational product detailed mechanism of action',
      'Clinical evidence from previous studies',
      'Relevant biomarker data'
    ]
  },
  'Hypothesis': {
    description: 'State the primary hypothesis and scientific assumptions',
    structure: [
      'Primary hypothesis statement',
      'Scientific rationale for the hypothesis',
      'Expected effect size and clinical significance',
      'Supporting evidence from preclinical and clinical data',
      'Alternative hypotheses (if applicable)'
    ]
  }
}

export function ProtocolSectionEditor({ title, content, onContentChange, trials = [], referenceInfo = '' }: ProtocolSectionEditorProps) {
  const [localContent, setLocalContent] = useState(content)
  
  // Update local content when prop changes
  useEffect(() => {
    if (content && content !== localContent) {
      console.log(`📝 ${title} content updated from context:`, content.substring(0, 100))
      setLocalContent(content)
      
      // Update the contentEditable div
      const contentDiv = document.querySelector(`[data-section="${title}"][contenteditable="true"]`)
      if (contentDiv) {
        contentDiv.innerHTML = content
      }
    }
  }, [content, title])

  const { generateProtocolSection, isGenerating, error } = useProtocolGeneration()
  
  const config = sectionConfig[title] || {
    description: `Generate and edit the ${title.toLowerCase()} section`,
    structure: []
  }

  const handleGenerate = async () => {
    try {
      // Determine section type based on title
      let sectionType = title.toLowerCase().replace(/\s+/g, '_')
      if (title.toLowerCase().includes('rationale')) sectionType = 'rationale'
      else if (title.toLowerCase().includes('objective')) sectionType = 'primary_objectives'
      else if (title.toLowerCase().includes('endpoint')) sectionType = 'primary_endpoints'
      else if (title.toLowerCase().includes('eligibility') || title.toLowerCase().includes('criteria')) sectionType = 'inclusion_criteria'
      else if (title.toLowerCase().includes('schedule') || title.toLowerCase().includes('activities')) sectionType = 'schedule_of_activities'
      else if (title.toLowerCase().includes('design')) sectionType = 'study_design'
      else if (title.toLowerCase().includes('schema')) sectionType = 'schema'
      else if (title.toLowerCase().includes('introduction')) sectionType = 'introduction'
      else if (title.toLowerCase().includes('background')) sectionType = 'background'
      else if (title.toLowerCase().includes('hypothesis')) sectionType = 'hypothesis'

      const response = await generateProtocolSection({
        section_type: sectionType,
        trials: trials,
        reference_info: referenceInfo
      })

      if (response && response.content) {
        const contentDiv = document.querySelector(`[data-section="${title}"][contenteditable="true"]`)
        if (contentDiv) {
          contentDiv.innerHTML = response.content
          setLocalContent(response.content)
        }
        onContentChange(response.content)
        toast.success(`${title} generated successfully!`)
      } else {
        toast.error(`Failed to generate ${title}. Please try again.`)
      }
    } catch (err) {
      console.error('Error generating protocol section:', err)
      toast.error('Error generating content. Please check your connection.')
    }
  }

  const handleSave = () => {
    onContentChange(localContent)
    console.log(`💾 Saved ${title} to context:`, localContent.substring(0, 100) + '...')
    toast.success(`${title} saved successfully!`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">{title}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {config.description}
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
          data-section={title}
          contentEditable
          className="p-6 min-h-[500px] focus:outline-none text-foreground leading-relaxed prose prose-invert max-w-none"
          suppressContentEditableWarning
          onInput={(e) => setLocalContent(e.currentTarget.textContent || "")}
          dangerouslySetInnerHTML={{
            __html: localContent || '<p class="text-muted-foreground">Start typing or use AI to generate content...</p>'
          }}
        />
      </div>

      {config.structure.length > 0 && (
        <div className="bg-info-bg border border-info rounded-lg p-4">
          <h3 className="font-semibold text-info mb-2">Suggested Structure</h3>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            {config.structure.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
