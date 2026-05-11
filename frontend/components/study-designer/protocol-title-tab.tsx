"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Sparkles, Save, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface ProtocolTitleTabProps {
  trials?: any[]
  referenceInfo?: string
}

export function ProtocolTitleTab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: ProtocolTitleTabProps = {}) {
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
  
  // Use context data if available, otherwise use local state
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials
  
  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined 
    ? propsReferenceInfo 
    : extractReferenceInfoFromTrials(trials, { indication, phase })
  
  // Get protocol title section from context (protocolSections is a Record<string, string>)
  const titleContent = protocolSections?.title || ""
  
  const [title, setTitle] = useState("")
  const [shortTitle, setShortTitle] = useState("")
  const [protocolNumber, setProtocolNumber] = useState("")
  const [version, setVersion] = useState("1.0")

  const { generateProtocolSection, isGenerating, error } = useProtocolGeneration()
  
  // Load from context when component mounts or when titleContent changes
  useEffect(() => {
    if (titleContent) {
      try {
        const titleData = JSON.parse(titleContent)
        setTitle(titleData.fullTitle || "")
        setShortTitle(titleData.shortTitle || "")
        setProtocolNumber(titleData.protocolNumber || "")
        setVersion(titleData.version || "1.0")
        console.log("✅ Loaded title from context:", titleData)
      } catch (e) {
        // If it's not JSON, treat it as plain title text
        setTitle(titleContent)
        console.log("✅ Loaded plain title from context")
      }
    }
  }, [titleContent])
  
  console.log("🔍 Protocol Title Tab:", {
    titleContent,
    usingContext: propsTrials === undefined,
    indication,
    phase,
    selectedTrials: trials.length
  })

  const handleSave = () => {
    // Always save current title to context
    const titleData = {
      fullTitle: title,
      shortTitle: shortTitle,
      protocolNumber: protocolNumber,
      version: version
    }
    updateProtocolSection('title', JSON.stringify(titleData))
    console.log('💾 Saved title to context:', titleData)
    toast.success('Protocol title saved successfully!')
  }

  const handleGenerate = async () => {
    console.log("🎬 handleGenerate called")
    
    // Validate we have necessary data
    if (!indication || !phase) {
      console.log("❌ Validation failed: missing indication or phase")
      toast.error('Please fill in Basic Info (indication and phase) before generating title')
      return
    }
    
    if (trials.length === 0) {
      console.log("❌ Validation failed: no trials selected")
      toast.error('Please select at least one reference trial before generating title')
      return
    }
    
    try {
      console.log("🔍 Generating protocol title with:", {
        indication,
        phase,
        trialsCount: trials.length,
        referenceInfo: referenceInfo ? referenceInfo.substring(0, 100) + '...' : '(empty)'
      })
      
      const response = await generateProtocolSection({
        section_type: 'title',
        trials: trials,
        reference_info: referenceInfo || ''
      })

      if (response && response.content) {
        // The backend returns both full title and short title in structured format
        const generatedContent = response.content
        
        console.log("📋 Received title content:", generatedContent.substring(0, 200))
        
        // Parse the structured response from backend
        // Backend may return various formats:
        // 1. "FULL TITLE:\n[title]\n\nSHORT TITLE:\n[short title]"
        // 2. Just the title as a paragraph
        // 3. Markdown formatted with headers
        
        let fullTitle = ''
        let shortTitleGenerated = ''
        
        // Try to parse structured format first
        if (generatedContent.includes('FULL TITLE:') || generatedContent.includes('SHORT TITLE:')) {
          const lines = generatedContent.split('\n')
          let currentSection = ''
          let currentTitle = ''
          
          console.log("🔍 Parsing structured format, total lines:", lines.length)
          
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i]
            const trimmedLine = line.trim()
            
            // Check for section headers (with or without markdown bold)
            const fullTitleMatch = trimmedLine.match(/^\*?\*?(FULL TITLE|Full Title|Protocol Title):\*?\*?/i)
            const shortTitleMatch = trimmedLine.match(/^\*?\*?(SHORT TITLE|Short Title|Abbreviated Title):\*?\*?/i)
            
            if (fullTitleMatch) {
              // Save previous section
              if (currentSection === 'full' && currentTitle) {
                fullTitle = currentTitle.trim()
              } else if (currentSection === 'short' && currentTitle) {
                shortTitleGenerated = currentTitle.trim()
              }
              
              currentSection = 'full'
              currentTitle = ''
              
              // Check if title is on the same line after colon
              const titleOnSameLine = trimmedLine.split(':').slice(1).join(':').trim().replace(/^\*\*|\*\*$/g, '')
              if (titleOnSameLine) {
                currentTitle = titleOnSameLine
              }
              console.log(`📍 Line ${i}: Found FULL TITLE header, titleOnSameLine:`, titleOnSameLine)
            } else if (shortTitleMatch) {
              // Save previous section
              if (currentSection === 'full' && currentTitle) {
                fullTitle = currentTitle.trim()
              } else if (currentSection === 'short' && currentTitle) {
                shortTitleGenerated = currentTitle.trim()
              }
              
              currentSection = 'short'
              currentTitle = ''
              
              // Check if title is on the same line after colon
              const titleOnSameLine = trimmedLine.split(':').slice(1).join(':').trim().replace(/^\*\*|\*\*$/g, '')
              if (titleOnSameLine) {
                currentTitle = titleOnSameLine
              }
              console.log(`📍 Line ${i}: Found SHORT TITLE header, titleOnSameLine:`, titleOnSameLine)
            } else if (trimmedLine && !trimmedLine.startsWith('#') && currentSection) {
              // Accumulate content for current section (handle multi-line titles)
              if (currentTitle) {
                currentTitle += ' ' + trimmedLine
              } else {
                currentTitle = trimmedLine
              }
              console.log(`📍 Line ${i}: Adding to ${currentSection}:`, trimmedLine.substring(0, 50))
            }
          }
          
          // Don't forget the last section
          if (currentSection === 'full' && currentTitle) {
            fullTitle = currentTitle.trim()
          } else if (currentSection === 'short' && currentTitle) {
            shortTitleGenerated = currentTitle.trim()
          }
          
          console.log("🔍 After structured parsing:", { fullTitle: fullTitle.substring(0, 100), shortTitleGenerated })
        } else {
          // If no structured format, use the content as the full title
          // Remove markdown headers
          fullTitle = generatedContent
            .split('\n')
            .filter(line => !line.trim().startsWith('#'))
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('**'))
            .join(' ')
            .substring(0, 500) // Limit length
        }
        
        // Generate short title from full title if not provided
        if (!shortTitleGenerated && fullTitle) {
          // Try to create a short title from the full title
          const phaseText = phase ? (phase.startsWith('Phase') ? phase : `Phase ${phase}`) : ''
          const indicationShort = indication.split(' ').slice(0, 3).join(' ')
          shortTitleGenerated = `${phaseText} ${indicationShort} Study`.trim()
        }
        
        // Clean up titles (remove markdown formatting)
        fullTitle = fullTitle.replace(/\*\*/g, '').trim()
        shortTitleGenerated = shortTitleGenerated.replace(/\*\*/g, '').trim()
        
        console.log("📋 Parsed titles:", { fullTitle, shortTitleGenerated })
        
        if (!fullTitle) {
          toast.error('Could not parse title from AI response. Please try again.')
          return
        }
        
        setTitle(fullTitle)
        setShortTitle(shortTitleGenerated)
        setProtocolNumber(`PROTO-${new Date().getFullYear()}-${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`)
        setVersion("1.0")
        
        // Save to context if available
        if (propsTrials === undefined) {
          updateProtocolSection('title', fullTitle)
        }
        
        toast.success('Protocol title generated successfully!')
      } else {
        console.log("❌ No response or content from API")
        toast.error('Failed to generate protocol title. Please try again.')
      }
    } catch (err) {
      console.error('❌ Error generating protocol title:', err)
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Error generating protocol title: ${errorMsg}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Protocol Title Page</h2>
          <p className="text-sm text-muted-foreground mt-1">Define the core identifiers for your protocol</p>
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

      <div className="grid gap-6 max-w-3xl">
        <div className="space-y-2">
          <Label htmlFor="protocol-number">Protocol Number</Label>
          <Input
            id="protocol-number"
            placeholder="e.g., ABC-123-2024"
            value={protocolNumber}
            onChange={(e) => setProtocolNumber(e.target.value)}
            className="bg-card border-border/50"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="version">Version</Label>
          <Input
            id="version"
            placeholder="e.g., 1.0"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            className="bg-card border-border/50"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="full-title">Full Protocol Title</Label>
          <Textarea
            id="full-title"
            placeholder="Enter the complete protocol title..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="bg-card border-border/50 min-h-[120px] resize-none"
          />
          <p className="text-xs text-muted-foreground">
            Should include study design, population, intervention, and primary endpoint
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="short-title">Short Title</Label>
          <Input
            id="short-title"
            placeholder="e.g., STELLAR Trial"
            value={shortTitle}
            onChange={(e) => setShortTitle(e.target.value)}
            className="bg-card border-border/50"
          />
          <p className="text-xs text-muted-foreground">Abbreviated name for easy reference</p>
        </div>
      </div>
    </div>
  )
}

