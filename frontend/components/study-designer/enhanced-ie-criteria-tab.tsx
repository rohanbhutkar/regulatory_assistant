"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import type { IECriterion } from "@/lib/types/study-types"
import { Plus, Trash2, Users, TrendingDown, AlertTriangle, Sparkles, Loader2, CheckCircle2, XCircle, Info, Edit2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"
import { API_CONFIG } from "@/lib/config/api"

interface PopulationFunnel {
  totalPopulation: number
  afterInclusion: number
  afterExclusion: number
  finalEligible: number
  screenFailureRate: number
}

interface CriterionImpact {
  criterionId: string
  estimated

Impact: number // % of population excluded
  patientsAffected: number
  reasoning: string
}

export function EnhancedIECriteriaTab() {
  const {
    inclusionCriteria,
    exclusionCriteria,
    setInclusionCriteria,
    setExclusionCriteria,
    selectedTrials,
    studyContext
  } = useStudyDesigner()
  
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''
  const therapeuticArea = studyContext?.therapeuticArea || ''
  
  const trials = selectedTrials
  const referenceInfo = extractReferenceInfoFromTrials(trials, { indication, phase })
  
  const { generateCriteria, isGenerating } = useProtocolGeneration()
  
  // Local state for editing
  const [editingCriterion, setEditingCriterion] = useState<string | null>(null)
  const [newCriterionText, setNewCriterionText] = useState("")
  const [newCriterionType, setNewCriterionType] = useState<"inclusion" | "exclusion">("inclusion")
  
  // Population funnel state
  const [populationFunnel, setPopulationFunnel] = useState<PopulationFunnel>({
    totalPopulation: 0,
    afterInclusion: 0,
    afterExclusion: 0,
    finalEligible: 0,
    screenFailureRate: 30
  })
  
  // Calculate population funnel based on criteria (including enabled state)
  useEffect(() => {
    calculatePopulationFunnel()
  }, [inclusionCriteria, exclusionCriteria, indication])
  
  // Recalculate relative impacts when criteria change
  useEffect(() => {
    recalculateRelativeImpacts()
  }, [inclusionCriteria, exclusionCriteria, indication, therapeuticArea])
  
  // Update funnel display after relative impacts are calculated
  useEffect(() => {
    // Wait for relative impacts to be calculated, then update funnel display
    if (inclusionCriteria.some(c => c.populationAfter !== undefined) || 
        exclusionCriteria.some(c => c.populationAfter !== undefined)) {
      calculatePopulationFunnel()
    }
  }, [inclusionCriteria.map(c => c.populationAfter).join(','), exclusionCriteria.map(c => c.populationAfter).join(',')])
  
  const calculatePopulationFunnel = () => {
    // Start with the therapeutic area (TA) population
    const taPopulation = getEstimatedPopulation(indication, therapeuticArea)
    
    // Get the last enabled inclusion criterion's populationAfter
    // This represents the population after all inclusion criteria
    const enabledInclusion = inclusionCriteria.filter(c => c.enabled !== false)
    const afterInclusion = enabledInclusion.length > 0 
      ? (enabledInclusion[enabledInclusion.length - 1].populationAfter || taPopulation)
      : taPopulation
    
    // Get the last enabled exclusion criterion's populationAfter
    // This represents the population after all exclusion criteria
    const enabledExclusion = exclusionCriteria.filter(c => c.enabled !== false)
    const afterExclusion = enabledExclusion.length > 0
      ? (enabledExclusion[enabledExclusion.length - 1].populationAfter || afterInclusion)
      : afterInclusion
    
    setPopulationFunnel({
      totalPopulation: taPopulation,
      afterInclusion,
      afterExclusion,
      finalEligible: afterExclusion,
      screenFailureRate: 30
    })
  }
  
  const recalculateRelativeImpacts = () => {
    // Calculate relative impact for each criterion based on population at that point
    // IMPORTANT: Start with the TA population, not full US population
    const taPopulation = getEstimatedPopulation(indication, therapeuticArea)
    let currentPopulation = taPopulation
    
    console.log(`🔄 Recalculating relative impacts starting with TA population: ${taPopulation.toLocaleString()}`)
    
    if (currentPopulation === 0) return // Wait for population to be calculated
    
    // Track enabled criteria seen so far to build context
    const criteriaSeenSoFar: IECriterion[] = []
    
    // Process inclusion criteria in order
    const updatedInclusion = inclusionCriteria.map((criterion) => {
      const isEnabled = criterion.enabled !== false
      const populationBefore = currentPopulation
      
      if (isEnabled) {
        // Build population context from all previous criteria
        const context = getPopulationContext(criteriaSeenSoFar)
        
        // Check if this criterion type should have context-aware adjustment
        const criterionType = detectCriterionType(criterion.text)
        
        let impact = criterion.estimatedImpact || 0.1
        let impactReasoning = criterion.impactReasoning || ""
        
        // Apply context-aware adjustment if applicable
        if (criterionType) {
          const adjusted = adjustImpactForContext(impact, criterionType, context)
          impact = adjusted.impact
          impactReasoning = adjusted.reasoning
          
          console.log(`🎯 Context-aware adjustment for "${criterion.text.substring(0, 50)}..."`)
          console.log(`   Context:`, context)
          console.log(`   Base impact: ${(criterion.estimatedImpact || 0.1) * 100}%`)
          console.log(`   Adjusted impact: ${impact * 100}%`)
          console.log(`   Reasoning: ${impactReasoning}`)
        }
        
        const populationAfter = Math.round(currentPopulation * (1 - impact))
        const patientsAffected = populationBefore - populationAfter
        
        currentPopulation = populationAfter
        
        // Add this criterion to the context for future criteria
        criteriaSeenSoFar.push(criterion)
        
        return {
          ...criterion,
          relativeImpact: impact,
          populationBefore,
          populationAfter,
          patientsAffected,
          impactReasoning // Update with context-aware reasoning
        }
      } else {
        return {
          ...criterion,
          relativeImpact: criterion.estimatedImpact || 0,
          populationBefore,
          populationAfter: currentPopulation,
          patientsAffected: 0
        }
      }
    })
    
    // Process exclusion criteria in order (continue building context)
    const updatedExclusion = exclusionCriteria.map((criterion) => {
      const isEnabled = criterion.enabled !== false
      const populationBefore = currentPopulation
      
      if (isEnabled) {
        // Build population context from all previous criteria (inclusion + exclusion)
        const context = getPopulationContext(criteriaSeenSoFar)
        
        // Check if this criterion type should have context-aware adjustment
        const criterionType = detectCriterionType(criterion.text)
        
        let impact = criterion.estimatedImpact || 0.05
        let impactReasoning = criterion.impactReasoning || ""
        
        // Apply context-aware adjustment if applicable
        if (criterionType) {
          const adjusted = adjustImpactForContext(impact, criterionType, context)
          impact = adjusted.impact
          impactReasoning = adjusted.reasoning
          
          console.log(`🎯 Context-aware adjustment for "${criterion.text.substring(0, 50)}..."`)
          console.log(`   Context:`, context)
          console.log(`   Base impact: ${(criterion.estimatedImpact || 0.05) * 100}%`)
          console.log(`   Adjusted impact: ${impact * 100}%`)
          console.log(`   Reasoning: ${impactReasoning}`)
        }
        
        const populationAfter = Math.round(currentPopulation * (1 - impact))
        const patientsAffected = populationBefore - populationAfter
        
        currentPopulation = populationAfter
        
        // Add this criterion to the context for future criteria
        criteriaSeenSoFar.push(criterion)
        
        return {
          ...criterion,
          relativeImpact: impact,
          populationBefore,
          populationAfter,
          patientsAffected,
          impactReasoning // Update with context-aware reasoning
        }
      } else {
        return {
          ...criterion,
          relativeImpact: criterion.estimatedImpact || 0,
          populationBefore,
          populationAfter: currentPopulation,
          patientsAffected: 0
        }
      }
    })
    
    // Only update if there are changes to avoid infinite loops
    const hasInclusionChanges = updatedInclusion.some((c, i) => 
      c.relativeImpact !== inclusionCriteria[i]?.relativeImpact ||
      c.populationBefore !== inclusionCriteria[i]?.populationBefore ||
      c.populationAfter !== inclusionCriteria[i]?.populationAfter
    )
    
    const hasExclusionChanges = updatedExclusion.some((c, i) => 
      c.relativeImpact !== exclusionCriteria[i]?.relativeImpact ||
      c.populationBefore !== exclusionCriteria[i]?.populationBefore ||
      c.populationAfter !== exclusionCriteria[i]?.populationAfter
    )
    
    if (hasInclusionChanges) {
      setInclusionCriteria(updatedInclusion)
    }
    if (hasExclusionChanges) {
      setExclusionCriteria(updatedExclusion)
    }
  }
  
  const toggleCriterion = (id: string, type: "inclusion" | "exclusion") => {
    if (type === 'inclusion') {
      setInclusionCriteria(inclusionCriteria.map(c => 
        c.id === id ? { ...c, enabled: !(c.enabled !== false) } : c
      ))
    } else {
      setExclusionCriteria(exclusionCriteria.map(c => 
        c.id === id ? { ...c, enabled: !(c.enabled !== false) } : c
      ))
    }
    toast.success('Criterion toggled')
  }
  
  const getEstimatedPopulation = (indication: string, therapeuticArea: string): number => {
    // US population extrapolated estimates based on prevalence data
    // These represent the THERAPEUTIC AREA population with the condition, not full US population
    
    if (!indication || indication.trim() === '') {
      console.warn('⚠️ No indication provided, using generic estimate')
      return 1000000
    }
    
    const lowerIndication = indication.toLowerCase().trim()
    console.log(`📊 Estimating population for indication: "${lowerIndication}"`)
    
    // Pattern matching for better detection
    if (lowerIndication.includes('nsclc') || lowerIndication.includes('non-small cell lung') || lowerIndication.includes('non small cell lung')) {
      console.log(`✅ Matched NSCLC → 541,000 US patients`)
      return 541000  // ~541K incident NSCLC cases per year in US
    }
    if (lowerIndication.includes('lung cancer') || lowerIndication.includes('lung carcinoma')) {
      return 541000
    }
    if (lowerIndication.includes('melanoma')) {
      return 200000  // ~200K incident melanoma cases per year in US
    }
    if (lowerIndication.includes('breast cancer') || lowerIndication.includes('breast carcinoma')) {
      return 300000  // ~300K incident breast cancer cases per year in US
    }
    if (lowerIndication.includes('diabetes') || lowerIndication.includes('dm') || lowerIndication.includes('t2d')) {
      return 37300000  // ~37.3M adults with diabetes in US
    }
    if (lowerIndication.includes('heart failure') || lowerIndication.includes('hf')) {
      return 6500000  // ~6.5M adults with heart failure in US
    }
    
    // Fallback: try to estimate from therapeutic area
    const lowerTA = therapeuticArea.toLowerCase()
    if (lowerTA.includes('oncology') || lowerTA.includes('cancer')) {
      return 2000000  // ~2M cancer patients as generic oncology estimate
    }
    if (lowerTA.includes('cardio')) {
      return 6500000  // ~6.5M cardiovascular patients
    }
    if (lowerTA.includes('metabolic') || lowerTA.includes('endocrin')) {
      return 37300000  // ~37M metabolic patients
    }
    
    // Last resort: return a reasonable clinical trial population, not full US population
    console.warn(`⚠️ Could not match indication "${indication}" to known population. Using generic estimate of 1M.`)
    return 1000000  // 1M patients as reasonable generic estimate
  }
  
  const handleAIGenerate = async () => {
    if (!indication || !phase) {
      toast.error('Please fill in Basic Info (indication and phase) before generating criteria')
      return
    }
    
    if (trials.length === 0) {
      toast.error('Please select at least one reference trial before generating criteria')
      return
    }
    
    try {
      console.log('🔬 Generating IE criteria...')
      const response = await generateCriteria({
        trials: trials,
        reference_info: referenceInfo,
        criteria_type: 'inclusion' // API now generates both
      })
      
      if (response && response.content) {
        console.log('📥 Received content:', response.content.length, 'characters')
        console.log('📄 First 500 chars:', response.content.substring(0, 500))
        
        // Check for both section headers
        const hasInclusion = response.content.match(/\*\*Inclusion Criteria/i)
        const hasExclusion = response.content.match(/\*\*Exclusion Criteria/i)
        console.log('🔍 Content analysis:', { hasInclusion: !!hasInclusion, hasExclusion: !!hasExclusion })
        
        const { inclusion, exclusion } = parseIECriteria(response.content)
        
        console.log('✅ Parsed results:', { 
          inclusionCount: inclusion.length, 
          exclusionCount: exclusion.length 
        })
        
        // Enrich with claims data
        console.log('🔍 Enriching criteria with claims data...')
        const enrichedInclusion = await enrichCriteriaWithClaims(inclusion)
        const enrichedExclusion = await enrichCriteriaWithClaims(exclusion)
        
        if (enrichedInclusion.length > 0) {
          setInclusionCriteria(enrichedInclusion)
          toast.success(`Generated ${enrichedInclusion.length} inclusion criteria`)
        }
        
        if (enrichedExclusion.length > 0) {
          setExclusionCriteria(enrichedExclusion)
          toast.success(`Generated ${enrichedExclusion.length} exclusion criteria`)
        }
        
        if (inclusion.length === 0 && exclusion.length === 0) {
          console.error('❌ Parser returned empty arrays')
          console.log('Full content:', response.content)
          toast.error('No criteria could be parsed from response')
        }
      }
    } catch (err) {
      console.error('❌ Error generating criteria:', err)
      toast.error('Failed to generate criteria')
    }
  }
  
  const enrichCriteriaWithClaims = async (criteria: IECriterion[]): Promise<IECriterion[]> => {
    const enriched = await Promise.all(
      criteria.map(async (criterion) => {
        if (criterion.primaryICD) {
          const claimsData = await fetchClaimsDataForICD(criterion.primaryICD, criterion.text)
          if (claimsData) {
            console.log(`✅ Claims data for ${criterion.primaryICD}:`, claimsData.estimated_us_patients, 'patients')
            return {
              ...criterion,
              estimatedImpact: claimsData.impact_percentage,
              impactReasoning: claimsData.reasoning,
              icdDescription: claimsData.description,
              patientsAffected: claimsData.estimated_us_patients
            }
          }
        }
        return criterion
      })
    )
    return enriched
  }
  
  const parseIECriteria = (content: string): { inclusion: IECriterion[], exclusion: IECriterion[] } => {
    const inclusion: IECriterion[] = []
    const exclusion: IECriterion[] = []
    
    const lines = content.split('\n').filter(line => line.trim())
    let currentType: "inclusion" | "exclusion" | null = null
    let orderCounter = 1
    
    for (const line of lines) {
      const trimmed = line.trim()
      
      // Detect section headers
      if (trimmed.match(/^\*\*Inclusion Criteria/i)) {
        currentType = "inclusion"
        orderCounter = 1
        continue
      }
      if (trimmed.match(/^\*\*Exclusion Criteria/i)) {
        currentType = "exclusion"
        orderCounter = 1
        continue
      }
      
      // Parse numbered criteria
      const match = trimmed.match(/^\d+\.\s+(.+)/)
      if (match && currentType) {
        const text = match[1].trim()
        
        // Estimate impact based on criterion type and content
        const impactData = estimateImpact(text, currentType)
        
        const criterion: IECriterion = {
          id: `${currentType}-${Date.now()}-${orderCounter}`,
          type: currentType,
          text: text,
          order: orderCounter,
          estimatedImpact: impactData.impact,
          impactReasoning: impactData.reasoning,
          primaryICD: impactData.primaryICD,
          icdDescription: impactData.icdDescription,
          icdCodes: extractICDCodes(text)
        }
        
        if (currentType === "inclusion") {
          inclusion.push(criterion)
        } else {
          exclusion.push(criterion)
        }
        
        orderCounter++
      }
    }
    
    return { inclusion, exclusion }
  }
  
  // Cache for claims-based ICD data
  const [icdDataCache, setIcdDataCache] = useState<Record<string, any>>({})
  
  const fetchClaimsDataForICD = async (icdCode: string, criterionText: string): Promise<any> => {
    // Check cache first
    if (icdDataCache[icdCode]) {
      return icdDataCache[icdCode]
    }
    
    try {
      const response = await fetch(`${API_CONFIG.baseURL}/api/data/icd-population-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          icd_codes: [icdCode],
          criterion_text: criterionText
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.results && data.results.length > 0) {
          const result = data.results[0]
          // Cache the result
          // NOTE: Backend already extrapolates from claims sample (15%) to full US population (330M)
          // result.estimated_us_patients is the extrapolated number
          setIcdDataCache(prev => ({ ...prev, [icdCode]: result }))
          return result
        }
      }
    } catch (error) {
      console.log('⚠️ Claims data not available, using estimates:', error)
    }
    
    return null
  }
  
  // Context-aware impact adjustment based on population characteristics
  const getPopulationContext = (currentCriteria: IECriterion[]): {
    hasCancerDiagnosis: boolean
    hasMetastaticDisease: boolean
    hasPriorTherapy: boolean
    hasBiomarkerSelection: boolean
    cancerType?: string
  } => {
    const context = {
      hasCancerDiagnosis: false,
      hasMetastaticDisease: false,
      hasPriorTherapy: false,
      hasBiomarkerSelection: false,
      cancerType: undefined as string | undefined
    }
    
    currentCriteria.forEach(c => {
      const text = c.text.toLowerCase()
      
      // Cancer diagnosis
      if (text.includes('nsclc') || text.includes('lung cancer') || 
          text.includes('breast cancer') || text.includes('melanoma') ||
          text.includes('carcinoma') || text.includes('sarcoma')) {
        context.hasCancerDiagnosis = true
        
        if (text.includes('nsclc') || text.includes('lung cancer')) context.cancerType = 'lung'
        else if (text.includes('breast')) context.cancerType = 'breast'
        else if (text.includes('melanoma')) context.cancerType = 'melanoma'
      }
      
      // Metastatic disease
      if (text.includes('metastatic') || text.includes('stage iv') || 
          text.includes('advanced') || text.includes('locally advanced')) {
        context.hasMetastaticDisease = true
      }
      
      // Prior therapy
      if (text.includes('prior therapy') || text.includes('previous treatment') ||
          text.includes('second-line') || text.includes('2l') || text.includes('relapsed')) {
        context.hasPriorTherapy = true
      }
      
      // Biomarker selection
      if (text.includes('pd-l1') || text.includes('egfr') || text.includes('alk') ||
          text.includes('biomarker') || text.includes('mutation')) {
        context.hasBiomarkerSelection = true
      }
    })
    
    return context
  }
  
  const adjustImpactForContext = (
    baseImpact: number, 
    criterionType: string,
    context: ReturnType<typeof getPopulationContext>
  ): { impact: number; reasoning: string } => {
    let adjustedImpact = baseImpact
    let adjustmentReason = ""
    
    // ECOG Performance Status adjustments
    if (criterionType === 'ecog') {
      if (context.hasCancerDiagnosis && context.hasMetastaticDisease && context.hasPriorTherapy) {
        // 2L+ metastatic cancer: Much worse performance status
        adjustedImpact = 0.60  // 60% have ECOG 2+
        adjustmentReason = "In 2L+ metastatic cancer population, 60% have ECOG 2+ (disease progression)"
      } else if (context.hasCancerDiagnosis && context.hasMetastaticDisease) {
        // 1L metastatic cancer: Moderately worse
        adjustedImpact = 0.40  // 40% have ECOG 2+
        adjustmentReason = "In metastatic cancer population, 40% have ECOG 2+"
      } else if (context.hasCancerDiagnosis) {
        // Any cancer diagnosis: Slightly worse
        adjustedImpact = 0.20  // 20% have ECOG 2+
        adjustmentReason = "In cancer population, 20% have ECOG 2+"
      } else {
        // General population
        adjustedImpact = 0.10  // 10% have ECOG 2+
        adjustmentReason = "In general population, 10% have ECOG 2+"
      }
    }
    
    // Prior therapy / Treatment-naive adjustments
    else if (criterionType === 'prior_therapy') {
      if (context.hasMetastaticDisease && context.cancerType === 'lung') {
        // Metastatic lung cancer: Most have had treatment
        adjustedImpact = 0.85  // 85% have had prior therapy
        adjustmentReason = "In metastatic lung cancer, 85% have received prior therapy"
      } else if (context.hasMetastaticDisease) {
        // Other metastatic cancers
        adjustedImpact = 0.75  // 75% have had prior therapy
        adjustmentReason = "In metastatic cancer population, 75% have received prior therapy"
      } else if (context.hasCancerDiagnosis) {
        // Early stage cancer
        adjustedImpact = 0.45  // 45% have had prior therapy
        adjustmentReason = "In cancer population, 45% have received prior therapy"
      } else {
        // General population
        adjustedImpact = 0.02  // 2% have had cancer therapy
        adjustmentReason = "In general population, only 2% have received cancer therapy"
      }
    }
    
    // Brain metastases adjustments
    else if (criterionType === 'brain_mets') {
      if (context.hasMetastaticDisease && context.cancerType === 'lung') {
        // Metastatic lung cancer: High rate of brain mets
        adjustedImpact = 0.25  // 25% have brain mets
        adjustmentReason = "In metastatic lung cancer, 25% have brain metastases"
      } else if (context.hasMetastaticDisease && context.cancerType === 'melanoma') {
        // Metastatic melanoma: Very high rate
        adjustedImpact = 0.40  // 40% have brain mets
        adjustmentReason = "In metastatic melanoma, 40% have brain metastases"
      } else if (context.hasMetastaticDisease) {
        // Other metastatic cancers
        adjustedImpact = 0.15  // 15% have brain mets
        adjustmentReason = "In metastatic cancer, 15% have brain metastases"
      } else {
        // Non-metastatic or general population
        adjustedImpact = 0.01  // 1% have brain mets
        adjustmentReason = "In non-metastatic population, <1% have brain metastases"
      }
    }
    
    // Biomarker prevalence adjustments
    else if (criterionType === 'pd_l1') {
      if (context.hasCancerDiagnosis && context.cancerType === 'lung') {
        // NSCLC: Well-characterized PD-L1 prevalence
        adjustedImpact = 0.50  // 50% have PD-L1 ≥50%
        adjustmentReason = "In NSCLC population, ~50% have PD-L1 ≥50%"
      } else if (context.hasCancerDiagnosis) {
        // Other cancers: Variable
        adjustedImpact = 0.30  // 30% have high PD-L1
        adjustmentReason = "In cancer population, ~30% have high PD-L1 expression"
      }
    }
    
    // Organ function (renal/hepatic) adjustments
    else if (criterionType === 'organ_function') {
      if (context.hasPriorTherapy && context.hasMetastaticDisease) {
        // Prior chemo + metastatic: Higher rate of organ dysfunction
        adjustedImpact = 0.25  // 25% have organ dysfunction
        adjustmentReason = "In heavily pre-treated metastatic population, 25% have organ dysfunction"
      } else if (context.hasCancerDiagnosis && context.hasMetastaticDisease) {
        // Metastatic cancer: Moderate rate
        adjustedImpact = 0.15  // 15% have organ dysfunction
        adjustmentReason = "In metastatic cancer population, 15% have organ dysfunction"
      } else if (context.hasCancerDiagnosis) {
        // Cancer diagnosis: Slight increase
        adjustedImpact = 0.10  // 10% have organ dysfunction
        adjustmentReason = "In cancer population, 10% have organ dysfunction"
      }
    }
    
    return { impact: adjustedImpact, reasoning: adjustmentReason }
  }
  
  const detectCriterionType = (text: string): string | null => {
    const lowerText = text.toLowerCase()
    
    if (lowerText.includes('ecog') || lowerText.includes('performance status')) return 'ecog'
    if (lowerText.includes('prior therapy') || lowerText.includes('treatment-naive') || 
        lowerText.includes('previous treatment') || lowerText.includes('first-line') ||
        lowerText.includes('untreated')) return 'prior_therapy'
    if (lowerText.includes('brain') && lowerText.includes('met')) return 'brain_mets'
    if (lowerText.includes('pd-l1')) return 'pd_l1'
    if (lowerText.includes('renal') || lowerText.includes('hepatic') || 
        lowerText.includes('creatinine') || lowerText.includes('bilirubin') ||
        lowerText.includes('alt') || lowerText.includes('ast')) return 'organ_function'
    
    return null
  }
  
  const estimateImpact = (text: string, type: "inclusion" | "exclusion"): { 
    impact: number
    reasoning: string
    primaryICD?: string
    icdDescription?: string
  } => {
    const lowerText = text.toLowerCase()
    
    // IMPORTANT: Check most specific patterns FIRST, then fall back to generic ones
    
    // ===== CANCER TYPES & DIAGNOSES =====
    
    // Non-Small Cell Lung Cancer (NSCLC)
    if (lowerText.includes('non-small cell lung') || lowerText.includes('nsclc')) {
      return {
        impact: 0.85,
        reasoning: 'NSCLC represents ~85% of all lung cancer diagnoses',
        primaryICD: 'C34.90',
        icdDescription: 'Non-small cell lung cancer, unspecified'
      }
    }
    
    // Small Cell Lung Cancer
    if (lowerText.includes('small cell lung') || lowerText.includes('sclc')) {
      return {
        impact: 0.15,
        reasoning: 'SCLC represents ~15% of lung cancer diagnoses',
        primaryICD: 'C34.91',
        icdDescription: 'Small cell lung cancer'
      }
    }
    
    // Melanoma
    if (lowerText.includes('melanoma')) {
      return {
        impact: 0.90,
        reasoning: 'Melanoma diagnosis criterion applies to primary disease population',
        primaryICD: 'C43.9',
        icdDescription: 'Malignant melanoma, unspecified'
      }
    }
    
    // Breast Cancer
    if (lowerText.includes('breast cancer') || lowerText.includes('breast carcinoma')) {
      return {
        impact: 0.90,
        reasoning: 'Breast cancer diagnosis criterion applies to primary disease population',
        primaryICD: 'C50.9',
        icdDescription: 'Malignant neoplasm of breast, unspecified'
      }
    }
    
    // Colorectal Cancer
    if (lowerText.includes('colorectal') || lowerText.includes('colon cancer')) {
      return {
        impact: 0.90,
        reasoning: 'Colorectal cancer diagnosis applies to primary disease population',
        primaryICD: 'C18.9',
        icdDescription: 'Malignant neoplasm of colon, unspecified'
      }
    }
    
    // ===== METASTASES (Check before "untreated" keyword) =====
    
    // Brain Metastases (must check BEFORE "untreated" pattern)
    if (lowerText.includes('brain') && (lowerText.includes('metasta') || lowerText.includes('mets'))) {
      return {
        impact: 0.15,
        reasoning: 'Brain metastases present in ~15% of advanced cancer patients',
        primaryICD: 'C79.31',
        icdDescription: 'Secondary malignant neoplasm of brain'
      }
    }
    
    // Liver Metastases
    if (lowerText.includes('liver') && (lowerText.includes('metasta') || lowerText.includes('mets'))) {
      return {
        impact: 0.30,
        reasoning: 'Liver metastases present in ~30% of advanced cancer patients',
        primaryICD: 'C78.7',
        icdDescription: 'Secondary malignant neoplasm of liver'
      }
    }
    
    // Bone Metastases
    if (lowerText.includes('bone') && (lowerText.includes('metasta') || lowerText.includes('mets'))) {
      return {
        impact: 0.25,
        reasoning: 'Bone metastases present in ~25% of advanced cancer patients',
        primaryICD: 'C79.51',
        icdDescription: 'Secondary malignant neoplasm of bone'
      }
    }
    
    // Leptomeningeal Disease
    if (lowerText.includes('leptomeningeal')) {
      return {
        impact: 0.05,
        reasoning: 'Leptomeningeal disease affects ~5% of advanced cancer patients',
        primaryICD: 'C79.32',
        icdDescription: 'Secondary malignant neoplasm of meninges'
      }
    }
    
    // General Metastatic/Advanced Disease
    if ((lowerText.includes('metastatic') || lowerText.includes('advanced') || lowerText.includes('recurrent')) && 
        (lowerText.includes('cancer') || lowerText.includes('disease') || lowerText.includes('nsclc'))) {
      return {
        impact: 0.40,
        reasoning: 'Metastatic/advanced disease represents ~40% of cancer population at any time',
        primaryICD: 'C79.9',
        icdDescription: 'Secondary malignant neoplasm, unspecified site'
      }
    }
    
    // ===== AGE RESTRICTIONS =====
    
    if (lowerText.includes('age') && lowerText.includes('18')) {
      return {
        impact: 0.05,
        reasoning: 'Age ≥18 requirement excludes <5% of adult population',
        primaryICD: 'Z00.00',
        icdDescription: 'General adult population'
      }
    }
    if (lowerText.includes('age') && lowerText.includes('65')) {
      return {
        impact: 0.15,
        reasoning: 'Age restriction excludes ~15% of patients over 65',
        primaryICD: 'Z00.00',
        icdDescription: 'Elderly population restriction'
      }
    }
    
    // Biomarkers
    if (lowerText.includes('pd-l1')) {
      return {
        impact: 0.50,
        reasoning: 'PD-L1 positive patients represent ~50% of tested population',
        primaryICD: 'C79.9',
        icdDescription: 'Biomarker-positive subset'
      }
    }
    if (lowerText.includes('egfr') || lowerText.includes('mutation')) {
      return {
        impact: 0.15,
        reasoning: 'EGFR mutations found in ~15% of lung cancer patients',
        primaryICD: 'C34.9',
        icdDescription: 'EGFR+ NSCLC subset'
      }
    }
    if (lowerText.includes('biomarker')) {
      return {
        impact: 0.40,
        reasoning: 'Biomarker requirement typically excludes ~40% of patients',
        primaryICD: 'C79.9',
        icdDescription: 'Biomarker screening requirement'
      }
    }
    
    // ===== MEASURABLE DISEASE (RECIST) =====
    
    if (lowerText.includes('measurable') && (lowerText.includes('recist') || lowerText.includes('disease'))) {
      return {
        impact: 0.70,
        reasoning: 'Measurable disease per RECIST applies to ~70% of patients with solid tumors',
        primaryICD: 'C80.1',
        icdDescription: 'Malignant neoplasm with measurable disease'
      }
    }
    
    // ===== HISTOLOGICAL/CYTOLOGICAL CONFIRMATION =====
    
    if (lowerText.includes('histolog') || lowerText.includes('cytolog')) {
      return {
        impact: 0.95,
        reasoning: 'Tissue confirmation is standard for most patients; ~95% have pathology documentation',
        primaryICD: 'R89.7',
        icdDescription: 'Abnormal histological findings'
      }
    }
    
    // ===== LABORATORY VALUES =====
    
    // Hematologic Function
    if (lowerText.includes('neutrophil') || lowerText.includes('platelet') || lowerText.includes('hemoglobin') || 
        (lowerText.includes('hematologic') && lowerText.includes('function'))) {
      return {
        impact: 0.12,
        reasoning: 'Hematologic dysfunction affects ~12% of cancer patients at screening',
        primaryICD: 'D75.9',
        icdDescription: 'Hematologic function requirement'
      }
    }
    
    // Hepatic Function
    if ((lowerText.includes('hepatic') || lowerText.includes('bilirubin') || lowerText.includes('ast') || lowerText.includes('alt')) &&
        lowerText.includes('function')) {
      return {
        impact: 0.10,
        reasoning: 'Hepatic impairment affects ~10% of patient population',
        primaryICD: 'K76.9',
        icdDescription: 'Adequate hepatic function requirement'
      }
    }
    
    // Renal Function
    if ((lowerText.includes('renal') || lowerText.includes('creatinine') || lowerText.includes('kidney')) && 
        lowerText.includes('function')) {
      return {
        impact: 0.15,
        reasoning: 'Renal impairment affects ~15% of patient population',
        primaryICD: 'N18.9',
        icdDescription: 'Adequate renal function requirement'
      }
    }
    
    // ===== AUTOIMMUNE & IMMUNOSUPPRESSION =====
    
    if (lowerText.includes('autoimmune')) {
      return {
        impact: 0.08,
        reasoning: 'Active autoimmune disease affects ~8% of general population',
        primaryICD: 'M35.9',
        icdDescription: 'Autoimmune disease, unspecified'
      }
    }
    
    if (lowerText.includes('immunosuppress')) {
      return {
        impact: 0.10,
        reasoning: 'Systemic immunosuppression requirement excludes ~10% of patients',
        primaryICD: 'D84.9',
        icdDescription: 'Immunodeficiency/immunosuppression'
      }
    }
    
    // ===== CARDIAC CONDITIONS =====
    
    if (lowerText.includes('cardiac') || lowerText.includes('myocardial') || lowerText.includes('heart failure') || 
        lowerText.includes('unstable angina')) {
      return {
        impact: 0.12,
        reasoning: 'Significant cardiac disease affects ~12% of cancer patient population',
        primaryICD: 'I51.9',
        icdDescription: 'Cardiac disease, unspecified'
      }
    }
    
    // ===== OTHER MALIGNANCIES =====
    
    if (lowerText.includes('another') && lowerText.includes('malignancy')) {
      return {
        impact: 0.10,
        reasoning: 'History of other primary malignancies affects ~10% of cancer patients',
        primaryICD: 'Z85.9',
        icdDescription: 'Personal history of malignant neoplasm'
      }
    }
    
    // ===== HYPERSENSITIVITY =====
    
    if (lowerText.includes('hypersensitivity') || lowerText.includes('severe allerg')) {
      return {
        impact: 0.05,
        reasoning: 'Severe hypersensitivity reactions affect ~5% of patients',
        primaryICD: 'T78.40',
        icdDescription: 'Allergy, unspecified'
      }
    }
    
    // ===== PRIOR THERAPY (Check AFTER brain metastases) =====
    
    if ((lowerText.includes('prior') && (lowerText.includes('therapy') || lowerText.includes('treatment'))) ||
        lowerText.includes('anticancer')) {
      return {
        impact: type === 'inclusion' ? 0.60 : 0.20,
        reasoning: type === 'inclusion' 
          ? 'Prior therapy requirement limits to ~40% with treatment history'
          : 'Excludes ~20% with specific prior treatments',
        primaryICD: 'Z92.21',
        icdDescription: 'History of antineoplastic therapy'
      }
    }
    
    if (lowerText.includes('treatment-naive') || 
        (lowerText.includes('untreated') && !lowerText.includes('brain'))) {
      return {
        impact: 0.50,
        reasoning: 'Treatment-naive requirement limits to ~50% of newly diagnosed',
        primaryICD: 'Z92.21',
        icdDescription: 'No prior systemic therapy'
      }
    }
    
    // ===== TRANSPLANTATION =====
    
    if (lowerText.includes('transplant')) {
      return {
        impact: 0.02,
        reasoning: 'Prior transplantation affects ~2% of patient population',
        primaryICD: 'Z94.9',
        icdDescription: 'History of transplantation'
      }
    }
    
    // ===== SURGICAL PROCEDURE =====
    
    if (lowerText.includes('surgery') || lowerText.includes('surgical')) {
      return {
        impact: 0.08,
        reasoning: 'Recent major surgery affects ~8% at screening',
        primaryICD: 'Z98.89',
        icdDescription: 'Post-surgical status'
      }
    }
    
    // ===== BLEEDING/ANTICOAGULATION =====
    
    if (lowerText.includes('bleeding') || lowerText.includes('anticoagul')) {
      return {
        impact: 0.10,
        reasoning: 'Bleeding disorders or anticoagulation affects ~10% of patients',
        primaryICD: 'D68.9',
        icdDescription: 'Coagulation defect, unspecified'
      }
    }
    
    // ===== PULMONARY DISEASE =====
    
    if (lowerText.includes('pulmonary') && (lowerText.includes('disease') || lowerText.includes('oxygen'))) {
      return {
        impact: 0.08,
        reasoning: 'Significant pulmonary disease affects ~8% of patients',
        primaryICD: 'J98.9',
        icdDescription: 'Respiratory disorder, unspecified'
      }
    }
    
    // ===== LIFE EXPECTANCY =====
    
    if (lowerText.includes('life expectancy')) {
      return {
        impact: 0.10,
        reasoning: 'Life expectancy requirements exclude ~10% with advanced disease',
        primaryICD: 'R69',
        icdDescription: 'Life expectancy assessment'
      }
    }
    
    // ===== INFORMED CONSENT & COMPLIANCE =====
    
    if (lowerText.includes('informed consent') || lowerText.includes('comply')) {
      return {
        impact: 0.02,
        reasoning: 'Informed consent/compliance issues affect <2% of otherwise eligible patients',
        primaryICD: 'Z71.89',
        icdDescription: 'Patient counseling and informed consent'
      }
    }
    
    // ===== GASTROINTESTINAL =====
    
    if (lowerText.includes('swallow') || lowerText.includes('gastrointestinal')) {
      return {
        impact: 0.05,
        reasoning: 'GI disorders affecting drug absorption present in ~5% of patients',
        primaryICD: 'K92.9',
        icdDescription: 'Gastrointestinal disorder'
      }
    }
    
    // ===== PERFORMANCE STATUS (if not caught above) =====
    
    if (lowerText.includes('ecog') || lowerText.includes('performance status')) {
      if (lowerText.includes('0-1') || lowerText.includes('0 or 1')) {
        return {
          impact: 0.30,
          reasoning: 'ECOG 0-1 represents ~70% of ambulatory patients',
          primaryICD: 'R53.1',
          icdDescription: 'Good performance status (ECOG 0-1)'
        }
      }
      if (lowerText.includes('2') || lowerText.includes('>2')) {
        return {
          impact: 0.15,
          reasoning: 'ECOG 2+ represents ~15% of symptomatic patients',
          primaryICD: 'R53.1',
          icdDescription: 'Limited performance status'
        }
      }
    }
    
    // ===== TYPE 1 DIABETES (for T2D studies) =====
    
    if (lowerText.includes('type 1') && lowerText.includes('diabetes')) {
      return {
        impact: 0.08,
        reasoning: 'Type 1 diabetes represents ~8% of all diabetes patients',
        primaryICD: 'E10.9',
        icdDescription: 'Type 1 diabetes mellitus'
      }
    }
    
    // ===== INFECTION (if not caught by HIV/Hepatitis) =====
    
    if (lowerText.includes('infection') || lowerText.includes('inflammatory')) {
      return {
        impact: 0.12,
        reasoning: 'Active infection/inflammation affects ~12% at screening',
        primaryICD: 'A49.9',
        icdDescription: 'Bacterial infection, unspecified'
      }
    }
    
    // ===== PREGNANCY/CONTRACEPTION =====
    
    if (lowerText.includes('pregnan') || lowerText.includes('breastfeed') || lowerText.includes('lactating') ||
        (lowerText.includes('women') && lowerText.includes('childbearing'))) {
      return {
        impact: 0.03,
        reasoning: 'Pregnancy/lactation affects ~3% of women of childbearing age',
        primaryICD: 'Z33.1',
        icdDescription: 'Pregnancy/childbearing considerations'
      }
    }
    
    // ===== CONTRACEPTION FOR MEN =====
    
    if (lowerText.includes('men') && lowerText.includes('contraception')) {
      return {
        impact: 0.02,
        reasoning: 'Male contraception requirements affect ~2% due to compliance',
        primaryICD: 'Z71.89',
        icdDescription: 'Contraception counseling for men'
      }
    }
    
    // ===== HIV/HEPATITIS =====
    
    if (lowerText.includes('hiv') || lowerText.includes('hepatitis')) {
      return {
        impact: 0.05,
        reasoning: 'HIV/Hepatitis affects ~5% of general population',
        primaryICD: 'B20',
        icdDescription: 'HIV/Hepatitis infection'
      }
    }
    
    // ===== PSYCHIATRIC CONDITIONS =====
    
    if (lowerText.includes('psychiatric') || lowerText.includes('mental')) {
      return {
        impact: 0.08,
        reasoning: 'Psychiatric conditions affecting compliance present in ~8% of patients',
        primaryICD: 'F99',
        icdDescription: 'Mental disorder, unspecified'
      }
    }
    
    // ===== DEFAULT FALLBACK =====
    return {
      impact: type === 'inclusion' ? 0.15 : 0.08,
      reasoning: type === 'inclusion' 
        ? 'Standard inclusion criterion, affects ~15% of population'
        : 'Standard exclusion criterion, excludes ~8% of population',
      primaryICD: undefined,
      icdDescription: 'General eligibility requirement'
    }
  }
  
  const extractICDCodes = (text: string): string[] => {
    // Extract ICD codes from text (simplified)
    const icdPattern = /\b[A-Z]\d{2}(?:\.\d{1,2})?\b/g
    return text.match(icdPattern) || []
  }
  
  const addCriterion = async () => {
    if (!newCriterionText.trim()) return
    
    const impactData = estimateImpact(newCriterionText, newCriterionType)
    
    let criterion: IECriterion = {
      id: `${newCriterionType}-${Date.now()}`,
      type: newCriterionType,
      text: newCriterionText,
      order: (newCriterionType === 'inclusion' ? inclusionCriteria.length : exclusionCriteria.length) + 1,
      estimatedImpact: impactData.impact,
      impactReasoning: impactData.reasoning,
      primaryICD: impactData.primaryICD,
      icdDescription: impactData.icdDescription,
      icdCodes: extractICDCodes(newCriterionText)
    }
    
    // Enrich with real claims data if ICD code is available
    if (impactData.primaryICD) {
      const claimsData = await fetchClaimsDataForICD(impactData.primaryICD, newCriterionText)
      if (claimsData) {
        console.log('✅ Using claims data for', impactData.primaryICD, claimsData)
        criterion = {
          ...criterion,
          estimatedImpact: claimsData.impact_percentage,
          impactReasoning: claimsData.reasoning,
          icdDescription: claimsData.description,
          patientsAffected: claimsData.estimated_us_patients
        }
      }
    }
    
    if (newCriterionType === 'inclusion') {
      setInclusionCriteria([...inclusionCriteria, criterion])
    } else {
      setExclusionCriteria([...exclusionCriteria, criterion])
    }
    
    setNewCriterionText("")
    toast.success(`Added ${newCriterionType} criterion`)
  }
  
  const removeCriterion = (id: string, type: "inclusion" | "exclusion") => {
    if (type === 'inclusion') {
      setInclusionCriteria(inclusionCriteria.filter(c => c.id !== id))
    } else {
      setExclusionCriteria(exclusionCriteria.filter(c => c.id !== id))
    }
    toast.success('Criterion removed')
  }
  
  const updateCriterion = async (id: string, type: "inclusion" | "exclusion", text: string) => {
    const impactData = estimateImpact(text, type)
    
    // Try to enrich with claims data
    let enrichedData = {
      estimatedImpact: impactData.impact,
      impactReasoning: impactData.reasoning,
      primaryICD: impactData.primaryICD,
      icdDescription: impactData.icdDescription,
      patientsAffected: undefined as number | undefined
    }
    
    if (impactData.primaryICD) {
      const claimsData = await fetchClaimsDataForICD(impactData.primaryICD, text)
      if (claimsData) {
        console.log('✅ Using claims data for', impactData.primaryICD, claimsData)
        enrichedData = {
          estimatedImpact: claimsData.impact_percentage,
          impactReasoning: claimsData.reasoning,
          primaryICD: impactData.primaryICD,
          icdDescription: claimsData.description,
          patientsAffected: claimsData.estimated_us_patients
        }
      }
    }
    
    const update = (c: IECriterion) => c.id === id ? { 
      ...c, 
      text, 
      estimatedImpact: enrichedData.estimatedImpact,
      impactReasoning: enrichedData.impactReasoning,
      primaryICD: enrichedData.primaryICD,
      icdDescription: enrichedData.icdDescription,
      patientsAffected: enrichedData.patientsAffected,
      icdCodes: extractICDCodes(text)
    } : c
    
    if (type === 'inclusion') {
      setInclusionCriteria(inclusionCriteria.map(update))
    } else {
      setExclusionCriteria(exclusionCriteria.map(update))
    }
    
    setEditingCriterion(null)
    toast.success('Criterion updated')
  }
  
  const CriterionCard = ({ criterion, onRemove, onUpdate }: {
    criterion: IECriterion
    onRemove: () => void
    onUpdate: (text: string) => void
  }) => {
    const isEditing = editingCriterion === criterion.id
    const [editText, setEditText] = useState(criterion.text)
    const isEnabled = criterion.enabled !== false
    
    // Use relative impact and actual patient flow
    const patientsAffected = criterion.patientsAffected || 0
    const populationBefore = criterion.populationBefore || 0
    const populationAfter = criterion.populationAfter || 0
    
    return (
      <Card className={`border-border/50 hover:border-primary/30 transition-colors ${!isEnabled ? 'opacity-50' : ''}`}>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-3">
              {/* Header with type, ICD, and toggle */}
              <div className="flex items-center gap-2 flex-wrap">
                {/* Toggle switch */}
                <button
                  onClick={() => toggleCriterion(criterion.id, criterion.type)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${
                    isEnabled ? 'bg-primary' : 'bg-muted'
                  }`}
                  title={isEnabled ? 'Click to disable' : 'Click to enable'}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-0.5 ${
                    isEnabled ? 'translate-x-5' : 'translate-x-0.5'
                  }`} />
                </button>
                
                {criterion.type === 'inclusion' ? (
                  <CheckCircle2 className={`h-4 w-4 flex-shrink-0 ${isEnabled ? 'text-green-500' : 'text-muted-foreground'}`} />
                ) : (
                  <XCircle className={`h-4 w-4 flex-shrink-0 ${isEnabled ? 'text-red-500' : 'text-muted-foreground'}`} />
                )}
                <span className="text-xs font-medium text-muted-foreground">
                  {criterion.type === 'inclusion' ? 'Inclusion' : 'Exclusion'} #{criterion.order}
                </span>
                
                {!isEnabled && (
                  <Badge variant="outline" className="text-xs text-muted-foreground">
                    DISABLED
                  </Badge>
                )}
                
                {/* Primary ICD Code Badge (larger, more prominent) */}
                {criterion.primaryICD && (
                  <Badge variant="default" className="text-xs font-mono bg-primary/10 text-primary border-primary/20">
                    ICD: {criterion.primaryICD}
                  </Badge>
                )}
                
                {/* Additional ICD codes if extracted from text */}
                {criterion.icdCodes && criterion.icdCodes.length > 0 && (
                  <Badge variant="outline" className="text-xs font-mono">
                    {criterion.icdCodes.join(', ')}
                  </Badge>
                )}
              </div>
              
              {/* ICD Description */}
              {criterion.icdDescription && (
                <div className="flex items-start gap-2 bg-muted/30 rounded-md px-2 py-1.5">
                  <Info className="h-3.5 w-3.5 text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-xs text-muted-foreground italic">
                    {criterion.icdDescription}
                  </span>
                </div>
              )}
              
              {/* Criterion Text */}
              {isEditing ? (
                <Input
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onBlur={() => {
                    if (editText.trim()) {
                      onUpdate(editText)
                    } else {
                      setEditingCriterion(null)
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && editText.trim()) {
                      onUpdate(editText)
                    }
                    if (e.key === 'Escape') {
                      setEditingCriterion(null)
                      setEditText(criterion.text)
                    }
                  }}
                  autoFocus
                  className="text-sm"
                />
              ) : (
                <p className="text-sm text-foreground leading-relaxed font-medium">{criterion.text}</p>
              )}
              
              {/* Impact Reasoning */}
              {criterion.impactReasoning && (
                <div className="flex items-start gap-2 bg-primary/5 rounded-md px-2 py-1.5 border border-primary/10">
                  <AlertTriangle className="h-3.5 w-3.5 text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-xs text-foreground">
                    <span className="font-medium">Impact Analysis:</span> {criterion.impactReasoning}
                  </span>
                </div>
              )}
              
              {/* Relative Impact Metrics */}
              <div className="space-y-2">
                {/* Population Flow */}
                <div className="bg-muted/30 rounded-md px-3 py-2">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground font-medium">POPULATION FLOW</span>
                    <span className={`font-bold ${isEnabled ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {isEnabled ? `${((criterion.relativeImpact || 0) * 100).toFixed(1)}% filtered` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 text-center">
                      <div className="text-xs text-muted-foreground">Before</div>
                      <div className="text-sm font-bold text-foreground">
                        {populationBefore.toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="h-px w-4 bg-border"></div>
                      <TrendingDown className={`h-3.5 w-3.5 ${isEnabled ? 'text-primary' : 'text-muted-foreground'}`} />
                      <div className="h-px w-4 bg-border"></div>
                    </div>
                    <div className="flex-1 text-center">
                      <div className="text-xs text-muted-foreground">After</div>
                      <div className="text-sm font-bold text-foreground">
                        {populationAfter.toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Patients Filtered */}
                {isEnabled && patientsAffected > 0 && (
                  <div className="flex items-center gap-2 bg-primary/5 rounded-md px-3 py-2 border border-primary/10">
                    <Users className="h-4 w-4 text-primary" />
                    <div className="flex-1">
                      <span className="text-xs text-muted-foreground">
                        Filters out <span className="font-bold text-foreground">{patientsAffected.toLocaleString()}</span> patients
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (isEditing) {
                    setEditingCriterion(null)
                    setEditText(criterion.text)
                  } else {
                    setEditingCriterion(criterion.id)
                  }
                }}
                className="h-8 w-8 p-0"
              >
                <Edit2 className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onRemove}
                className="h-8 w-8 p-0 text-destructive hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Eligibility Criteria</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Define patient population with estimated screening impact
          </p>
        </div>
        <Button onClick={handleAIGenerate} disabled={isGenerating} className="gap-2 bg-primary">
          {isGenerating ? (
            <><Loader2 className="h-4 w-4 animate-spin" />Generating...</>
          ) : (
            <><Sparkles className="h-4 w-4" />Generate with AI</>
          )}
        </Button>
      </div>
      
      {/* Population Funnel Overview */}
      <Card className="border-2 border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5" />
            Population Screening Funnel
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">🇺🇸 US Population</p>
              <p className="text-2xl font-bold text-foreground">
                {populationFunnel.totalPopulation.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">{indication || 'Therapeutic Area'}</p>
            </div>
            
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">→ After Inclusion</p>
              <p className="text-2xl font-bold text-green-600">
                {populationFunnel.afterInclusion.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">
                {((populationFunnel.afterInclusion / populationFunnel.totalPopulation) * 100).toFixed(1)}% of TA population
              </p>
            </div>
            
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">→ After Exclusion</p>
              <p className="text-2xl font-bold text-blue-600">
                {populationFunnel.afterExclusion.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">
                {((populationFunnel.afterExclusion / populationFunnel.totalPopulation) * 100).toFixed(1)}% of TA population
              </p>
            </div>
            
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">→ Final Eligible</p>
              <p className="text-2xl font-bold text-primary">
                {populationFunnel.finalEligible.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">
                {((populationFunnel.finalEligible / populationFunnel.totalPopulation) * 100).toFixed(1)}% of TA population
              </p>
            </div>
          </div>
          
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <strong>All numbers extrapolated to full US population.</strong> Population estimates based on {indication || 'indication'} prevalence data from claims database (15% sample extrapolated to 330M US population). 
              Individual criterion impacts are context-aware and adjust based on population characteristics at each stage. 
              Actual enrollment will depend on site selection and recruitment effectiveness.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
      
      <div className="grid grid-cols-2 gap-6">
        {/* Inclusion Criteria */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <h3 className="text-lg font-semibold">Inclusion Criteria</h3>
              <Badge variant="secondary">{inclusionCriteria.length}</Badge>
            </div>
          </div>
          
          <div className="space-y-2">
            {inclusionCriteria.map((criterion) => (
              <CriterionCard
                key={criterion.id}
                criterion={criterion}
                onRemove={() => removeCriterion(criterion.id, 'inclusion')}
                onUpdate={(text) => updateCriterion(criterion.id, 'inclusion', text)}
              />
            ))}
            
            {inclusionCriteria.length === 0 && (
              <Card className="border-dashed">
                <CardContent className="pt-8 pb-8 text-center text-muted-foreground text-sm">
                  No inclusion criteria yet. Click "Generate with AI" or add manually below.
                </CardContent>
              </Card>
            )}
          </div>
          
          {/* Add new inclusion criterion */}
          <div className="flex gap-2">
            <Input
              placeholder="Add inclusion criterion..."
              value={newCriterionType === 'inclusion' ? newCriterionText : ''}
              onChange={(e) => {
                setNewCriterionType('inclusion')
                setNewCriterionText(e.target.value)
              }}
              onKeyDown={(e) => e.key === 'Enter' && newCriterionType === 'inclusion' && addCriterion()}
              className="flex-1"
            />
            <Button 
              onClick={() => {
                setNewCriterionType('inclusion')
                addCriterion()
              }}
              disabled={newCriterionType !== 'inclusion' || !newCriterionText.trim()}
              size="sm"
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Add
            </Button>
          </div>
        </div>
        
        {/* Exclusion Criteria */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              <h3 className="text-lg font-semibold">Exclusion Criteria</h3>
              <Badge variant="secondary">{exclusionCriteria.length}</Badge>
            </div>
          </div>
          
          <div className="space-y-2">
            {exclusionCriteria.map((criterion) => (
              <CriterionCard
                key={criterion.id}
                criterion={criterion}
                onRemove={() => removeCriterion(criterion.id, 'exclusion')}
                onUpdate={(text) => updateCriterion(criterion.id, 'exclusion', text)}
              />
            ))}
            
            {exclusionCriteria.length === 0 && (
              <Card className="border-dashed">
                <CardContent className="pt-8 pb-8 text-center text-muted-foreground text-sm">
                  No exclusion criteria yet. Click "Generate with AI" or add manually below.
                </CardContent>
              </Card>
            )}
          </div>
          
          {/* Add new exclusion criterion */}
          <div className="flex gap-2">
            <Input
              placeholder="Add exclusion criterion..."
              value={newCriterionType === 'exclusion' ? newCriterionText : ''}
              onChange={(e) => {
                setNewCriterionType('exclusion')
                setNewCriterionText(e.target.value)
              }}
              onKeyDown={(e) => e.key === 'Enter' && newCriterionType === 'exclusion' && addCriterion()}
              className="flex-1"
            />
            <Button 
              onClick={() => {
                setNewCriterionType('exclusion')
                addCriterion()
              }}
              disabled={newCriterionType !== 'exclusion' || !newCriterionText.trim()}
              size="sm"
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Add
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

