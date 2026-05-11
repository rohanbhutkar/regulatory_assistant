"use client"

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { 
  ReferenceTrial, 
  SimulationResult, 
  Site,
  Objective,
  Endpoint,
  IECriteria
} from '@/lib/types/study-types'
import type { CPPResult } from '@/lib/types/cpp'
import { toast } from 'sonner'

interface Arm {
  id: string
  name: string
  intervention: string
  participants: string
}

interface OverallStudyDesign {
  studyType?: string
  totalParticipants?: number
  duration?: string
  arms?: Arm[]
  indication?: string
  phase?: string
}

export interface Insight {
  id: string
  type: 'benchmark' | 'warning' | 'optimization' | 'opportunity' | 'risk' | 'bestPractice'
  title: string
  message: string
  confidence: number
  data?: any
  visualization?: string
  detail?: string
  source: string
  actions?: Array<{
    label: string
    action: string
    value?: any
  }>
}

export interface StudyDesignerContextType {
  // Reference Trials
  referenceTrials: ReferenceTrial[]
  selectedTrials: ReferenceTrial[]
  setReferenceTrials: (trials: ReferenceTrial[]) => void
  setSelectedTrials: (trials: ReferenceTrial[]) => void
  
  // Simulation
  simulationResult: SimulationResult | null
  setSimulationResult: (result: SimulationResult | null) => void
  
  // CPP Result
  cppResult: CPPResult | null
  setCppResult: (result: CPPResult | null) => void
  
  // Sites
  selectedSites: Site[]
  setSelectedSites: (sites: Site[]) => void
  
  // Protocol Components
  objectives: Objective[]
  setObjectives: (objectives: Objective[]) => void
  endpoints: Endpoint[]
  setEndpoints: (endpoints: Endpoint[]) => void
  inclusionCriteria: IECriteria[]
  setInclusionCriteria: (criteria: IECriteria[]) => void
  exclusionCriteria: IECriteria[]
  setExclusionCriteria: (criteria: IECriteria[]) => void
  
  // SoA (Schedule of Activities)
  soaVisits: any[]
  setSoaVisits: (visits: any[]) => void
  soaActivities: any[]
  setSoaActivities: (activities: any[]) => void
  
  // Overall Study Design
  studyDesign: OverallStudyDesign | null
  setStudyDesign: (design: OverallStudyDesign | null) => void
  
  // Protocol Sections
  protocolSections: Record<string, string>
  updateProtocolSection: (sectionId: string, content: string) => void
  
  // Active Tab
  activeTab: string
  setActiveTab: (tab: string) => void
  
  // Study Context (derived from basic info, study design, or selected trials)
  studyContext: {
    indication: string
    phase: string
    therapeuticArea: string
    drugName: string
    studyTitle?: string
    patient_count?: number
    duration_months?: number
    duration_weeks?: number
    duration_text?: string
    site_count?: number
    studyDesign?: string
    studyType?: string
    totalParticipants?: number
    numberOfArms?: number
    primaryEndpoint?: string
    objectives?: string
    background?: string
  }
  
  // Basic Info Management
  updateBasicInfo: (updates: any) => void
  
  // AI Insights
  insights: Record<string, Insight[]>  // Insights by tab
  insightsLoading: boolean
  generateInsights: (tab: string) => Promise<void>
  clearInsights: (tab: string) => void
  
  // Agent Actions
  agentActions: {
    selectTrials: (query: string, refine?: boolean) => Promise<void>
    runSimulation: (type: string) => Promise<void>
    generateCriteria: (indication: string) => Promise<void>
    selectSites: (criteria: string) => Promise<void>
    switchToTab: (tab: string) => void
    generateProtocolSection: (sectionId: string) => Promise<void>
    updateProtocolSection: (sectionId: string, content: string) => void
    updateFromTrials: () => void
    updateStudyMetadata: (updates: {
      indication?: string
      phase?: string
      drugName?: string
      therapeuticArea?: string
    }, source?: 'agent' | 'manual') => void
  }
  
  // Helper functions
  clearSelection: () => void
  updateFromTrials: () => void
}

const StudyDesignerContext = createContext<StudyDesignerContextType | undefined>(undefined)

export function StudyDesignerProvider({ children }: { children: React.ReactNode }) {
  // State
  const [referenceTrials, setReferenceTrials] = useState<ReferenceTrial[]>([])
  const [selectedTrials, setSelectedTrials] = useState<ReferenceTrial[]>([])
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null)
  const [cppResult, setCppResult] = useState<CPPResult | null>(null)
  const [selectedSites, setSelectedSites] = useState<Site[]>([])
  const [objectives, setObjectives] = useState<Objective[]>([])
  const [endpoints, setEndpoints] = useState<Endpoint[]>([])
  const [inclusionCriteria, setInclusionCriteria] = useState<IECriteria[]>([])
  const [exclusionCriteria, setExclusionCriteria] = useState<IECriteria[]>([])
  const [studyDesign, setStudyDesign] = useState<OverallStudyDesign | null>(null)
  const [protocolSections, setProtocolSections] = useState<Record<string, string>>({})
  const [activeTab, setActiveTab] = useState<string>('basic-info')
  
  // SoA (Schedule of Activities) state
  const [soaVisits, setSoaVisits] = useState<any[]>([])
  const [soaActivities, setSoaActivities] = useState<any[]>([])
  
  // Basic info state (can be manually set or derived from trials)
  const [basicInfo, setBasicInfo] = useState<{
    indication?: string
    phase?: string
    therapeuticArea?: string
    drugName?: string
    studyTitle?: string
    patient_count?: number
    duration_months?: number
    site_count?: number
    studyDesign?: string
    primaryEndpoint?: string
    objectives?: string
    background?: string
  }>({})
  
  // AI Insights state
  const [insights, setInsights] = useState<Record<string, Insight[]>>({})
  const [insightsLoading, setInsightsLoading] = useState(false)
  
  // Helper function to parse duration text
  const parseDuration = (durationText: string | undefined) => {
    if (!durationText) return { months: undefined, weeks: undefined, text: undefined }
    
    const text = durationText.toLowerCase()
    let months: number | undefined
    let weeks: number | undefined
    
    // Try to extract weeks
    const weeksMatch = text.match(/(\d+)\s*weeks?/)
    if (weeksMatch) {
      weeks = parseInt(weeksMatch[1])
      months = Math.round(weeks / 4.33) // Approximate months
    }
    
    // Try to extract months
    const monthsMatch = text.match(/(\d+)\s*months?/)
    if (monthsMatch) {
      months = parseInt(monthsMatch[1])
      weeks = Math.round(months * 4.33) // Approximate weeks
    }
    
    // Try to extract years
    const yearsMatch = text.match(/(\d+)\s*years?/)
    if (yearsMatch) {
      const years = parseInt(yearsMatch[1])
      months = years * 12
      weeks = years * 52
    }
    
    return { months, weeks, text: durationText }
  }
  
  // Derived study context from basic info, study design, OR selected trials (precedence: basic info > study design > trials)
  const studyContext = React.useMemo(() => {
    // Start with base context from basic info or trials
    let baseContext = {
      indication: '',
      phase: '',
      therapeuticArea: '',
      drugName: ''
    }
    
    // If we have manually entered basic info, use that as base
    if (Object.keys(basicInfo).length > 0) {
      baseContext = {
        indication: basicInfo.indication || '',
        phase: basicInfo.phase || '',
        therapeuticArea: basicInfo.therapeuticArea || '',
        drugName: basicInfo.drugName || ''
      }
    } else if (selectedTrials.length > 0) {
      // Otherwise derive from selected trials
      const firstTrial = selectedTrials[0]
      baseContext = {
        indication: firstTrial.indication || firstTrial.disease || '',
        phase: firstTrial.phase || '',
        therapeuticArea: firstTrial.therapeuticArea || '',
        drugName: firstTrial.primaryDrug || ''
      }
    }
    
    // Parse duration from studyDesign if available
    const durationInfo = parseDuration(studyDesign?.duration)
    
    // Merge with study design data, IE criteria, objectives, and endpoints
    return {
      ...baseContext,
      studyTitle: basicInfo.studyTitle,
      patient_count: basicInfo.patient_count || studyDesign?.totalParticipants,
      totalParticipants: studyDesign?.totalParticipants || basicInfo.patient_count,
      duration_months: basicInfo.duration_months || durationInfo.months,
      duration_weeks: durationInfo.weeks,
      duration_text: studyDesign?.duration || basicInfo.studyDesign,
      site_count: basicInfo.site_count || selectedSites.length,
      studyDesign: basicInfo.studyDesign || studyDesign?.studyType,
      studyType: studyDesign?.studyType,
      numberOfArms: studyDesign?.arms?.length,
      primaryEndpoint: basicInfo.primaryEndpoint || (endpoints.length > 0 ? endpoints.find(e => e.isPrimary)?.description : undefined),
      primaryObjective: basicInfo.primaryObjective || (objectives.length > 0 ? objectives.find(o => o.isPrimary)?.description : undefined),
      objectives: basicInfo.objectives,
      background: basicInfo.background,
      // Include IE Criteria from state
      ieCriteria: {
        inclusion: inclusionCriteria,
        exclusion: exclusionCriteria
      },
      // Include objectives and endpoints from state
      objectivesList: objectives,
      endpointsList: endpoints,
      // Include SoA data
      soa_data: soaVisits.length > 0 || soaActivities.length > 0 ? {
        visits: soaVisits,
        activities: soaActivities
      } : undefined
    }
  }, [selectedTrials, basicInfo, studyDesign, inclusionCriteria, exclusionCriteria, objectives, endpoints, selectedSites, soaVisits, soaActivities])
  
  // Update protocol sections helper
  const updateProtocolSection = useCallback((sectionId: string, content: string) => {
    setProtocolSections(prev => ({
      ...prev,
      [sectionId]: content
    }))
  }, [])
  
  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedTrials([])
    setSimulationResult(null)
    setSelectedSites([])
  }, [])
  
  // Update context from selected trials
  const updateFromTrials = useCallback(() => {
    if (selectedTrials.length === 0) return
    
    // Extract common patterns from selected trials
    const indications = selectedTrials.map(t => t.indication || t.disease).filter(Boolean)
    const phases = selectedTrials.map(t => t.phase).filter(Boolean)
    const drugs = selectedTrials.map(t => t.primaryDrug).filter(Boolean)
    
    console.log('📊 Updated study context from trials:', {
      indications: [...new Set(indications)],
      phases: [...new Set(phases)],
      drugs: [...new Set(drugs)]
    })
  }, [selectedTrials])

  // Update basic info (for manual or agent updates)
  const updateBasicInfo = useCallback((updates: Partial<typeof basicInfo>) => {
    console.log('📝 Updating basic info:', updates)
    setBasicInfo(prev => ({
      ...prev,
      ...updates
    }))
  }, [])
  
  // Agent-initiated update with hierarchy: manual > agent > reference trials
  // This allows the research agent to intelligently populate fields
  const updateStudyMetadata = useCallback((updates: {
    indication?: string
    phase?: string
    drugName?: string
    therapeuticArea?: string
  }, source: 'agent' | 'manual' = 'agent') => {
    console.log(`🤖 Updating study metadata from ${source}:`, updates)
    
    // Update basic info state (hierarchy: manual > agent > reference trials)
    setBasicInfo(prev => ({
      ...prev,
      ...(updates.indication !== undefined && { indication: updates.indication }),
      ...(updates.phase !== undefined && { phase: updates.phase }),
      ...(updates.drugName !== undefined && { drugName: updates.drugName }),
      ...(updates.therapeuticArea !== undefined && { therapeuticArea: updates.therapeuticArea })
    }))
    
    toast.success(`Study metadata updated from ${source}`)
  }, [])
  
  // AI Insights Functions
  const generateInsights = useCallback(async (tab: string) => {
    try {
      setInsightsLoading(true)
      console.log('🔮 Generating insights for tab:', tab)
      
      const response = await fetch('http://localhost:8001/api/insights/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tab,
          study_context: studyContext,
          selected_trials: selectedTrials,
          selected_sites: selectedSites
        })
      })
      
      if (!response.ok) {
        throw new Error(`Insights generation failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      setInsights(prev => ({
        ...prev,
        [tab]: data.insights
      }))
      
      toast.success(`Generated ${data.insights.length} insights for ${tab}`)
      
      // Cache insights in localStorage
      try {
        localStorage.setItem(`insights-${tab}`, JSON.stringify(data.insights))
      } catch (e) {
        console.warn('Failed to cache insights:', e)
      }
      
    } catch (error) {
      console.error('❌ Error generating insights:', error)
      toast.error('Failed to generate insights')
    } finally {
      setInsightsLoading(false)
    }
  }, [studyContext, selectedTrials, selectedSites])
  
  const clearInsights = useCallback((tab: string) => {
    setInsights(prev => {
      const updated = { ...prev }
      delete updated[tab]
      return updated
    })
    try {
      localStorage.removeItem(`insights-${tab}`)
    } catch (e) {
      console.warn('Failed to clear cached insights:', e)
    }
  }, [])
  
  // Agent Actions
  const selectTrialsByCriteria = useCallback(async (query: string, refine: boolean = false) => {
    try {
      console.log('🔍 Selecting trials by criteria:', { query, refine })
      
      const response = await fetch('http://localhost:8001/api/data/trialtrove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query,
          use_smart_search: true
        })
      })
      
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      const trials = data.trials || []
      
      console.log('✅ Found trials:', trials.length)
      console.log('📋 First trial sample:', trials[0])
      console.log('📋 Trial keys:', trials[0] ? Object.keys(trials[0]) : 'No trials')
      
      // Convert to ReferenceTrial format
      // Note: TrialTrove columns can have spaces OR underscores, so we check both
      const convertedTrials: ReferenceTrial[] = trials.map((t: any, index: number) => ({
        id: t['Trial ID'] || t.Trial_ID || t.id || `trial-${index}`,
        nctId: t['Protocol/Trial ID'] || t['NCT ID'] || t.NCT_ID || t.nctId || '',
        title: t['Trial Title'] || t.Trial_Title || t.title || '',
        indication: t.Disease || t.indication || '',
        disease: t.Disease || t.disease || '',
        phase: t['Trial Phase'] || t.Trial_Phase || t.phase || '',
        status: t['Trial Status'] || t.Trial_Status || t.status || '',
        sponsor: t['Sponsor/Collaborator'] || t.Sponsor || t.sponsor || '',
        primaryDrug: t['Primary Tested Drug'] || t.Primary_Tested_Drug || t.primaryDrug || '',
        therapeuticArea: t['Therapeutic Area'] || t.Therapeutic_Area || t.therapeuticArea || '',
        enrollmentTarget: t['Target Accrual'] || t.Enrollment_Target || t.enrollmentTarget || 0,
        enrollmentCurrent: t['Actual Accrual (No. of patients)'] || t.Enrollment_Current || t.enrollmentCurrent || 0,
        startDate: t['Start Date'] || t.Trial_Start_Date || t.startDate || '',
        completionDate: t['Full Completion Date'] || t.Trial_Completion_Date || t.completionDate || '',
        primaryEndpoint: t['Primary Endpoint'] || t.Primary_Endpoint || t.primaryEndpoint || '',
        secondaryEndpoint: t['Secondary/Other Endpoint'] || t.Secondary_Endpoint || t.secondaryEndpoint || '',
        studyDesign: t['Study Design'] || t.Study_Design || t.studyDesign || '',
        countries: t.Countries || t.countries || '',
        sites: t['Identified Sites'] || t.Sites || t.sites || 0,
        selected: true, // Mark as selected when added by agent
        ieKeyPoints: [],
        locations: []
      }))
      
      console.log('🔄 Converted trials:', convertedTrials.length)
      console.log('📋 First converted trial:', convertedTrials[0])
      console.log('📋 Converted trial has id?', convertedTrials[0]?.id)
      console.log('📋 Converted trial has title?', convertedTrials[0]?.title)
      
      if (refine) {
        // Refine existing selection
        const refinedTrials = convertedTrials.filter(newTrial =>
          selectedTrials.some(existing => existing.id === newTrial.id) ||
          !selectedTrials.length
        )
        setSelectedTrials(refinedTrials.length > 0 ? refinedTrials : convertedTrials)
      } else {
        // Replace selection
        setSelectedTrials(convertedTrials)
      }
      
      toast.success(`Selected ${convertedTrials.length} trials`)
    } catch (error) {
      console.error('❌ Error selecting trials:', error)
      toast.error('Failed to select trials')
    }
  }, [selectedTrials])
  
  const runSimulation = useCallback(async (type: string) => {
    try {
      console.log('🎯 Running simulation:', type)
      
      // Prepare simulation request based on type
      let endpoint = ''
      let requestBody: any = {}
      
      if (type === 'startup') {
        endpoint = 'http://localhost:8001/api/commercial/simulate'
        requestBody = {
          studyDesign: studyContext.indication,
          sites: selectedSites.map(s => s.name),
          patientCount: selectedTrials.reduce((sum, t) => sum + (t.enrollmentTarget || 0), 0),
          durationMonths: 24,
          therapeuticArea: studyContext.therapeuticArea
        }
      } else if (type === 'budget') {
        endpoint = 'http://localhost:8001/api/commercial/budget-analysis'
        requestBody = {
          studyDesign: studyContext.indication,
          sites: selectedSites.map(s => s.name),
          patientCount: selectedTrials.reduce((sum, t) => sum + (t.enrollmentTarget || 0), 0),
          durationMonths: 24,
          therapeuticArea: studyContext.therapeuticArea
        }
      }
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })
      
      if (!response.ok) {
        throw new Error(`Simulation failed: ${response.statusText}`)
      }
      
      const result = await response.json()
      setSimulationResult(result)
      toast.success('Simulation completed')
      
      // Switch to simulation tab
      setActiveTab('simulation')
    } catch (error) {
      console.error('❌ Error running simulation:', error)
      toast.error('Failed to run simulation')
    }
  }, [studyContext, selectedSites, selectedTrials])
  
  const generateCriteria = useCallback(async (indication: string) => {
    try {
      console.log('📝 Generating criteria for:', indication)
      
      const response = await fetch('http://localhost:8001/api/protocol/generate-section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_type: 'inclusion_criteria',
          trials: selectedTrials,
          reference_info: indication
        })
      })
      
      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Parse criteria from response
      if (data.content) {
        const criteriaLines = data.content.split('\n').filter((line: string) => line.trim())
        const newCriteria: IECriteria[] = criteriaLines.map((line: string, idx: number) => ({
          id: `criteria-${idx}`,
          text: line.replace(/^[-•]\s*/, ''),
          category: 'General'
        }))
        
        setInclusionCriteria(newCriteria)
        toast.success('Criteria generated')
      }
    } catch (error) {
      console.error('❌ Error generating criteria:', error)
      toast.error('Failed to generate criteria')
    }
  }, [selectedTrials])
  
  const selectSites = useCallback(async (criteria: string) => {
    try {
      console.log('🏥 Selecting sites by criteria:', criteria)
      
      const response = await fetch('http://localhost:8001/api/commercial/site-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          indication: studyContext.indication,
          phase: studyContext.phase,
          targetEnrollment: selectedTrials.reduce((sum, t) => sum + (t.enrollmentTarget || 0), 0),
          criteria
        })
      })
      
      if (!response.ok) {
        throw new Error(`Site selection failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      if (data.sites) {
        setSelectedSites(data.sites)
        toast.success(`Selected ${data.sites.length} sites`)
        setActiveTab('site-selection')
      }
    } catch (error) {
      console.error('❌ Error selecting sites:', error)
      toast.error('Failed to select sites')
    }
  }, [studyContext, selectedTrials])
  
  const switchToTab = useCallback((tab: string) => {
    console.log('🔄 Switching to tab:', tab)
    setActiveTab(tab)
  }, [])
  
  const generateProtocolSection = useCallback(async (sectionId: string) => {
    try {
      console.log('📝 Generating protocol section:', sectionId)
      
      const response = await fetch('http://localhost:8001/api/protocol/generate-section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_type: sectionId,
          trials: selectedTrials,
          reference_info: `${studyContext.indication} - ${studyContext.phase}`
        })
      })
      
      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      if (data.content) {
        updateProtocolSection(sectionId, data.content)
        toast.success(`${sectionId} section generated`)
      }
    } catch (error) {
      console.error('❌ Error generating protocol section:', error)
      toast.error('Failed to generate protocol section')
    }
  }, [selectedTrials, studyContext, updateProtocolSection])
  
  const agentActions = {
    selectTrials: selectTrialsByCriteria,
    runSimulation,
    generateCriteria,
    selectSites,
    switchToTab,
    generateProtocolSection,
    updateProtocolSection: (sectionId: string, content: string) => {
      console.log(`✏️ Agent updating protocol section: ${sectionId}`)
      updateProtocolSection(sectionId, content)
    },
    updateFromTrials,
    updateStudyMetadata
  }
  
  const value: StudyDesignerContextType = {
    referenceTrials,
    selectedTrials,
    setReferenceTrials,
    setSelectedTrials,
    simulationResult,
    setSimulationResult,
    cppResult,
    setCppResult,
    selectedSites,
    setSelectedSites,
    objectives,
    setObjectives,
    endpoints,
    setEndpoints,
    inclusionCriteria,
    setInclusionCriteria,
    exclusionCriteria,
    setExclusionCriteria,
    soaVisits,
    setSoaVisits,
    soaActivities,
    setSoaActivities,
    studyDesign,
    setStudyDesign,
    protocolSections,
    updateProtocolSection,
    activeTab,
    setActiveTab,
    studyContext,
    updateBasicInfo,
    insights,
    insightsLoading,
    generateInsights,
    clearInsights,
    agentActions,
    clearSelection,
    updateFromTrials
  }
  
  return (
    <StudyDesignerContext.Provider value={value}>
      {children}
    </StudyDesignerContext.Provider>
  )
}

export function useStudyDesigner() {
  const context = useContext(StudyDesignerContext)
  if (context === undefined) {
    throw new Error('useStudyDesigner must be used within a StudyDesignerProvider')
  }
  return context
}

/** Safe on routes without StudyDesignerProvider (e.g. regulatory-intelligence, research). */
export function useStudyDesignerOptional(): StudyDesignerContextType | undefined {
  return useContext(StudyDesignerContext)
}
