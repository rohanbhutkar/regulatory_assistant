"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Sparkles, Save, Plus, Trash2, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface Endpoint {
  id: string
  type: "primary" | "secondary"
  name: string
  description: string
  timepoint: string
}

interface EndpointsTabProps {
  trials?: any[]
  referenceInfo?: string
}

export function EndpointsTab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: EndpointsTabProps = {}) {
  // Use context data with props as fallback
  const {
    endpoints: contextEndpoints,
    setEndpoints: setContextEndpoints,
    selectedTrials,
    studyContext
  } = useStudyDesigner()
  
  // Extract indication and phase from studyContext
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''

  // Protocol generation hook
  const { generateEndpoints, isGenerating, error } = useProtocolGeneration()

  // Use context data if available, otherwise use local state
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials

  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined
    ? propsReferenceInfo
    : extractReferenceInfoFromTrials(trials, { indication, phase })

  // Local state (only used if not from context)
  const [localEndpoints, setLocalEndpoints] = useState<Endpoint[]>([
    { id: "1", type: "primary", name: "", description: "", timepoint: "" },
  ])

  // Use context or local endpoints
  const endpoints = contextEndpoints.length > 0 ? contextEndpoints : localEndpoints
  const setEndpoints = contextEndpoints.length > 0 || propsTrials === undefined ? setContextEndpoints : setLocalEndpoints


  console.log("🔍 Endpoints Tab:", {
    contextEndpoints: contextEndpoints.length,
    localEndpoints: localEndpoints.length,
    usingContext: contextEndpoints.length > 0 || propsTrials === undefined,
    indication,
    phase,
    selectedTrials: trials.length
  })

  const handleSave = () => {
    // Explicitly save endpoints to context
    setEndpoints([...endpoints])
    console.log('💾 Saved endpoints to context:', {
      primary: endpoints.filter(e => e.type === 'primary').length,
      secondary: endpoints.filter(e => e.type === 'secondary').length,
      exploratory: endpoints.filter(e => e.type === 'exploratory').length
    })
    toast.success('Endpoints saved successfully!')
  }

  const handleAIGenerate = async () => {
    console.log("🎬 handleAIGenerate called for endpoints")

    // Validate we have necessary data
    if (!indication || !phase) {
      console.log("❌ Validation failed: missing indication or phase")
      toast.error('Please fill in Basic Info (indication and phase) before generating endpoints')
      return
    }
    
    if (trials.length === 0) {
      console.log("❌ Validation failed: no trials selected")
      toast.error('Please select at least one reference trial before generating endpoints')
      return
    }

    try {
      console.log("🔍 Endpoints Tab - Generating with:", {
        trialsCount: trials.length,
        indication,
        phase,
        referenceInfo: referenceInfo ? referenceInfo.substring(0, 100) + '...' : '(empty)'
      })
      
      const response = await generateEndpoints({
        trials: trials,
        reference_info: referenceInfo || ''
      })
      
      console.log("📋 Received endpoints response:", response)
      console.log("📋 Content length:", response?.content?.length || 0)
      console.log("📋 First 500 chars:", response?.content?.substring(0, 500))

      if (response && response.content) {
        const content = response.content
        console.log("📋 Full content for parsing:", content)
        
        const endpointsArray: Endpoint[] = []
        
        // Helper to clean markdown formatting
        const cleanMarkdown = (text: string): string => {
          return text
            .replace(/\*\*/g, '') // Remove bold markers
            .replace(/^[-•]\s*/, '') // Remove bullet points
            .replace(/^\s*\*\s*/, '') // Remove asterisk bullets
            .trim()
        }
        
        // Parse based on the expected format:
        // **Primary Endpoint(s):**
        // **Endpoint Name**
        // - **Definition**: Description
        // - **Timepoint**: When measured
        
        const lines = content.split('\n').map(l => l.trim()).filter(l => l)
        console.log("📋 Total lines:", lines.length)
        
        let currentType: "primary" | "secondary" = "secondary"
        let currentEndpoint: Partial<Endpoint> | null = null
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]
          
          // Detect section headers (be flexible with "Endpoint" vs "Endpoints")
          if (line.match(/\*\*Primary.*Endpoint/i)) {
            currentType = "primary"
            console.log("📍 Found Primary Endpoints section")
            continue
          }
          if (line.match(/\*\*Secondary.*Endpoint/i)) {
            // Save previous endpoint before switching sections
            if (currentEndpoint && currentEndpoint.name) {
              endpointsArray.push({
                id: `ep-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                type: currentType,
                name: currentEndpoint.name,
                description: currentEndpoint.description || currentEndpoint.name,
                timepoint: currentEndpoint.timepoint || "As specified in protocol"
              })
              console.log(`✅ Added ${currentType} endpoint: ${currentEndpoint.name}`)
              currentEndpoint = null
            }
            currentType = "secondary"
            console.log("📍 Found Secondary Endpoints section")
            continue
          }
          
          // Skip tables
          if (line.includes('|') || line.match(/^[-=]{3,}/)) {
            continue
          }
          
          // Check if this is a bold endpoint name (no bullet point, no colon inside the bold)
          const endpointNameMatch = line.match(/^\*\*([^*]+)\*\*\s*$/)
          if (endpointNameMatch) {
            // Save previous endpoint if exists
            if (currentEndpoint && currentEndpoint.name) {
              endpointsArray.push({
                id: `ep-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                type: currentType,
                name: currentEndpoint.name,
                description: currentEndpoint.description || currentEndpoint.name,
                timepoint: currentEndpoint.timepoint || "As specified in protocol"
              })
              console.log(`✅ Added ${currentType} endpoint: ${currentEndpoint.name}`)
            }
            
            // Start new endpoint
            currentEndpoint = {
              name: cleanMarkdown(endpointNameMatch[1]),
              description: "",
              timepoint: "As specified in protocol"
            }
            continue
          }
          
          // Check for definition bullet point
          const definitionMatch = line.match(/^[-•*]\s*\*\*Definition\*\*:?\s*(.+)/i)
          if (definitionMatch && currentEndpoint) {
            currentEndpoint.description = cleanMarkdown(definitionMatch[1])
            continue
          }
          
          // Check for timepoint bullet point
          const timepointMatch = line.match(/^[-•*]\s*\*\*Timepoint\*\*:?\s*(.+)/i)
          if (timepointMatch && currentEndpoint) {
            currentEndpoint.timepoint = cleanMarkdown(timepointMatch[1])
            continue
          }
          
          // Check for assessment/measure bullet point (alternative to definition)
          const measureMatch = line.match(/^[-•*]\s*\*\*(Measure|Assessment)\*\*:?\s*(.+)/i)
          if (measureMatch && currentEndpoint && !currentEndpoint.description) {
            currentEndpoint.description = cleanMarkdown(measureMatch[2])
            continue
          }
        }
        
        // Don't forget the last endpoint
        if (currentEndpoint && currentEndpoint.name) {
          endpointsArray.push({
            id: `ep-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type: currentType,
            name: currentEndpoint.name,
            description: currentEndpoint.description || currentEndpoint.name,
            timepoint: currentEndpoint.timepoint || "As specified in protocol"
          })
          console.log(`✅ Added ${currentType} endpoint: ${currentEndpoint.name}`)
        }
        
        console.log("📋 Parsed endpoints:", endpointsArray)
        
        // If no endpoints parsed, try a simpler fallback parser
        if (endpointsArray.length === 0) {
          console.log("⚠️ No endpoints from main parser, trying fallback...")
          
          // Simple fallback: Look for any lines that look like endpoint descriptions
          const simpleLines = content.split('\n').filter(line => {
            const trimmed = line.trim()
            return trimmed.length > 20 && 
                   !trimmed.startsWith('#') && 
                   !trimmed.match(/^[\*_]{2}.*Endpoint.*[\*_]{2}:?\s*$/i) &&
                   (trimmed.includes('survival') || 
                    trimmed.includes('response') || 
                    trimmed.includes('progression') ||
                    trimmed.includes('quality') ||
                    trimmed.includes('toxicity') ||
                    trimmed.includes('safety') ||
                    trimmed.includes('time to') ||
                    trimmed.match(/^\d+\./))
          })
          
          console.log("📋 Fallback found lines:", simpleLines)
          
          let isPrimary = true
          simpleLines.forEach((line, idx) => {
            if (line.match(/secondary/i)) isPrimary = false
            if (line.match(/primary/i)) isPrimary = true
            
            const cleaned = cleanMarkdown(line)
            if (cleaned.length > 10) {
              const parts = cleaned.split(':')
              const name = parts[0].replace(/^\d+\.\s*/, '').trim()
              const description = parts.slice(1).join(':').trim() || name
              
              if (name) {
                endpointsArray.push({
                  id: `fallback-${idx}`,
                  type: isPrimary ? 'primary' : 'secondary',
                  name: name.substring(0, 100),
                  description: description.substring(0, 500),
                  timepoint: 'As specified in protocol'
                })
              }
            }
          })
          
          console.log("📋 Fallback parsed endpoints:", endpointsArray)
        }
        
        if (endpointsArray.length > 0) {
          // Convert any "exploratory" type to "secondary" for display
          const normalizedEndpoints = endpointsArray.map(ep => ({
            ...ep,
            type: (ep.type === 'exploratory' ? 'secondary' : ep.type) as "primary" | "secondary"
          }))
          
          setEndpoints(normalizedEndpoints)
          const primaryCount = normalizedEndpoints.filter(e => e.type === 'primary').length
          const secondaryCount = normalizedEndpoints.filter(e => e.type === 'secondary').length
          toast.success(`Generated ${primaryCount} primary and ${secondaryCount} secondary endpoints!`)
        } else {
          console.log("❌ No endpoints could be parsed from response even with fallback")
          console.log("📋 Raw content:", content)
          toast.error('No endpoints could be parsed. The AI may have returned an unexpected format. Please try again or enter manually.')
        }
      } else {
        console.log("❌ No response or content from API")
        toast.error('Failed to generate study endpoints. Please try again.')
      }
    } catch (err) {
      console.error('❌ Error generating endpoints:', err)
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Error generating study endpoints: ${errorMsg}`)
    }
  }

  const addEndpoint = (type: "primary" | "secondary") => {
    setEndpoints([
      ...endpoints,
      { id: Date.now().toString(), type, name: "", description: "", timepoint: "" },
    ])
  }

  const removeEndpoint = (id: string) => {
    setEndpoints(endpoints.filter((ep) => ep.id !== id))
  }

  const updateEndpoint = (id: string, field: keyof Endpoint, value: string) => {
    setEndpoints(endpoints.map((ep) => (ep.id === id ? { ...ep, [field]: value } : ep)))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Endpoints & Estimands</h2>
          <p className="text-sm text-muted-foreground mt-1">Define study endpoints and statistical estimands</p>
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

      <div className="space-y-8 max-w-5xl">
        {/* Primary Endpoints */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-lg font-semibold">Primary Endpoints</Label>
            <Button variant="outline" size="sm" onClick={() => addEndpoint("primary")} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Primary
            </Button>
          </div>
          {endpoints
            .filter((ep) => ep.type === "primary")
            .map((endpoint, index) => (
              <div key={endpoint.id} className="border border-border/50 rounded-lg p-4 bg-card space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">Primary Endpoint {index + 1}</span>
                  {endpoints.filter((e) => e.type === "primary").length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeEndpoint(endpoint.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Endpoint Name</Label>
                    <Input
                      placeholder="e.g., Overall Survival"
                      value={endpoint.name}
                      onChange={(e) => updateEndpoint(endpoint.id, "name", e.target.value)}
                      className="bg-background border-border/50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Timepoint</Label>
                    <Input
                      placeholder="e.g., Week 24"
                      value={endpoint.timepoint}
                      onChange={(e) => updateEndpoint(endpoint.id, "timepoint", e.target.value)}
                      className="bg-background border-border/50"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Measure</Label>
                  <Textarea
                    placeholder="Describe how the endpoint will be measured..."
                    value={endpoint.description}
                    onChange={(e) => updateEndpoint(endpoint.id, "description", e.target.value)}
                    className="bg-background border-border/50 min-h-[80px]"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Estimand</Label>
                  <Textarea
                    placeholder="Define the treatment effect and population..."
                    value={endpoint.description}
                    onChange={(e) => updateEndpoint(endpoint.id, "description", e.target.value)}
                    className="bg-background border-border/50 min-h-[80px]"
                  />
                </div>
              </div>
            ))}
        </div>

        {/* Secondary Endpoints */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-lg font-semibold">Secondary Endpoints</Label>
            <Button variant="outline" size="sm" onClick={() => addEndpoint("secondary")} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Secondary
            </Button>
          </div>
          {endpoints
            .filter((ep) => ep.type === "secondary")
            .map((endpoint, index) => (
              <div key={endpoint.id} className="border border-border/50 rounded-lg p-4 bg-card space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">Secondary Endpoint {index + 1}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeEndpoint(endpoint.id)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Endpoint Name</Label>
                    <Input
                      placeholder="e.g., Progression-Free Survival"
                      value={endpoint.name}
                      onChange={(e) => updateEndpoint(endpoint.id, "name", e.target.value)}
                      className="bg-background border-border/50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Timepoint</Label>
                    <Input
                      placeholder="e.g., Week 12"
                      value={endpoint.timepoint}
                      onChange={(e) => updateEndpoint(endpoint.id, "timepoint", e.target.value)}
                      className="bg-background border-border/50"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Measure</Label>
                  <Textarea
                    placeholder="Describe how the endpoint will be measured..."
                    value={endpoint.description}
                    onChange={(e) => updateEndpoint(endpoint.id, "description", e.target.value)}
                    className="bg-background border-border/50 min-h-[80px]"
                  />
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
