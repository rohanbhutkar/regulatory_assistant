"use client"

import { Button } from "@/components/ui/button"
import { Sparkles, Save, Download, Loader2 } from "lucide-react"
import { useState } from "react"
import { StudySchemaDigram } from "./study-schema-diagram"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface SchemaTabProps {
  trials?: any[]
  referenceInfo?: string
}

export function SchemaTab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: SchemaTabProps = {}) {
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
  const studyDesign = studyContext?.studyDesign || ''
  
  // Use context data if available, otherwise use props
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials
  
  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined 
    ? propsReferenceInfo 
    : extractReferenceInfoFromTrials(trials, { indication, phase })
  
  // Get protocol schema section from context (protocolSections is an object, not array)
  const schemaSection = protocolSections?.schema || ''
  
  const [showSchema, setShowSchema] = useState(schemaSection ? true : true)

  const { generateStudySchema, isGenerating, error } = useProtocolGeneration()
  
  console.log("🔍 Schema Tab:", {
    schemaSection: schemaSection ? `${schemaSection.substring(0, 100)}...` : 'none',
    usingContext: propsTrials === undefined,
    indication,
    phase,
    studyDesign,
    selectedTrials: trials.length
  })

  const handleSave = () => {
    // Always save to context if there's content
    if (schemaSection) {
      updateProtocolSection('schema', schemaSection)
      console.log('💾 Schema saved to context:', schemaSection.substring(0, 100) + '...')
      toast.success('Study schema saved successfully!')
    } else {
      toast.error('No schema content to save. Please generate the schema first.')
    }
  }

  const handleGenerate = async () => {
    try {
      console.log('🔄 Generating schema with:', {
        trialsCount: trials.length,
        referenceInfoLength: referenceInfo.length,
        indication,
        phase
      })
      
      const response = await generateStudySchema({
        trials: trials,
        reference_info: referenceInfo
      })

      console.log('✅ Schema generation response:', {
        success: response?.success,
        hasContent: !!response?.content,
        contentLength: response?.content?.length || 0,
        contentPreview: response?.content?.substring(0, 100) || 'none'
      })

      if (response && response.content) {
        setShowSchema(true)
        
        // Save to context if available
        if (propsTrials === undefined) {
          updateProtocolSection('schema', response.content)
          console.log('💾 Schema saved to context')
        }
        
        toast.success('Study schema generated successfully!')
      } else {
        console.error('❌ No content in schema response')
        toast.error('Failed to generate study schema. Please try again.')
      }
    } catch (err) {
      console.error('❌ Error generating study schema:', err)
      toast.error('Error generating study schema. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Study Schema</h2>
          <p className="text-sm text-muted-foreground mt-1">Visual representation of study flow and timeline</p>
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
          <Button variant="outline" className="gap-2 bg-transparent">
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" className="gap-2 bg-transparent" onClick={handleSave}>
            <Save className="h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      {showSchema ? (
        <div className="space-y-6">
          {/* AI Generated Content */}
          {schemaSection && (
            <div className="bg-card border border-border/50 rounded-lg p-6">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-foreground mb-2">AI-Generated Study Schema</h3>
                <p className="text-sm text-muted-foreground">Schema details generated from reference trials</p>
              </div>
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <div className="whitespace-pre-wrap text-foreground">{schemaSection}</div>
              </div>
            </div>
          )}
          
          {/* Visual Diagram */}
          <StudySchemaDigram 
            studyDuration={studyContext.duration_text}
            numberOfArms={studyContext.numberOfArms}
            studyType={studyContext.studyType}
            totalParticipants={studyContext.totalParticipants}
          />
        </div>
      ) : (
        <div className="border-2 border-dashed border-border/50 rounded-lg p-12 bg-card/50 flex flex-col items-center justify-center min-h-[500px]">
          <div className="text-center space-y-4 max-w-md">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
              <Sparkles className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-xl font-semibold text-foreground">Generate Study Schema</h3>
            <p className="text-muted-foreground">
              Use AI to automatically generate a visual study schema based on your protocol design, or upload your own
              diagram.
            </p>
            <div className="flex gap-3 justify-center pt-4">
              <Button onClick={handleGenerate} disabled={isGenerating} className="gap-2">
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
              <Button variant="outline">Upload Diagram</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
