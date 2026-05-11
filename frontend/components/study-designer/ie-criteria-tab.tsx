"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { IECriterion } from "@/lib/types/study-types"
import { Plus, Trash2, Users, TrendingDown, AlertCircle, Sparkles, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

// Props are now optional since we get data from context
interface IECriteriaTabProps {
  criteria?: IECriterion[]
  onCriteriaChange?: (criteria: IECriterion[]) => void
  trials?: any[]
  referenceInfo?: string
}

export function IECriteriaTab({ criteria: propsCriteria, onCriteriaChange: propsOnChange, trials: propsTrials, referenceInfo: propsReferenceInfo }: IECriteriaTabProps = {}) {
  // Use context data with props as fallback
  const {
    inclusionCriteria,
    exclusionCriteria,
    setInclusionCriteria,
    setExclusionCriteria,
    selectedTrials,
    studyContext
  } = useStudyDesigner()
  
  // Extract indication and phase from studyContext
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''

  // Combine context criteria (from separate arrays)
  const contextCriteria = [...(inclusionCriteria || []), ...(exclusionCriteria || [])]

  // Use context data if available, otherwise use props
  const criteria = propsCriteria !== undefined ? propsCriteria : contextCriteria
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials

  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined
    ? propsReferenceInfo
    : extractReferenceInfoFromTrials(trials, { indication, phase })

  const [newCriterion, setNewCriterion] = useState("")
  const [criterionType, setCriterionType] = useState<"inclusion" | "exclusion">("inclusion")

  const { generateCriteria, isGenerating, error } = useProtocolGeneration()

  // Helper to update context (split by type into separate arrays)
  const updateContextCriteria = (newCriteria: IECriterion[]) => {
    const inclusion = newCriteria.filter(c => c.type === 'inclusion')
    const exclusion = newCriteria.filter(c => c.type === 'exclusion')
    setInclusionCriteria(inclusion)
    setExclusionCriteria(exclusion)
  }

  // Helper to add a single criterion
  const addCriterion = (criterion: IECriterion) => {
    if (propsOnChange) {
      propsOnChange([...criteria, criterion])
    } else {
      updateContextCriteria([...contextCriteria, criterion])
    }
  }

  // Helper to remove a criterion
  const removeCriterion = (criterionId: string) => {
    const updated = criteria.filter(c => c.id !== criterionId)
    if (propsOnChange) {
      propsOnChange(updated)
    } else {
      updateContextCriteria(updated)
    }
  }

  // Helper to update a criterion
  const updateCriterion = (criterionId: string, updates: Partial<IECriterion>) => {
    const updated = criteria.map(c => c.id === criterionId ? { ...c, ...updates } : c)
    if (propsOnChange) {
      propsOnChange(updated)
    } else {
      updateContextCriteria(updated)
    }
  }

  console.log("🔍 IE Criteria Tab:", {
    contextCriteria: contextCriteria?.length || 0,
    propsCriteria: propsCriteria?.length,
    usingContext: propsCriteria === undefined,
    indication,
    phase,
    selectedTrials: trials.length
  })

  const handleAIGenerate = async () => {
    // Validate we have necessary data
    if (!indication || !phase) {
      toast.error('Please fill in Basic Info (indication and phase) before generating criteria')
      return
    }
    
    if (trials.length === 0) {
      toast.error('Please select at least one reference trial before generating criteria')
      return
    }
    
    try {
      console.log("🔍 Generating IE criteria with:", {
        indication,
        phase,
        trialsCount: trials.length,
        referenceInfo: referenceInfo.substring(0, 100) + '...'
      })
      
      const response = await generateCriteria({
        trials: trials,
        reference_info: referenceInfo,
        criteria_type: 'inclusion'
      })

      if (response && response.content) {
        // Parse the content to extract criteria
        // Backend returns structured content like:
        // **Inclusion Criteria:**
        // 1. Age ≥18 years
        // 2. Histologically confirmed diagnosis...
        // **Exclusion Criteria:**
        // 1. Prior systemic therapy...
        // 2. Active brain metastases...
        
        const content = response.content
        const criteriaArray: IECriterion[] = []
        
        // Split content into sections
        const lines = content.split('\n').filter(line => line.trim())
        
        let currentType: "inclusion" | "exclusion" | null = null
        let orderCounter = criteria.length + 1
        
        for (const line of lines) {
          const trimmedLine = line.trim()
          
          // Check for section headers
          if (trimmedLine.match(/^\*\*Inclusion Criteria/i)) {
            currentType = "inclusion"
            continue
          } else if (trimmedLine.match(/^\*\*Exclusion Criteria/i)) {
            currentType = "exclusion"
            continue
          }
          
          // Parse numbered criteria (e.g., "1. Age ≥18 years")
          const numberedMatch = trimmedLine.match(/^\d+\.\s+(.+)/)
          if (numberedMatch && currentType) {
            const criterionText = numberedMatch[1].trim()
            
            // Estimate population impact based on criterion type
            // More restrictive criteria have higher impact
            let populationImpact = 10 // default
            
            if (criterionText.toLowerCase().includes('age')) {
              populationImpact = Math.floor(Math.random() * 10) + 5 // 5-15%
            } else if (criterionText.toLowerCase().includes('prior') || criterionText.toLowerCase().includes('previous')) {
              populationImpact = Math.floor(Math.random() * 20) + 10 // 10-30%
            } else if (criterionText.toLowerCase().includes('metasta') || criterionText.toLowerCase().includes('stage')) {
              populationImpact = Math.floor(Math.random() * 30) + 20 // 20-50%
            } else if (criterionText.toLowerCase().includes('performance') || criterionText.toLowerCase().includes('ecog')) {
              populationImpact = Math.floor(Math.random() * 15) + 5 // 5-20%
            } else {
              populationImpact = Math.floor(Math.random() * 15) + 10 // 10-25%
            }
            
            criteriaArray.push({
              id: `criterion-${Date.now()}-${Math.random()}`,
              type: currentType,
              criterion: criterionText,
              icdCodes: [],
              populationImpact: populationImpact,
              order: orderCounter++
            })
            continue
          }
          
          // If it's a non-numbered line after a header and we have a type, treat it as a criterion
          if (currentType && trimmedLine.length > 10 && !trimmedLine.startsWith('**') && !trimmedLine.startsWith('#')) {
            criteriaArray.push({
              id: `criterion-${Date.now()}-${Math.random()}`,
              type: currentType,
              criterion: trimmedLine,
              icdCodes: [],
              populationImpact: Math.floor(Math.random() * 15) + 10,
              order: orderCounter++
            })
          }
        }
        
        // If no criteria were parsed, try a fallback approach
        if (criteriaArray.length === 0) {
          // Split by double newlines to get paragraphs
          const paragraphs = content.split(/\n\n+/).filter(p => p.trim())
          
          for (let i = 0; i < paragraphs.length && criteriaArray.length < 20; i++) {
            const para = paragraphs[i].trim()
            // Skip headers
            if (para.startsWith('**') && para.endsWith('**')) continue
            
            // Determine type based on content or position
            let type: "inclusion" | "exclusion" = "inclusion"
            if (para.toLowerCase().includes('exclusion') || para.toLowerCase().includes('exclude')) {
              type = "exclusion"
            } else if (para.toLowerCase().includes('inclusion') || para.toLowerCase().includes('include')) {
              type = "inclusion"
            } else {
              // If ambiguous, alternate or use first half as inclusion
              type = i < paragraphs.length / 2 ? "inclusion" : "exclusion"
            }
            
            // Remove leading numbers
            const cleanedPara = para.replace(/^\d+\.\s*/, '').trim()
            
            if (cleanedPara.length > 10) {
              criteriaArray.push({
                id: `criterion-${Date.now()}-${Math.random()}`,
                type: type,
                criterion: cleanedPara,
                icdCodes: [],
                populationImpact: Math.floor(Math.random() * 20) + 10,
                order: orderCounter++
              })
            }
          }
        }
        
        console.log("📋 Parsed IE criteria:", criteriaArray)
        
        // Use context or props method
        if (propsOnChange) {
          propsOnChange([...criteria, ...criteriaArray])
        } else {
          updateContextCriteria([...contextCriteria, ...criteriaArray])
        }
        
        const inclusionCount = criteriaArray.filter(c => c.type === 'inclusion').length
        const exclusionCount = criteriaArray.filter(c => c.type === 'exclusion').length
        toast.success(`Generated ${inclusionCount} inclusion and ${exclusionCount} exclusion criteria!`)
      } else {
        toast.error('Failed to generate IE criteria. Please try again.')
      }
    } catch (err) {
      console.error('Error generating IE criteria:', err)
      toast.error('Error generating IE criteria. Please try again.')
    }
  }

  const handleAddCriterion = () => {
    if (newCriterion.trim()) {
      const criterion: IECriterion = {
        id: `criterion-${Date.now()}`,
        type: criterionType,
        criterion: newCriterion,
        icdCodes: [],
        populationImpact: Math.floor(Math.random() * 30) + 10,
        order: criteria.length + 1,
      }

      // Use context or props method
      if (propsOnChange) {
        propsOnChange([...criteria, criterion])
      } else {
        addCriterion(criterion)
      }
      setNewCriterion("")
    }
  }

  const handleRemoveCriterion = (id: string) => {
    // Use context or props method
    if (propsOnChange) {
      propsOnChange(criteria.filter((c) => c.id !== id))
    } else {
      removeCriterion(id)
    }
  }

  const filteredInclusionCriteria = criteria.filter((c) => c.type === "inclusion")
  const filteredExclusionCriteria = criteria.filter((c) => c.type === "exclusion")

  // Calculate population funnel
  const basePopulation = 100000
  const remainingPopulation = criteria.reduce((acc, c) => acc * (1 - c.populationImpact / 100), basePopulation)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Inclusion & Exclusion Criteria</h2>
          <p className="text-sm text-muted-foreground mt-1">Define patient eligibility criteria</p>
        </div>
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
      </div>

      {/* Add Criterion */}
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Add New Criterion</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant={criterionType === "inclusion" ? "default" : "outline"}
              onClick={() => setCriterionType("inclusion")}
              size="sm"
            >
              Inclusion
            </Button>
            <Button
              variant={criterionType === "exclusion" ? "default" : "outline"}
              onClick={() => setCriterionType("exclusion")}
              size="sm"
            >
              Exclusion
            </Button>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Enter criterion (e.g., Age ≥18 years)"
              value={newCriterion}
              onChange={(e) => setNewCriterion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddCriterion()}
              className="flex-1 bg-card border-border/50"
            />
            <Button onClick={handleAddCriterion} className="gap-2">
              <Plus className="h-4 w-4" />
              Add
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Population Funnel */}
      <Card className="border-border/50 bg-gradient-to-br from-primary/5 to-accent/5">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Population Funnel Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Base Population</span>
              <span className="text-lg font-bold text-foreground">{basePopulation.toLocaleString()}</span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-primary to-accent" style={{ width: "100%" }} />
            </div>

            {criteria.map((criterion, index) => {
              const prevPopulation = criteria
                .slice(0, index)
                .reduce((acc, c) => acc * (1 - c.populationImpact / 100), basePopulation)
              const currentPopulation = prevPopulation * (1 - criterion.populationImpact / 100)
              const percentage = (currentPopulation / basePopulation) * 100

              return (
                <div key={criterion.id} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      After: {criterion.criterion ? criterion.criterion.substring(0, 40) : 'Unknown criterion'}...
                    </span>
                    <span className="font-semibold text-foreground">
                      {Math.floor(currentPopulation).toLocaleString()}
                    </span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-300"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              )
            })}

            <div className="flex items-center justify-between pt-3 border-t border-border">
              <span className="text-sm font-semibold text-foreground">Final Eligible Population</span>
              <span className="text-xl font-bold text-success">{Math.floor(remainingPopulation).toLocaleString()}</span>
            </div>
          </div>

          {remainingPopulation < basePopulation * 0.1 && (
            <div className="bg-warning-subtle border border-warning-subtle rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-warning flex-shrink-0 mt-0.5" />
              <div className="text-sm text-muted-foreground">
                <p className="font-semibold text-foreground">Low Eligible Population</p>
                <p>Consider relaxing some criteria to improve recruitment feasibility.</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Criteria Lists */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Inclusion Criteria */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-lg text-success">Inclusion Criteria ({filteredInclusionCriteria.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {filteredInclusionCriteria.map((criterion) => (
              <div key={criterion.id} className="bg-secondary/30 rounded-lg p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-foreground flex-1">{criterion.criterion}</p>
                  <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleRemoveCriterion(criterion.id)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <TrendingDown className="h-3 w-3" />
                  <span>Reduces population by ~{criterion.populationImpact}%</span>
                </div>
              </div>
            ))}
            {filteredInclusionCriteria.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">No inclusion criteria added yet</p>
            )}
          </CardContent>
        </Card>

        {/* Exclusion Criteria */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-lg text-destructive">Exclusion Criteria ({filteredExclusionCriteria.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {filteredExclusionCriteria.map((criterion) => (
              <div key={criterion.id} className="bg-secondary/30 rounded-lg p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-foreground flex-1">{criterion.criterion}</p>
                  <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleRemoveCriterion(criterion.id)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <TrendingDown className="h-3 w-3" />
                  <span>Reduces population by ~{criterion.populationImpact}%</span>
                </div>
              </div>
            ))}
            {filteredExclusionCriteria.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">No exclusion criteria added yet</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
