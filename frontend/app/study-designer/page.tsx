"use client"

import { useState, useEffect, useCallback, type MouseEvent } from "react"
import { Header } from "@/components/layout/header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StudyList } from "@/components/study-designer/study-list"
import { toast } from "sonner"
import { BasicInfoTab } from "@/components/study-designer/basic-info-tab"
import { ReferenceTrialsTab } from "@/components/study-designer/reference-trials-tab"
import { IECriteriaTab } from "@/components/study-designer/ie-criteria-tab"
import { EnhancedIECriteriaTab } from "@/components/study-designer/enhanced-ie-criteria-tab"
import { SiteSelectionTab } from "@/components/study-designer/site-selection-tab"
import { EnhancedSiteSelectionTab } from "@/components/study-designer/enhanced-site-selection-tab"
import { EnhancedSiteSelectionTabV2 } from "@/components/study-designer/enhanced-site-selection-tab-v2"
import { SimulationTab } from "@/components/study-designer/simulation-tab"
import { EnhancedSimulationTab } from "@/components/study-designer/enhanced-simulation-tab"
import { BudgetTab } from "@/components/study-designer/budget-tab"
import { ComprehensiveBudgetTab } from "@/components/study-designer/comprehensive-budget-tab"
import { ProtocolTitleTab } from "@/components/study-designer/protocol-title-tab"
import { RationaleTab } from "@/components/study-designer/rationale-tab"
import { ObjectivesTab } from "@/components/study-designer/objectives-tab"
import { EndpointsTab } from "@/components/study-designer/endpoints-tab"
import { OverallDesignTab } from "@/components/study-designer/overall-design-tab"
import { SchemaTab } from "@/components/study-designer/schema-tab"
import { SoATab } from "@/components/study-designer/soa-tab"
import { ProtocolSectionEditor } from "@/components/study-designer/protocol-section-editor"
import { ResearchAgentChat } from "@/components/chat/research-agent-chat"
import { USDMExportButton } from "@/components/study-designer/usdm-export-button"
import { AIInsightsPanel } from "@/components/study-designer/ai-insights-panel"
import { StudyDesignerProvider, useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { MOCK_STUDIES, MOCK_REFERENCE_TRIALS } from "@/lib/data/mock-studies"
import type { StudyDesign, ReferenceTrial, IECriterion, SelectedSite, SimulationResult } from "@/lib/types/study-types"
import { ArrowLeft, FileText, Pencil, Check, X } from "lucide-react"
import { useRouter } from "next/navigation"

function StudyDesignerContent() {
  const router = useRouter()
  const { 
    referenceTrials, 
    setReferenceTrials, 
    selectedTrials,
    setSelectedTrials,
    selectedSites, 
    setSelectedSites, 
    simulationResult, 
    setSimulationResult, 
    activeTab, 
    setActiveTab,
    studyContext,
    updateBasicInfo,
    objectives,
    setObjectives,
    endpoints,
    setEndpoints,
    inclusionCriteria,
    setInclusionCriteria,
    exclusionCriteria,
    setExclusionCriteria,
    protocolSections,
    updateProtocolSection,
    studyDesign,
    setStudyDesign
  } = useStudyDesigner()
  const [selectedStudy, setSelectedStudy] = useState<StudyDesign | null>(null)
  const [studies, setStudies] = useState<StudyDesign[]>(MOCK_STUDIES)
  const [chatWidth, setChatWidth] = useState(400)
  const [isResizing, setIsResizing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  
  // Editable fields state
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [editableTitle, setEditableTitle] = useState("")
  const [isEditingTA, setIsEditingTA] = useState(false)
  const [editableTA, setEditableTA] = useState("")
  const [isEditingPhase, setIsEditingPhase] = useState(false)
  const [editablePhase, setEditablePhase] = useState("")
  const [isEditingMolecule, setIsEditingMolecule] = useState(false)
  const [editableMolecule, setEditableMolecule] = useState("")

  // Load studies from localStorage on mount
  useEffect(() => {
    const savedStudies = localStorage.getItem('study-designer-studies')
    if (savedStudies) {
      try {
        const parsed = JSON.parse(savedStudies)
        // Convert date strings back to Date objects
        const studiesWithDates = parsed.map((study: any) => ({
          ...study,
          lastModified: new Date(study.lastModified)
        }))
        setStudies(studiesWithDates)
      } catch (error) {
        console.error('Error loading studies from localStorage:', error)
      }
    }
  }, [])

  // Auto-save when context data changes (debounced)
  useEffect(() => {
    if (!selectedStudy) return

    const timeoutId = setTimeout(() => {
      // Silently save in background
      handleSaveStudy()
    }, 2000) // Save 2 seconds after last change

    return () => clearTimeout(timeoutId)
  }, [selectedTrials, protocolSections, selectedSites, inclusionCriteria, exclusionCriteria, simulationResult, objectives, endpoints, studyDesign])

  // Helper function to strip large/regenerable data before saving
  const stripLargeData = (study: StudyDesign): StudyDesign => {
    return {
      ...study,
      // Keep only essential trial data (ID, NCT, title)
      referenceTrials: (study.referenceTrials || []).map(t => ({
        id: t.id,
        nctId: t.nctId,
        title: t.title,
        indication: t.indication,
        phase: t.phase,
        primaryEndpoint: t.primaryEndpoint,
        sponsor: t.sponsor,
        selected: t.selected,
        therapeuticArea: t.therapeuticArea,
        primaryDrug: t.primaryDrug,
        reportedSites: t.reportedSites,
        identifiedSites: t.identifiedSites,
      } as any)),
      // Keep only essential site data (ID, name, location)
      sites: (study.sites || []).map(s => ({
        id: s.id,
        name: s.name,
        location: s.location,
        coordinates: s.coordinates,
        score: s.score,
        historicalPerformance: s.historicalPerformance,
        estimatedEnrollment: s.estimatedEnrollment,
      })),
      // Keep only essential IE criteria (strip population analysis)
      ieCriteria: (study.ieCriteria || []).map(c => ({
        id: c.id,
        type: c.type,
        text: c.text,
        criterion: c.criterion,
        icdCodes: c.icdCodes,
        order: c.order,
        enabled: c.enabled,
        // Strip: estimatedImpact, populationImpact, patientsAffected, relativeImpact, etc.
      } as any)),
      // Strip large simulation data (keep only summary)
      simulation: study.simulation ? {
        simulation_id: study.simulation.simulation_id,
        success_probability: study.simulation.success_probability,
        expected_completion_date: study.simulation.expected_completion_date,
        expected_duration_months: study.simulation.expected_duration_months,
        // Strip: enrollment_curve, milestones (too large)
      } as any : null,
    }
  }

  // Save current study data to context
  const handleSaveStudy = useCallback(() => {
    if (!selectedStudy) return

    setIsSaving(true)
    
    try {
      // Create updated study with current context data
      const updatedStudy: StudyDesign = {
        ...selectedStudy,
        title: studyContext.indication 
          ? `${studyContext.phase ? (studyContext.phase.startsWith('Phase') ? studyContext.phase : `Phase ${studyContext.phase}`) : ''} ${studyContext.indication} Study`.trim()
          : selectedStudy.title,
        therapeuticArea: studyContext.therapeuticArea || selectedStudy.therapeuticArea,
        indication: studyContext.indication || selectedStudy.indication,
        phase: studyContext.phase || selectedStudy.phase,
        molecule: studyContext.drugName || selectedStudy.molecule,
        lastModified: new Date(),
        modifiedBy: "Current User",
        recentActivity: "Updated study design",
        referenceTrials: selectedTrials,
        protocolSections: Object.entries(protocolSections).map(([id, content]) => ({
          id,
          title: id.charAt(0).toUpperCase() + id.slice(1).replace(/_/g, ' '),
          content,
          lastModified: new Date(),
          modifiedBy: "Current User"
        })),
        sites: selectedSites,
        ieCriteria: [...inclusionCriteria, ...exclusionCriteria],
        simulation: simulationResult,
        objectives: objectives,
        endpoints: endpoints,
        // Overall Study Design fields (from context)
        studyType: studyDesign?.studyType,
        totalParticipants: studyDesign?.totalParticipants,
        duration: studyDesign?.duration,
        arms: studyDesign?.arms,
      }

      // Update studies list
      const updatedStudies = studies.map(s => 
        s.id === selectedStudy.id ? updatedStudy : s
      )
      
      // If it's a new study (not in the list), add it
      if (!studies.find(s => s.id === selectedStudy.id)) {
        updatedStudies.push(updatedStudy)
      }

      setStudies(updatedStudies)
      setSelectedStudy(updatedStudy)

      // Strip large data before saving to localStorage
      const strippedStudies = updatedStudies.map(stripLargeData)
      const dataToSave = JSON.stringify(strippedStudies)
      
      // Check size before saving (localStorage limit is ~5MB)
      const sizeInMB = new Blob([dataToSave]).size / 1024 / 1024
      console.log(`💾 Saving ${sizeInMB.toFixed(2)}MB to localStorage`)
      
      if (sizeInMB > 4.5) {
        console.warn('⚠️ Data size is large, keeping only the 5 most recent studies')
        // Keep only the 5 most recent studies if size is too large
        const recentStudies = strippedStudies
          .sort((a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime())
          .slice(0, 5)
        localStorage.setItem('study-designer-studies', JSON.stringify(recentStudies))
      } else {
        localStorage.setItem('study-designer-studies', dataToSave)
      }

      toast.success('Study saved successfully!')
    } catch (error: any) {
      console.error('Error saving study:', error)
      
      if (error.name === 'QuotaExceededError') {
        // Try to save with even more aggressive pruning
        try {
          console.warn('💾 Storage quota exceeded, keeping only current study')
          const strippedStudy = stripLargeData({
            ...selectedStudy,
            referenceTrials: selectedTrials,
            sites: selectedSites,
            ieCriteria: [...inclusionCriteria, ...exclusionCriteria],
            simulation: simulationResult,
            objectives: objectives,
            endpoints: endpoints,
          })
          localStorage.setItem('study-designer-studies', JSON.stringify([strippedStudy]))
          toast.warning('Storage limit reached - saved current study only')
        } catch (innerError) {
          console.error('Failed to save even with pruning:', innerError)
          toast.error('Storage quota exceeded - please export your study data')
        }
      } else {
        toast.error('Failed to save study')
      }
    } finally {
      setIsSaving(false)
    }
  }, [selectedStudy, studyContext, selectedTrials, protocolSections, selectedSites, inclusionCriteria, exclusionCriteria, simulationResult, objectives, endpoints, studies, studyDesign])

  const handleCreateNew = () => {
    const newStudy: StudyDesign = {
      id: `study-${Date.now()}`,
      title: "New Study Design",
      status: "design",
      therapeuticArea: "",
      indication: "",
      phase: "",
      lastModified: new Date(),
      modifiedBy: "Current User",
      recentActivity: "Created",
      referenceTrials: [],
      protocolSections: [],
      sites: [],
      ieCriteria: [],
      simulation: null,
    }
    setSelectedStudy(newStudy)
    
    // Clear basic info for new study
    updateBasicInfo({
      indication: "",
      phase: "",
      therapeuticArea: "",
      drugName: "",
      studyTitle: "",
    })
  }

  const handleSelectStudy = (study: StudyDesign) => {
    setSelectedStudy(study)
    // Load study data into context
    setSelectedTrials(study.referenceTrials || [])
    setSelectedSites(study.sites || [])
    
    // Split IE criteria by type
    const inclusion = (study.ieCriteria || []).filter(c => c.type === 'inclusion')
    const exclusion = (study.ieCriteria || []).filter(c => c.type === 'exclusion')
    setInclusionCriteria(inclusion)
    setExclusionCriteria(exclusion)
    
    setSimulationResult(study.simulation || null)
    
    // Load objectives and endpoints
    setObjectives(study.objectives || [])
    setEndpoints(study.endpoints || [])
    
    // Load overall study design
    if (study.studyType || study.totalParticipants || study.duration || study.arms) {
      setStudyDesign({
        studyType: study.studyType,
        totalParticipants: study.totalParticipants,
        duration: study.duration,
        arms: study.arms,
        indication: study.indication,
        phase: study.phase,
      })
      console.log('✅ Loaded study design from saved study:', {
        studyType: study.studyType,
        totalParticipants: study.totalParticipants,
        duration: study.duration,
        arms: study.arms?.length
      })
    }
    
    // Populate basic info from the study metadata
    updateBasicInfo({
      indication: study.indication,
      phase: study.phase,
      therapeuticArea: study.therapeuticArea,
      drugName: study.molecule,
      studyTitle: study.title,
    })
  }

  const handleDeleteStudy = (studyId: string) => {
    // Remove from studies list
    const updatedStudies = studies.filter(s => s.id !== studyId)
    setStudies(updatedStudies)
    
    // Update localStorage with stripped data
    const strippedStudies = updatedStudies.map(stripLargeData)
    localStorage.setItem('study-designer-studies', JSON.stringify(strippedStudies))
    
    // If the deleted study is currently selected, clear it
    if (selectedStudy?.id === studyId) {
      setSelectedStudy(null)
    }
    
    toast.success('Study deleted successfully')
  }

  const handleClearOldStudies = () => {
    // Keep only the 3 most recent studies
    const recentStudies = studies
      .sort((a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime())
      .slice(0, 3)
    
    setStudies(recentStudies)
    
    // Save stripped data
    const strippedStudies = recentStudies.map(stripLargeData)
    localStorage.setItem('study-designer-studies', JSON.stringify(strippedStudies))
    
    toast.success(`Cleared old studies, kept ${recentStudies.length} most recent`)
  }

  // Edit handlers
  const handleEditTitle = () => {
    setEditableTitle(selectedStudy?.title || "")
    setIsEditingTitle(true)
  }

  const handleSaveTitle = () => {
    if (selectedStudy && editableTitle.trim()) {
      const updatedStudy = { ...selectedStudy, title: editableTitle.trim() }
      setSelectedStudy(updatedStudy)
      setIsEditingTitle(false)
      handleSaveStudy()
    }
  }

  const handleCancelTitle = () => {
    setIsEditingTitle(false)
    setEditableTitle("")
  }

  const handleEditTA = () => {
    setEditableTA(studyContext.therapeuticArea || selectedStudy?.therapeuticArea || "")
    setIsEditingTA(true)
  }

  const handleSaveTA = () => {
    if (editableTA.trim()) {
      const updatedStudy = { ...selectedStudy!, therapeuticArea: editableTA.trim() }
      setSelectedStudy(updatedStudy)
      setIsEditingTA(false)
      // Update context
      updateBasicInfo({ therapeuticArea: editableTA.trim() })
      handleSaveStudy()
    }
  }

  const handleCancelTA = () => {
    setIsEditingTA(false)
    setEditableTA("")
  }

  const handleEditPhase = () => {
    setEditablePhase(studyContext.phase || selectedStudy?.phase || "")
    setIsEditingPhase(true)
  }

  const handleSavePhase = () => {
    if (editablePhase.trim()) {
      const updatedStudy = { ...selectedStudy!, phase: editablePhase.trim() }
      setSelectedStudy(updatedStudy)
      setIsEditingPhase(false)
      // Update context
      updateBasicInfo({ phase: editablePhase.trim() })
      handleSaveStudy()
    }
  }

  const handleCancelPhase = () => {
    setIsEditingPhase(false)
    setEditablePhase("")
  }

  const handleEditMolecule = () => {
    setEditableMolecule(studyContext.drugName || selectedStudy?.molecule || "")
    setIsEditingMolecule(true)
  }

  const handleSaveMolecule = () => {
    if (editableMolecule.trim()) {
      const updatedStudy = { ...selectedStudy!, molecule: editableMolecule.trim() }
      setSelectedStudy(updatedStudy)
      setIsEditingMolecule(false)
      // Update context
      updateBasicInfo({ drugName: editableMolecule.trim() })
      handleSaveStudy()
    }
  }

  const handleCancelMolecule = () => {
    setIsEditingMolecule(false)
    setEditableMolecule("")
  }

  const handleMouseDown = () => {
    setIsResizing(true)
  }

  const handleMouseMove = useCallback((e: Event) => {
    if (isResizing) {
      const mouseEvent = e as unknown as MouseEvent
      const newWidth = mouseEvent.clientX
      if (newWidth >= 300 && newWidth <= 600) {
        setChatWidth(newWidth)
      }
    }
  }, [isResizing])

  const handleMouseUp = () => {
    setIsResizing(false)
  }

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.addEventListener("mousemove", handleMouseMove)
      window.addEventListener("mouseup", handleMouseUp)
    }
    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("mousemove", handleMouseMove)
        window.removeEventListener("mouseup", handleMouseUp)
      }
    }
  }, [handleMouseMove])

  if (selectedStudy) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <Header />

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-4 sm:px-6 lg:px-8 py-2 sm:py-3 border-b border-border/40">
            <Button
              variant="ghost"
              onClick={() => setSelectedStudy(null)}
              className="mb-2 sm:mb-3 -ml-2 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Studies
            </Button>

            <div className="flex flex-col sm:flex-row items-start justify-between gap-3">
              <div className="flex-1">
                {/* Title - Editable */}
                <div className="flex items-center gap-2 mb-1 group">
                  {isEditingTitle ? (
                    <div className="flex items-center gap-2 flex-1">
                      <Input
                        value={editableTitle}
                        onChange={(e) => setEditableTitle(e.target.value)}
                        className="text-xl sm:text-2xl lg:text-3xl font-semibold"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveTitle()
                          if (e.key === 'Escape') handleCancelTitle()
                        }}
                      />
                      <Button size="sm" variant="ghost" onClick={handleSaveTitle}>
                        <Check className="h-4 w-4 text-green-600" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={handleCancelTitle}>
                        <X className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  ) : (
                    <>
                      <h1 className="text-xl sm:text-2xl lg:text-3xl font-semibold tracking-tight text-foreground">
                        {studyContext.indication 
                          ? `${studyContext.phase ? (studyContext.phase.startsWith('Phase') ? studyContext.phase : `Phase ${studyContext.phase}`) : ''} ${studyContext.indication} Study`
                          : selectedStudy.title}
                </h1>
                      <Button 
                        size="sm" 
                        variant="ghost" 
                        onClick={handleEditTitle}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>

                {/* Subtitles - Editable */}
                <div className="flex flex-wrap items-center gap-2 text-sm sm:text-base text-muted-foreground">
                  {/* Therapeutic Area */}
                  <div className="flex items-center gap-1 group/ta">
                    {isEditingTA ? (
                      <>
                        <Input
                          value={editableTA}
                          onChange={(e) => setEditableTA(e.target.value)}
                          className="w-48 h-8 text-base"
                          placeholder="Therapeutic Area"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveTA()
                            if (e.key === 'Escape') handleCancelTA()
                          }}
                        />
                        <Button size="sm" variant="ghost" onClick={handleSaveTA} className="h-6 w-6 p-0">
                          <Check className="h-3 w-3 text-green-600" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={handleCancelTA} className="h-6 w-6 p-0">
                          <X className="h-3 w-3 text-destructive" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <span>{studyContext.therapeuticArea || selectedStudy.therapeuticArea}</span>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={handleEditTA}
                          className="h-6 w-6 p-0 opacity-0 group-hover/ta:opacity-100 transition-opacity"
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                      </>
                    )}
                  </div>
                  
                  <span>•</span>
                  
                  {/* Phase */}
                  <div className="flex items-center gap-1 group/phase">
                    {isEditingPhase ? (
                      <>
                        <Input
                          value={editablePhase}
                          onChange={(e) => setEditablePhase(e.target.value)}
                          className="w-32 h-8 text-base"
                          placeholder="Phase"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSavePhase()
                            if (e.key === 'Escape') handleCancelPhase()
                          }}
                        />
                        <Button size="sm" variant="ghost" onClick={handleSavePhase} className="h-6 w-6 p-0">
                          <Check className="h-3 w-3 text-green-600" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={handleCancelPhase} className="h-6 w-6 p-0">
                          <X className="h-3 w-3 text-destructive" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <span>{(() => {
                          const phase = studyContext.phase || selectedStudy.phase
                          return phase?.startsWith('Phase') ? phase : `Phase ${phase}`
                        })()}</span>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={handleEditPhase}
                          className="h-6 w-6 p-0 opacity-0 group-hover/phase:opacity-100 transition-opacity"
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                      </>
                    )}
                  </div>
                  
                  {(studyContext.drugName || selectedStudy.molecule) && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1 group/molecule">
                        {isEditingMolecule ? (
                          <>
                            <Input
                              value={editableMolecule}
                              onChange={(e) => setEditableMolecule(e.target.value)}
                              className="w-48 h-8 text-base"
                              placeholder="Molecule"
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveMolecule()
                                if (e.key === 'Escape') handleCancelMolecule()
                              }}
                            />
                            <Button size="sm" variant="ghost" onClick={handleSaveMolecule} className="h-6 w-6 p-0">
                              <Check className="h-3 w-3 text-green-600" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={handleCancelMolecule} className="h-6 w-6 p-0">
                              <X className="h-3 w-3 text-destructive" />
                            </Button>
                          </>
                        ) : (
                          <>
                            <span>{studyContext.drugName || selectedStudy.molecule}</span>
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              onClick={handleEditMolecule}
                              className="h-6 w-6 p-0 opacity-0 group-hover/molecule:opacity-100 transition-opacity"
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                          </>
                        )}
                      </div>
                    </>
                  )}
                </div>
                
                {selectedTrials.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Based on {selectedTrials.length} reference trial{selectedTrials.length !== 1 ? 's' : ''}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleSaveStudy}
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save Draft'}
                </Button>
                <Button size="sm">Export Protocol</Button>
                <USDMExportButton />
              </div>
            </div>
          </div>

          <div className="flex-1 flex min-h-0 overflow-hidden">
            {/* Chat Panel - Hidden on mobile */}
            <div style={{ width: chatWidth }} className="hidden lg:flex border-r border-border/40 flex-col min-h-0">
              
              <div className="flex-1 min-h-0 overflow-hidden">
                <ResearchAgentChat />
              </div>
            </div>

            <div
              className="hidden lg:block w-1 bg-border/40 hover:bg-border cursor-col-resize transition-colors"
              onMouseDown={handleMouseDown}
            />

            {/* Canvas Panel */}
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full min-h-0 flex flex-col">
                <div className="px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 border-b border-border/40 overflow-x-auto">
                  <TabsList className="bg-transparent border-b-0 p-0 h-auto inline-flex min-w-max">
                    <TabsTrigger
                      value="basic-info"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Basic Info
                    </TabsTrigger>
                    <TabsTrigger
                      value="reference-trials"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Reference Trials
                    </TabsTrigger>
                    <TabsTrigger
                      value="title"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Title
                    </TabsTrigger>
                    <TabsTrigger
                      value="rationale"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Rationale
                    </TabsTrigger>
                    <TabsTrigger
                      value="introduction"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Introduction
                    </TabsTrigger>
                    <TabsTrigger
                      value="background"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Background
                    </TabsTrigger>
                    <TabsTrigger
                      value="hypothesis"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Hypothesis
                    </TabsTrigger>
                    <TabsTrigger
                      value="objectives"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Objectives
                    </TabsTrigger>
                    <TabsTrigger
                      value="endpoints"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Endpoints
                    </TabsTrigger>
                    <TabsTrigger
                      value="ie-criteria"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      IE Criteria
                    </TabsTrigger>
                    <TabsTrigger
                      value="design"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Overall Design
                    </TabsTrigger>
                    <TabsTrigger
                      value="schema"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Schema
                    </TabsTrigger>
                    <TabsTrigger
                      value="soa"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      SoA
                    </TabsTrigger>
                    <TabsTrigger
                      value="site-selection"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Site Selection
                    </TabsTrigger>
                    <TabsTrigger
                      value="simulation"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Simulation
                    </TabsTrigger>
                    <TabsTrigger
                      value="budget"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Budget
                    </TabsTrigger>
                    <TabsTrigger
                      value="research"
                      className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                    >
                      Research Agent
                    </TabsTrigger>
                  </TabsList>
                </div>

                <TabsContent value="basic-info" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <BasicInfoTab />
                </TabsContent>

                <TabsContent value="reference-trials" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ReferenceTrialsTab trials={selectedTrials} onTrialsChange={setSelectedTrials} />
                </TabsContent>

                <TabsContent value="title" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ProtocolTitleTab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="rationale" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <RationaleTab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="introduction" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ProtocolSectionEditor 
                    title="Introduction"
                    content={protocolSections.introduction || ""}
                    onContentChange={(content) => updateProtocolSection('introduction', content)}
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="background" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ProtocolSectionEditor 
                    title="Background"
                    content={protocolSections.background || ""}
                    onContentChange={(content) => updateProtocolSection('background', content)}
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="hypothesis" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ProtocolSectionEditor 
                    title="Hypothesis"
                    content={protocolSections.hypothesis || ""}
                    onContentChange={(content) => updateProtocolSection('hypothesis', content)}
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="objectives" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ObjectivesTab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="endpoints" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <EndpointsTab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="ie-criteria" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <EnhancedIECriteriaTab />
                </TabsContent>

                <TabsContent value="design" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <OverallDesignTab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="schema" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <SchemaTab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="soa" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <SoATab 
                    trials={selectedTrials} 
                    referenceInfo={`${studyContext.phase || ''} ${studyContext.indication || ''} ${studyContext.drugName || ''}`.trim()} 
                  />
                </TabsContent>

                <TabsContent value="site-selection" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <EnhancedSiteSelectionTabV2 />
                </TabsContent>

                <TabsContent value="simulation" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <EnhancedSimulationTab />
                </TabsContent>

                <TabsContent value="budget" className="flex-1 overflow-auto p-4 sm:p-6 mt-0">
                  <ComprehensiveBudgetTab />
                </TabsContent>

                <TabsContent value="research" className="flex-1 min-h-0 overflow-hidden mt-0">
                  <ResearchAgentChat />
                </TabsContent>
              </Tabs>
            </div>
          </div>
          
          {/* AI Insights Panel - Fixed on right side */}
          <AIInsightsPanel tab={activeTab} />
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Page Header */}
        <div className="p-6 border-b border-border/50 bg-card/30">
          <div className="flex items-center justify-between mb-4">
            <Button variant="ghost" onClick={() => router.push("/")} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Personas
            </Button>
          </div>

          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-muted/80 flex items-center justify-center">
              <FileText className="h-6 w-6 text-foreground" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Study Designer</h1>
              <p className="text-muted-foreground">Protocol design and trial planning workspace</p>
            </div>
          </div>
        </div>

        {/* Study List */}
        <div className="flex-1 overflow-auto p-6">
          <StudyList 
            studies={studies} 
            onSelectStudy={handleSelectStudy} 
            onCreateNew={handleCreateNew}
            onDeleteStudy={handleDeleteStudy}
          />
        </div>
      </div>
    </div>
  )
}

export default function StudyDesignerPage() {
  return (
    <StudyDesignerProvider>
      <StudyDesignerContent />
    </StudyDesignerProvider>
  )
}





















