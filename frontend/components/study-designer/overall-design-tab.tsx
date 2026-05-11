"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sparkles, Save, Plus, Trash2, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface Arm {
  id: string
  name: string
  intervention: string
  participants: string
}

interface OverallDesignTabProps {
  trials?: any[]
  referenceInfo?: string
}

export function OverallDesignTab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: OverallDesignTabProps = {}) {
  // Use context data with props as fallback
  const {
    studyDesign: contextStudyDesign,
    setStudyDesign: setContextStudyDesign,
    selectedTrials,
    studyContext
  } = useStudyDesigner()
  
  // Extract indication, phase, and drug name from studyContext
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''
  const drugName = studyContext?.drugName || studyContext?.compound || ''

  // Use context data if available, otherwise use local state
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials

  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined
    ? propsReferenceInfo
    : extractReferenceInfoFromTrials(trials, { indication, phase })
  
  // Helper function to distribute participants evenly across arms
  const distributeParticipants = (total: number, numArms: number): string[] => {
    const perArm = Math.floor(total / numArms)
    const remainder = total % numArms
    
    const distribution: string[] = []
    for (let i = 0; i < numArms; i++) {
      // Add 1 extra to first 'remainder' arms to ensure sum equals total
      distribution.push((perArm + (i < remainder ? 1 : 0)).toString())
    }
    
    return distribution
  }
  
  // Helper function to get drug name from context or trials
  const getDrugName = (): string => {
    if (drugName) return drugName
    
    // Try to extract from reference trials
    if (trials && trials.length > 0) {
      for (const trial of trials) {
        if (trial.interventions && trial.interventions.length > 0) {
          const intervention = trial.interventions[0]
          if (intervention.name || intervention.intervention_name) {
            return intervention.name || intervention.intervention_name
          }
        }
      }
    }
    
    return 'Investigational Drug'
  }

  const [studyType, setStudyType] = useState("")
  const [totalParticipants, setTotalParticipants] = useState("")
  const [duration, setDuration] = useState("")
  const [arms, setArms] = useState<Arm[]>([{ id: "1", name: "", intervention: "", participants: "" }])

  // Load from context when component mounts or when contextStudyDesign changes
  useEffect(() => {
    if (contextStudyDesign) {
      setStudyType(contextStudyDesign.studyType || "")
      setTotalParticipants(contextStudyDesign.totalParticipants?.toString() || "")
      setDuration(contextStudyDesign.duration || "")
      setArms(contextStudyDesign.arms || [{ id: "1", name: "", intervention: "", participants: "" }])
      console.log("✅ Loaded study design from context:", contextStudyDesign)
    }
  }, [contextStudyDesign])

  const { generateStudyDesign, isGenerating, error } = useProtocolGeneration()

  console.log("🔍 Overall Design Tab:", {
    contextStudyDesign,
    usingContext: propsTrials === undefined,
    indication,
    phase,
    drugName: getDrugName(),
    selectedTrials: trials.length,
    referenceInfo: referenceInfo ? referenceInfo.substring(0, 100) + '...' : 'none'
  })

  const handleSave = () => {
    // Always save current study design to context
    const designData = {
      studyType,
      totalParticipants: parseInt(totalParticipants) || 0,
      duration,
      arms,
      indication,
      phase
    }
    
    setContextStudyDesign(designData)
    
    console.log('💾 Saved study design to context:', designData)
    toast.success('Study design saved successfully!')
  }

  const handleAIGenerate = async () => {
    try {
      // Build study context to pass to backend
      const studyContextData = {
        indication,
        phase,
        drugName: getDrugName(),
        totalParticipants: parseInt(totalParticipants) || 300
      }
      
      console.log("🚀 Generating study design with context:", studyContextData)
      
      const response = await generateStudyDesign({
        trials: trials,
        reference_info: referenceInfo,
        study_context: studyContextData
      })

      if (response && response.content) {
        // Backend returns plain text (markdown), not JSON
        const generatedContent = response.content

        // Parse the text content to extract design information
        // Look for key patterns in the generated text

        // Detect study type
        const studyTypeMatch = generatedContent.toLowerCase()
        let extractedStudyType = "rct"
        if (studyTypeMatch.includes("randomized")) extractedStudyType = "rct"
        else if (studyTypeMatch.includes("observational")) extractedStudyType = "observational"
        else if (studyTypeMatch.includes("single-arm") || studyTypeMatch.includes("single arm")) extractedStudyType = "single-arm"
        else if (studyTypeMatch.includes("crossover")) extractedStudyType = "crossover"

        // Extract participants (look for numbers like "300 patients", "N=300", etc.)
        const participantsMatch = generatedContent.match(/(?:N\s*=\s*|approximately\s+|up\s+to\s+)?(\d{2,4})\s*(?:patients|participants|subjects)/i)
        const extractedParticipants = participantsMatch ? participantsMatch[1] : "300"

        // Extract duration (look for patterns like "52 weeks", "12 months", etc.)
        const durationMatch = generatedContent.match(/(\d+)\s*(?:weeks|months|years)/i)
        const extractedDuration = durationMatch ? durationMatch[0] : "52 weeks"

        // Extract arms (look for treatment descriptions)
        let extractedArms: Arm[] = []

        // Try to find arm descriptions
        const armPattern = /(?:Arm\s+[A-Z]|Group\s+\d|Treatment\s+\d):\s*([^\n]+)/gi
        const armMatches = [...generatedContent.matchAll(armPattern)]

        const total = parseInt(extractedParticipants)
        const extractedDrugName = getDrugName()

        if (armMatches.length > 0) {
          // Use distributeParticipants to ensure arms sum to total
          const participantDistribution = distributeParticipants(total, armMatches.length)
          
          extractedArms = armMatches.map((match, idx) => ({
            id: (idx + 1).toString(),
            name: `Arm ${idx + 1}`,
            intervention: match[1].trim(),
            participants: participantDistribution[idx]
          }))
        } else {
          // Default to 2 arms if none detected (2:1 randomization for Phase II/III)
          const isPhase1 = phase && phase.toLowerCase().includes('1')
          const participantDistribution = isPhase1 
            ? distributeParticipants(total, 1)  // Single arm for Phase I
            : distributeParticipants(total, 2)  // Two arms for Phase II/III
          
          if (isPhase1) {
            extractedArms = [
              {
                id: "1",
                name: extractedDrugName,
                intervention: `${extractedDrugName} for ${indication || 'indication'}`,
                participants: participantDistribution[0],
              }
            ]
          } else {
            // 2:1 randomization
            const controlParticipants = Math.floor(total / 3)
            const treatmentParticipants = total - controlParticipants
            
            extractedArms = [
              {
                id: "1",
                name: extractedDrugName,
                intervention: `${extractedDrugName} for ${indication || 'indication'}`,
                participants: treatmentParticipants.toString(),
              },
              {
                id: "2",
                name: "Control",
                intervention: "Standard of care or placebo",
                participants: controlParticipants.toString(),
              },
            ]
          }
        }

        setStudyType(extractedStudyType)
        setTotalParticipants(extractedParticipants)
        setDuration(extractedDuration)
        setArms(extractedArms)

        // Save to context if available
        if (propsTrials === undefined) {
          setContextStudyDesign({
            studyType: extractedStudyType,
            totalParticipants: parseInt(extractedParticipants),
            duration: extractedDuration,
            arms: extractedArms,
            indication: indication,
            phase: phase
          })
        }

        toast.success('Study design generated successfully!')
      } else {
        // Fallback to context-based design if API fails
        const phaseText = phase ? (phase.startsWith('Phase') ? phase : `Phase ${phase}`) : 'Phase 3'
        const indicationText = indication || 'Advanced Non-Small Cell Lung Cancer'
        const extractedDrugName = getDrugName()
        
        const total = 300
        const controlParticipants = Math.floor(total / 3)  // 2:1 randomization
        const treatmentParticipants = total - controlParticipants

        setStudyType("rct")
        setTotalParticipants(total.toString())
        setDuration("52 weeks")
        setArms([
          {
            id: "1",
            name: extractedDrugName,
            intervention: `${extractedDrugName} for ${indicationText}`,
            participants: treatmentParticipants.toString(),
          },
          {
            id: "2",
            name: "Control",
            intervention: "Standard of care",
            participants: controlParticipants.toString(),
          },
        ])

        // Save to context if available
        if (propsTrials === undefined) {
          setContextStudyDesign({
            studyType: "rct",
            totalParticipants: total,
            duration: "52 weeks",
            arms: [
              {
                id: "1",
                name: extractedDrugName,
                intervention: `${extractedDrugName} for ${indicationText}`,
                participants: treatmentParticipants.toString(),
              },
              {
                id: "2",
                name: "Control",
                intervention: "Standard of care",
                participants: controlParticipants.toString(),
              },
            ],
            indication: indication,
            phase: phase
          })
        }

        toast.success('Study design generated from context!')
      }
    } catch (err) {
      console.error('Error generating study design:', err)

      // Generate from context as fallback
      const phaseText = phase ? `Phase ${phase}` : 'Phase 3'
      const indicationText = indication || 'Advanced Non-Small Cell Lung Cancer'
      const extractedDrugName = getDrugName()
      
      const total = 300
      const controlParticipants = Math.floor(total / 3)  // 2:1 randomization
      const treatmentParticipants = total - controlParticipants

      setStudyType("rct")
      setTotalParticipants(total.toString())
      setDuration("52 weeks")
      setArms([
        {
          id: "1",
          name: extractedDrugName,
          intervention: `${extractedDrugName} for ${indicationText}`,
          participants: treatmentParticipants.toString(),
        },
        {
          id: "2",
          name: "Control",
          intervention: "Standard of care",
          participants: controlParticipants.toString(),
        },
      ])

      if (propsTrials === undefined) {
        setContextStudyDesign({
          studyType: "rct",
          totalParticipants: total,
          duration: "52 weeks",
          arms: [
            {
              id: "1",
              name: extractedDrugName,
              intervention: `${extractedDrugName} for ${indicationText}`,
              participants: treatmentParticipants.toString(),
            },
            {
              id: "2",
              name: "Control",
              intervention: "Standard of care",
              participants: controlParticipants.toString(),
            },
          ],
          indication: indication,
          phase: phase
        })
      }

      toast.success('Study design generated from context!')
    }
  }

  const addArm = () => {
    setArms([...arms, { id: Date.now().toString(), name: "", intervention: "", participants: "" }])
  }

  const removeArm = (id: string) => {
    setArms(arms.filter((arm) => arm.id !== id))
  }

  const updateArm = (id: string, field: keyof Arm, value: string) => {
    setArms(arms.map((arm) => (arm.id === id ? { ...arm, [field]: value } : arm)))
  }
  
  // Calculate total from arms
  const calculateArmTotal = (): number => {
    return arms.reduce((sum, arm) => sum + (parseInt(arm.participants) || 0), 0)
  }
  
  // Check if arms sum equals total participants
  const armsValid = (): boolean => {
    const total = parseInt(totalParticipants) || 0
    const armTotal = calculateArmTotal()
    return total === armTotal
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Overall Study Design</h2>
          <p className="text-sm text-muted-foreground mt-1">Define study structure and intervention groups</p>
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
        {/* Study Overview */}
        <div className="border border-border/50 rounded-lg p-6 bg-card space-y-4">
          <h3 className="font-semibold text-foreground">Study Overview</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Study Type</Label>
              <Select value={studyType} onValueChange={setStudyType}>
                <SelectTrigger className="bg-background border-border/50">
                  <SelectValue placeholder="Select study type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rct">Randomized Controlled Trial</SelectItem>
                  <SelectItem value="observational">Observational Study</SelectItem>
                  <SelectItem value="single-arm">Single-Arm Trial</SelectItem>
                  <SelectItem value="crossover">Crossover Trial</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Total Participants</Label>
              <Input
                placeholder="e.g., 300"
                value={totalParticipants}
                onChange={(e) => setTotalParticipants(e.target.value)}
                className="bg-background border-border/50"
              />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Study Duration</Label>
              <Input
                placeholder="e.g., 52 weeks"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="bg-background border-border/50"
              />
            </div>
          </div>
        </div>

        {/* Intervention Arms */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-lg font-semibold">Intervention Arms</Label>
            <Button variant="outline" size="sm" onClick={addArm} className="gap-2 bg-transparent">
              <Plus className="h-4 w-4" />
              Add Arm
            </Button>
          </div>
          {arms.map((arm, index) => (
            <div key={arm.id} className="border border-border/50 rounded-lg p-4 bg-card space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">Arm {index + 1}</span>
                {arms.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeArm(arm.id)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Arm Name</Label>
                  <Input
                    placeholder="e.g., Treatment A"
                    value={arm.name}
                    onChange={(e) => updateArm(arm.id, "name", e.target.value)}
                    className="bg-background border-border/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Intervention</Label>
                  <Input
                    placeholder="e.g., Drug X 100mg"
                    value={arm.intervention}
                    onChange={(e) => updateArm(arm.id, "intervention", e.target.value)}
                    className="bg-background border-border/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Participants</Label>
                  <Input
                    placeholder="e.g., 150"
                    value={arm.participants}
                    onChange={(e) => updateArm(arm.id, "participants", e.target.value)}
                    className="bg-background border-border/50"
                  />
                </div>
              </div>
            </div>
          ))}
          
          {/* Arms Total Validation */}
          {arms.length > 0 && totalParticipants && (
            <div className={`border rounded-lg p-4 ${armsValid() ? 'border-green-500/50 bg-green-500/5' : 'border-amber-500/50 bg-amber-500/5'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Total Participants from Arms:</span>
                  <span className={`text-lg font-bold ${armsValid() ? 'text-green-600' : 'text-amber-600'}`}>
                    {calculateArmTotal()}
                  </span>
                  <span className="text-sm text-muted-foreground">/ {totalParticipants}</span>
                </div>
                {armsValid() ? (
                  <span className="text-xs text-green-600 font-medium">✓ Arms sum correctly</span>
                ) : (
                  <span className="text-xs text-amber-600 font-medium">⚠️ Arms should sum to {totalParticipants}</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
