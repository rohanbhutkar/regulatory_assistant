"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ConfidenceIntervalChart } from '@/components/charts/confidence-interval-chart'
import { RiskFactorsChart } from '@/components/charts/risk-factors-chart'
import { useAPIPost } from '@/lib/hooks/use-api'
import { useStudyDesigner } from '@/lib/contexts/study-designer-context'
import { Loader2, TrendingUp, AlertTriangle, Calendar, DollarSign, Target, Sparkles, Info } from 'lucide-react'
import { toast } from 'sonner'

interface SimulationResponse {
  success: boolean
  simulation_id: string
  enrollment_curve: Array<{
    month: number
    enrolled_mean: number
    enrolled_p10: number
    enrolled_p50: number
    enrolled_p90: number
    cumulative_mean: number
    cumulative_p10: number
    cumulative_p50: number
    cumulative_p90: number
  }>
  milestones: Array<{
    name: string
    date: string
    date_range: {
      p10: string
      p50: string
      p90: string
    }
    probability: number
    status: string
  }>
  risk_factors: Array<{
    factor: string
    probability: number
    impact: string
    mitigation: string
    severity: 'Low' | 'Medium' | 'High'
  }>
  risk_assessment: string
  success_probability: number
  expected_completion_date: string
  expected_duration_months: number
  budget_projection: number
  budget_details: {
    total_cost: number
    cost_per_patient: number
    breakdown: {
      patient_costs: number
      site_costs: number
      monitoring_costs: number
      overhead: number
    }
    monthly_burn_rate: number
  }
  confidence_interval: {
    completion_time_p10: number
    completion_time_p50: number
    completion_time_p90: number
  }
  summary_statistics: {
    mean_enrollment_rate: number
    mean_screen_failure_rate: number
    mean_dropout_rate: number
    mean_site_activation_weeks: number
    probability_on_time: number
    probability_delayed: number
    mean_final_enrolled?: number
    mean_sites_depleted?: number
    mean_total_screened?: number
    mean_regulatory_delays_months?: number
    probability_regulatory_event?: number
  }
  model_assumptions?: {
    simulation_approach: string
    iterations: number
    target_enrollment: number
    timeline_months: number
    number_of_sites: number
    number_of_countries?: number
    countries?: string[]
    budget_tracking_enabled?: boolean
    total_budget?: number
    site_parameters: Record<string, any>
    global_parameters: Record<string, any>
    learning_curve: Record<string, any>
    seasonal_effects: Record<string, any>
    stochastic_variation: Record<string, any>
    curve_drivers: Record<string, any>
    data_sources?: Record<string, any>
  }
  simulation_type?: 'enhanced' | 'advanced'
  country_performance_summary?: Array<{
    country_code: string
    country_name: string
    sites: number
    total_enrolled: number
    regulatory_status: string
  }>
  budget_exhaustion_probability?: number
  regulatory_event_summary?: {
    clinical_holds: number
    protocol_amendments: number
    regulatory_audits: number
    site_audits: number
  }
  operational_metrics?: {
    cra_utilization: number
    dm_utilization: number
    average_queries_per_site: number
    site_monitoring_coverage: number
  }
}

export function EnhancedSimulationTab() {
  const { 
    studyContext, 
    selectedSites, 
    selectedTrials, 
    inclusionCriteria, 
    exclusionCriteria,
    setSimulationResult 
  } = useStudyDesigner()
  const [parameters, setParameters] = useState({
    enrollmentTarget: 300,
    timelineMonths: 24,
    screenFailureRate: 0.30,
    dropoutRate: 0.10
  })
  const [advancedOptions, setAdvancedOptions] = useState({
    useAdvanced: false,
    totalBudget: null as number | null,
    enableCountryModeling: true,
    enableBudgetConstraints: false,
    enableRegulatoryEvents: true,
    enableOperationalConstraints: true,
    enableExternalShocks: true
  })
  const [aiRecommendations, setAiRecommendations] = useState<{
    enrollmentTarget?: number
    timelineMonths?: number
    screenFailureRate?: number
    dropoutRate?: number
    reasoning?: string | {
      enrollmentTarget?: string
      timeline?: string
      screenFailure?: string
      dropout?: string
    }
  } | null>(null)
  const [generatingRecommendations, setGeneratingRecommendations] = useState(false)
  const [justUpdated, setJustUpdated] = useState(false)

  const {
    execute: runSimulation,
    loading,
    data: simulationData,
    error
  } = useAPIPost<SimulationResponse>('/api/analysis/simulation/run')

  // Clear the "just updated" flag after animation
  useEffect(() => {
    if (justUpdated) {
      const timer = setTimeout(() => setJustUpdated(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [justUpdated])

  // Auto-save simulation results to context when they're loaded
  useEffect(() => {
    if (simulationData && simulationData.success) {
      console.log('💾 Auto-saving simulation results to context:', {
        simulation_id: simulationData.simulation_id,
        success_probability: simulationData.success_probability,
        expected_duration: simulationData.expected_duration_months
      })
      setSimulationResult(simulationData)
      toast.success('Simulation results saved automatically')
    }
  }, [simulationData, setSimulationResult])

  const calculatePopulationFromIE = () => {
    // Use the inclusionCriteria and exclusionCriteria from the hook above
    console.log('📊 Calculating population from IE criteria:', {
      inclusionCount: inclusionCriteria?.length || 0,
      exclusionCount: exclusionCriteria?.length || 0,
      sitesCount: selectedSites?.length || 0
    })
    
    // Calculate final eligible population from IE criteria
    let finalEligible = 0
    let totalPopulation = 0
    
    // Null safety: check if arrays exist
    if (inclusionCriteria && Array.isArray(inclusionCriteria) && inclusionCriteria.length > 0) {
      // Get the last inclusion criterion's populationAfter
      const lastInclusion = [...inclusionCriteria]
        .reverse()
        .find(c => c && c.enabled !== false && c.populationAfter)
      
      if (lastInclusion) {
        finalEligible = lastInclusion.populationAfter || 0
        // Get initial population from first criterion
        totalPopulation = inclusionCriteria[0]?.populationBefore || 0
      }
    }
    
    // Apply exclusion criteria
    if (exclusionCriteria && Array.isArray(exclusionCriteria) && exclusionCriteria.length > 0 && finalEligible > 0) {
      const lastExclusion = [...exclusionCriteria]
        .reverse()
        .find(c => c && c.enabled !== false && c.populationAfter)
      
      if (lastExclusion) {
        finalEligible = lastExclusion.populationAfter || finalEligible
      }
    }
    
    // Calculate population by state (simplified - equal distribution)
    const population_by_state: Record<string, number> = {}
    
    // Null safety: check if selectedSites exists and is an array
    if (finalEligible > 0 && selectedSites && Array.isArray(selectedSites) && selectedSites.length > 0) {
      // Get unique states from selected sites (using correct property names)
      const states = [...new Set(selectedSites.map((s: any) => s?.state || s?.State).filter(Boolean))]
      
      if (states.length > 0) {
        // Distribute population proportionally by number of sites per state
        const sitesByState: Record<string, number> = {}
        selectedSites.forEach((site: any) => {
          const siteState = site?.state || site?.State
          if (site && siteState) {
            sitesByState[siteState] = (sitesByState[siteState] || 0) + 1
          }
        })
        
        // Calculate proportional distribution
        const totalSites = selectedSites.length
        states.forEach(state => {
          const sitesInState = sitesByState[state] || 0
          population_by_state[state] = Math.round((finalEligible * sitesInState) / totalSites)
        })
      }
    }
    
    const result = {
      eligible_population: {
        total: totalPopulation,
        final_eligible: finalEligible,
        us_population: 330000000, // US population constant
        ta_population: totalPopulation
      },
      population_by_state
    }
    
    console.log('✅ Population data calculated:', {
      finalEligible,
      totalPopulation,
      statesCount: Object.keys(population_by_state).length,
      populationByState: population_by_state
    })
    
    return result
  }

  const handleGenerateRecommendations = async () => {
    if (!studyContext.indication || !studyContext.phase) {
      toast.error('Please fill in Basic Info (indication and phase) first')
      return
    }

    setGeneratingRecommendations(true)
    
    try {
      // Generate AI recommendations based on study context and reference trials
      const recommendations = await generateSimulationParameters()
      
      console.log('📝 AI Recommendations received:', recommendations)
      console.log('   - enrollmentTarget:', recommendations?.enrollmentTarget, typeof recommendations?.enrollmentTarget)
      console.log('   - timelineMonths:', recommendations?.timelineMonths, typeof recommendations?.timelineMonths)
      console.log('   - screenFailureRate:', recommendations?.screenFailureRate, typeof recommendations?.screenFailureRate)
      console.log('   - dropoutRate:', recommendations?.dropoutRate, typeof recommendations?.dropoutRate)
      
      setAiRecommendations(recommendations)
      
      // Only update parameters if we got valid recommendations
      if (!recommendations) {
        toast.error('No recommendations received from AI')
        return
      }
      
      // Update parameters with recommendations - ensure we have numbers
      const updatedParams = {
        enrollmentTarget: typeof recommendations.enrollmentTarget === 'number' && recommendations.enrollmentTarget > 0 
          ? recommendations.enrollmentTarget 
          : parameters.enrollmentTarget,
        timelineMonths: typeof recommendations.timelineMonths === 'number' && recommendations.timelineMonths > 0 
          ? recommendations.timelineMonths 
          : parameters.timelineMonths,
        screenFailureRate: typeof recommendations.screenFailureRate === 'number' && recommendations.screenFailureRate >= 0 
          ? recommendations.screenFailureRate 
          : parameters.screenFailureRate,
        dropoutRate: typeof recommendations.dropoutRate === 'number' && recommendations.dropoutRate >= 0 
          ? recommendations.dropoutRate 
          : parameters.dropoutRate
      }
      
      console.log('✅ Updating parameters to:', updatedParams)
      setParameters(updatedParams)
      setJustUpdated(true)  // Trigger visual feedback
      
      toast.success(`AI recommendations applied: ${updatedParams.enrollmentTarget} patients, ${updatedParams.timelineMonths} months`)
    } catch (error) {
      console.error('Error generating recommendations:', error)
      toast.error('Failed to generate AI recommendations')
    } finally {
      setGeneratingRecommendations(false)
    }
  }

  const generateSimulationParameters = async () => {
    // Call backend AI endpoint to generate intelligent parameters
    try {
      console.log("🤖 Calling AI to generate complete simulation configuration...")
      
      // Calculate population data from IE criteria
      const populationData = calculatePopulationFromIE()
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/analysis/simulation/generate-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          study_design: {
            phase: studyContext.phase || 'Phase II',
            therapeuticArea: studyContext.therapeuticArea || '',
            indication: studyContext.indication || '',
            referenceTrials: (selectedTrials && Array.isArray(selectedTrials) ? selectedTrials.slice(0, 10) : []).map(t => ({
              phase: t?.phase || 'Unknown',
              enrollment: t?.total_enrollment || t?.target_accrual || t?.actualAccrual || t?.targetAccrual || 0,
              duration: t?.enrollment_duration_mos || t?.enrollmentDuration || 0,
              sites: t?.reported_sites || t?.identifiedSites || t?.reportedSites || t?.identified_sites || 0
            }))
          },
          sites: (selectedSites && Array.isArray(selectedSites) ? selectedSites : []).map(s => ({
            id: s?.site_id || s?.id || '',
            name: s?.site_name || s?.name || 'Unknown',
            state: s?.state || s?.State || '',
            country: s?.country || s?.Country || 'US',
            total_trials: s?.historical_trials || s?.total_trials || 0,
            ongoing_trials: s?.ongoing_trials || 0,
            avg_enrollment: s?.avg_enrollment || 0,
            organization_type: s?.organization_type || 'Unknown'
          })),
          eligible_population: populationData.eligible_population,
          population_by_state: populationData.population_by_state,
          overall_design: studyContext.totalParticipants ? {
            numberOfArms: studyContext.numberOfArms || 2,
            totalParticipants: studyContext.totalParticipants,
            studyDuration: studyContext.duration_months || 24
          } : undefined,
          endpoints: [], // Could populate from context if available
          inclusion_criteria: [] // Could populate from context if available
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      console.log("✅ AI-generated configuration (raw):", JSON.stringify(data, null, 2))
      
      // Backend returns camelCase keys
      return {
        enrollmentTarget: data.enrollmentTarget,
        timelineMonths: data.timelineMonths,
        screenFailureRate: data.screenFailureRate,
        dropoutRate: data.dropoutRate,
        estimatedBudget: data.estimatedBudget,
        siteParameters: data.siteParameters,
        riskFactors: data.riskFactors,
        reasoning: data.reasoning  // Can be string or object with detailed explanations
      }
      
    } catch (error) {
      console.error("❌ Failed to call AI parameter endpoint:", error)
      
      // Fallback to basic defaults if API fails
      const phaseDefaults: Record<string, any> = {
        'Phase I': { target: 30, months: 12, screenFailure: 0.40, dropout: 0.15 },
        'Phase II': { target: 100, months: 18, screenFailure: 0.35, dropout: 0.12 },
        'Phase III': { target: 500, months: 36, screenFailure: 0.30, dropout: 0.10 },
        'Phase IV': { target: 1000, months: 24, screenFailure: 0.25, dropout: 0.08 }
      }
      
      const defaults = phaseDefaults[studyContext.phase || 'Phase II'] || phaseDefaults['Phase II']
      
      return {
        enrollmentTarget: defaults.target,
        timelineMonths: defaults.months,
        screenFailureRate: defaults.screenFailure,
        dropoutRate: defaults.dropout,
        reasoning: 'Using default values (AI service unavailable)'
      }
    }
  }

  const handleRunSimulation = async () => {
    try {
      // Calculate population data from IE criteria
      const populationData = calculatePopulationFromIE()
      
      const requestBody: any = {
        study_design: {
          phase: studyContext.phase || 'Phase II',
          therapeuticArea: studyContext.therapeuticArea || '',
          indication: studyContext.indication || '',
          referenceTrials: (selectedTrials && Array.isArray(selectedTrials) ? selectedTrials.slice(0, 10) : []).map(t => ({
            trial_title: t?.trial_title || '',
            phase: t?.phase || 'Unknown',
            ptsPerSitePerMonth: t?.pts_per_site_per_month || 0,
            enrollmentDuration: t?.enrollment_duration_mos || 0
          }))
        },
        sites: (selectedSites && Array.isArray(selectedSites) ? selectedSites : []).map(s => ({
          // Spread all existing properties
          ...s,
          // Normalize property names for backend
          id: s?.site_id || s?.id,
          name: s?.site_name || s?.name || 'Unknown',
          state: s?.state || s?.State,
          country: s?.country || s?.Country || 'US',
          total_trials: s?.historical_trials || s?.total_trials || 0
        })),
        enrollment_target: parameters.enrollmentTarget,
        timeline_months: parameters.timelineMonths,
        budget_constraints: {
          screen_failure_rate: parameters.screenFailureRate,
          dropout_rate: parameters.dropoutRate
        },
        // Include IE criteria population data
        eligible_population: populationData.eligible_population,
        population_by_state: populationData.population_by_state
      }
      
      // Add advanced options if enabled
      if (advancedOptions.useAdvanced || advancedOptions.totalBudget) {
        requestBody.use_advanced_simulation = advancedOptions.useAdvanced
        requestBody.total_budget = advancedOptions.totalBudget
        requestBody.enable_country_modeling = advancedOptions.enableCountryModeling
        requestBody.enable_budget_constraints = advancedOptions.enableBudgetConstraints
        requestBody.enable_regulatory_events = advancedOptions.enableRegulatoryEvents
        requestBody.enable_operational_constraints = advancedOptions.enableOperationalConstraints
        requestBody.enable_external_shocks = advancedOptions.enableExternalShocks
      }
      
      console.log('🚀 Sending simulation request:', {
        sitesCount: requestBody.sites.length,
        enrollmentTarget: requestBody.enrollment_target,
        timelineMonths: requestBody.timeline_months,
        hasIEData: !!requestBody.eligible_population,
        finalEligible: requestBody.eligible_population?.final_eligible,
        statesCount: Object.keys(requestBody.population_by_state || {}).length
      })
      
      // Use a longer timeout for Monte Carlo simulations (5 minutes)
      // Simulations with 5000 iterations can take 1-3 minutes
      const result = await runSimulation(requestBody, {
        timeout: 300000 // 5 minutes in milliseconds
      })

      if (result && result.success) {
        const successProb = result.success_probability?.toFixed(1) ?? 'N/A'
        // Don't show duplicate success toast - auto-save useEffect will handle it
        console.log(`✅ Simulation completed with ${successProb}% success probability`)
      }
    } catch (err: any) {
      // Silently ignore cancelled requests (this happens when user clicks again while request is in progress)
      if (err?.code === 'REQUEST_CANCELLED' || err?.message?.includes('cancelled')) {
        console.log('Simulation request cancelled (new request started)')
        return
      }
      
      // Check for timeout errors
      if (err?.code === 'REQUEST_TIMEOUT') {
        toast.error('Simulation timed out. The backend may still be processing. Please wait a moment and check results.')
        console.error('Simulation timeout:', err)
        return
      }
      
      // Only show error for actual failures
      toast.error('Failed to run simulation')
      console.error(err)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Monte Carlo Simulation Parameters</CardTitle>
              <CardDescription>
                Configure simulation parameters for realistic enrollment prediction (5,000 iterations)
              </CardDescription>
            </div>
            <Button
              onClick={handleGenerateRecommendations}
              disabled={generatingRecommendations || !studyContext.indication || !studyContext.phase}
              variant="outline"
              className="gap-2"
            >
              {generatingRecommendations ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  AI Draft Parameters
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* AI Recommendations Alert */}
          {aiRecommendations && aiRecommendations.reasoning && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                <strong>AI Recommendations:</strong>
                {typeof aiRecommendations.reasoning === 'string' ? (
                  <div className="mt-2 text-sm">{aiRecommendations.reasoning}</div>
                ) : typeof aiRecommendations.reasoning === 'object' ? (
                  <div className="mt-2 space-y-1 text-sm">
                    {aiRecommendations.reasoning.enrollmentTarget && (
                      <div><strong>Enrollment Target:</strong> {aiRecommendations.reasoning.enrollmentTarget}</div>
                    )}
                    {aiRecommendations.reasoning.timeline && (
                      <div><strong>Timeline:</strong> {aiRecommendations.reasoning.timeline}</div>
                    )}
                    {aiRecommendations.reasoning.screenFailure && (
                      <div><strong>Screen Failure:</strong> {aiRecommendations.reasoning.screenFailure}</div>
                    )}
                    {aiRecommendations.reasoning.dropout && (
                      <div><strong>Dropout:</strong> {aiRecommendations.reasoning.dropout}</div>
                    )}
                  </div>
                ) : null}
                <span className="text-xs text-muted-foreground mt-2 block">
                  Based on {studyContext.phase || 'Phase II'} trials in {studyContext.therapeuticArea || 'general'} {studyContext.indication || 'indication'}
                  {selectedTrials && selectedTrials.length > 0 && ` and ${selectedTrials.length} reference trials`}
                  {selectedSites && selectedSites.length > 0 && ` with ${selectedSites.length} selected sites`}.
                  You can adjust these parameters before running the simulation.
                </span>
              </AlertDescription>
            </Alert>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="enrollmentTarget" className="flex items-center gap-2">
                Target Enrollment
                {aiRecommendations && (
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Sparkles className="h-3 w-3" />
                    AI
                  </Badge>
                )}
              </Label>
              <Input
                id="enrollmentTarget"
                type="number"
                value={parameters.enrollmentTarget}
                onChange={(e) => setParameters({ ...parameters, enrollmentTarget: parseInt(e.target.value) || 300 })}
                className={`${aiRecommendations ? 'border-blue-500/50' : ''} ${justUpdated ? 'ring-2 ring-blue-500 animate-pulse' : ''}`}
              />
              <p className="text-xs text-muted-foreground">
                Patients to enroll
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="timelineMonths" className="flex items-center gap-2">
                Enrollment Timeline (Months)
                {aiRecommendations && (
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Sparkles className="h-3 w-3" />
                    AI
                  </Badge>
                )}
              </Label>
              <Input
                id="timelineMonths"
                type="number"
                value={parameters.timelineMonths}
                onChange={(e) => setParameters({ ...parameters, timelineMonths: parseInt(e.target.value) || 24 })}
                className={`${aiRecommendations ? 'border-blue-500/50' : ''} ${justUpdated ? 'ring-2 ring-blue-500 animate-pulse' : ''}`}
              />
              <p className="text-xs text-muted-foreground">
                Expected enrollment duration (not total trial)
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="screenFailureRate" className="flex items-center gap-2">
                Screen Failure Rate
                {aiRecommendations && (
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Sparkles className="h-3 w-3" />
                    AI
                  </Badge>
                )}
              </Label>
              <Input
                id="screenFailureRate"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={parameters.screenFailureRate}
                onChange={(e) => setParameters({ ...parameters, screenFailureRate: parseFloat(e.target.value) || 0.30 })}
                className={`${aiRecommendations ? 'border-blue-500/50' : ''} ${justUpdated ? 'ring-2 ring-blue-500 animate-pulse' : ''}`}
              />
              <p className="text-xs text-muted-foreground">{(parameters.screenFailureRate * 100).toFixed(0)}% of screened patients fail</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="dropoutRate" className="flex items-center gap-2">
                Dropout Rate
                {aiRecommendations && (
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Sparkles className="h-3 w-3" />
                    AI
                  </Badge>
                )}
              </Label>
              <Input
                id="dropoutRate"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={parameters.dropoutRate}
                onChange={(e) => setParameters({ ...parameters, dropoutRate: parseFloat(e.target.value) || 0.10 })}
                className={`${aiRecommendations ? 'border-blue-500/50' : ''} ${justUpdated ? 'ring-2 ring-blue-500 animate-pulse' : ''}`}
              />
              <p className="text-xs text-muted-foreground">{(parameters.dropoutRate * 100).toFixed(0)}% of enrolled patients dropout</p>
            </div>
          </div>

          <Button 
            onClick={handleRunSimulation} 
            disabled={loading}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running Monte Carlo Simulation...
              </>
            ) : (
              <>
                <TrendingUp className="mr-2 h-4 w-4" />
                Run Monte Carlo Simulation
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      {simulationData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Success Probability</span>
              </div>
              <div className={`text-3xl font-bold ${
                (simulationData.success_probability ?? 0) >= 80 ? 'text-green-600' :
                (simulationData.success_probability ?? 0) >= 60 ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {simulationData.success_probability?.toFixed(1) ?? 'N/A'}%
              </div>
              <Badge 
                variant={(simulationData.success_probability ?? 0) >= 80 ? 'default' : 'destructive'}
                className="mt-2"
              >
                {simulationData.risk_assessment || 'Unknown'} Risk
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Predicted Enrollment Duration</span>
              </div>
              <div className="text-3xl font-bold">
                {simulationData.expected_duration_months?.toFixed(1) ?? 'N/A'}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                months (P50: {simulationData.confidence_interval?.completion_time_p50?.toFixed(1) ?? 'N/A'})
              </p>
              {simulationData.expected_duration_months && parameters.timelineMonths && (
                <div className="mt-2">
                  {simulationData.expected_duration_months < parameters.timelineMonths * 0.7 ? (
                    <Badge variant="default" className="text-xs">
                      ✓ {((parameters.timelineMonths - simulationData.expected_duration_months) / parameters.timelineMonths * 100).toFixed(0)}% faster than planned
                    </Badge>
                  ) : simulationData.expected_duration_months > parameters.timelineMonths * 1.2 ? (
                    <Badge variant="destructive" className="text-xs">
                      ⚠ {((simulationData.expected_duration_months - parameters.timelineMonths) / parameters.timelineMonths * 100).toFixed(0)}% slower than planned
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">
                      ≈ On target
                    </Badge>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Total Budget</span>
              </div>
              <div className="text-3xl font-bold">
                {formatCurrency(simulationData.budget_projection)}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {formatCurrency(simulationData.budget_details.cost_per_patient)}/patient
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">On-Time Probability</span>
              </div>
              <div className={`text-3xl font-bold ${
                (simulationData.summary_statistics?.probability_on_time ?? 0) >= 0.7 ? 'text-green-600' :
                (simulationData.summary_statistics?.probability_on_time ?? 0) >= 0.5 ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {simulationData.summary_statistics?.probability_on_time
                  ? (simulationData.summary_statistics.probability_on_time * 100).toFixed(1) + '%'
                  : 'N/A'}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                within {parameters.timelineMonths} months
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      {simulationData ? (
        <Tabs defaultValue="enrollment" className="space-y-4">
          <TabsList className={`grid ${simulationData.simulation_type === 'advanced' ? 'grid-cols-9' : 'grid-cols-6'} w-full`}>
            <TabsTrigger value="enrollment">Enrollment</TabsTrigger>
            <TabsTrigger value="risks">Risks</TabsTrigger>
            <TabsTrigger value="milestones">Milestones</TabsTrigger>
            <TabsTrigger value="budget">Budget</TabsTrigger>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="model">Model</TabsTrigger>
            {simulationData.simulation_type === 'advanced' && (
              <>
                <TabsTrigger value="countries">Countries</TabsTrigger>
                <TabsTrigger value="regulatory">Regulatory</TabsTrigger>
                <TabsTrigger value="operational">Operational</TabsTrigger>
              </>
            )}
          </TabsList>

          {/* Enrollment Curves */}
          <TabsContent value="enrollment" className="space-y-4">
            <ConfidenceIntervalChart
              data={simulationData.enrollment_curve.map(point => ({
                month: point.month,
                mean: point.cumulative_mean,
                p10: point.cumulative_p10,
                p50: point.cumulative_p50,
                p90: point.cumulative_p90
              }))}
              title="Cumulative Enrollment Projection"
              description="Monte Carlo simulation with confidence intervals (5,000 iterations)"
              yAxisLabel="Cumulative Patients Enrolled"
            />

            <ConfidenceIntervalChart
              data={simulationData.enrollment_curve.map(point => ({
                month: point.month,
                mean: point.enrolled_mean,
                p10: point.enrolled_p10,
                p50: point.enrolled_p50,
                p90: point.enrolled_p90
              }))}
              title="Monthly Enrollment Rate"
              description="New patients enrolled per month with uncertainty"
              yAxisLabel="Patients Enrolled (Monthly)"
            />
          </TabsContent>

          {/* Risk Factors */}
          <TabsContent value="risks">
            <RiskFactorsChart riskFactors={simulationData.risk_factors} />
          </TabsContent>

          {/* Milestones */}
          <TabsContent value="milestones">
            <Card>
              <CardHeader>
                <CardTitle>Key Milestones with Uncertainty</CardTitle>
                <CardDescription>
                  Predicted milestone dates with 10th, 50th, and 90th percentiles
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {simulationData.milestones.map((milestone, index) => (
                  <div key={index} className="border border-border rounded-lg p-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold text-lg">{milestone.name}</h4>
                        <p className="text-sm text-muted-foreground mt-1">
                          Expected: {formatDate(milestone.date)}
                        </p>
                      </div>
                      <Badge variant={(milestone.probability ?? 0) >= 0.8 ? 'default' : 'secondary'}>
                        {milestone.probability 
                          ? (milestone.probability * 100).toFixed(0) + '% likely'
                          : 'N/A'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Optimistic (P10)</p>
                        <p className="font-medium">{formatDate(milestone.date_range.p10)}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Most Likely (P50)</p>
                        <p className="font-medium">{formatDate(milestone.date_range.p50)}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Pessimistic (P90)</p>
                        <p className="font-medium">{formatDate(milestone.date_range.p90)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Budget */}
          <TabsContent value="budget" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Budget Breakdown</CardTitle>
                <CardDescription>
                  Detailed cost analysis based on simulation results
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">Patient Costs</p>
                    <p className="text-2xl font-bold">
                      {formatCurrency(simulationData.budget_details.breakdown.patient_costs)}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">Site Costs</p>
                    <p className="text-2xl font-bold">
                      {formatCurrency(simulationData.budget_details.breakdown.site_costs)}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">Monitoring</p>
                    <p className="text-2xl font-bold">
                      {formatCurrency(simulationData.budget_details.breakdown.monitoring_costs)}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">Overhead</p>
                    <p className="text-2xl font-bold">
                      {formatCurrency(simulationData.budget_details.breakdown.overhead)}
                    </p>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-lg font-semibold">Total Budget</span>
                    <span className="text-2xl font-bold text-primary">
                      {formatCurrency(simulationData.budget_details.total_cost)}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Monthly burn rate: {formatCurrency(simulationData.budget_details.monthly_burn_rate)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Statistics */}
          <TabsContent value="statistics">
            <Card>
              <CardHeader>
                <CardTitle>Simulation Statistics</CardTitle>
                <CardDescription>
                  Detailed metrics from Monte Carlo simulation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Mean Enrollment Rate</p>
                    <p className="text-2xl font-bold">
                      {simulationData.summary_statistics?.mean_enrollment_rate?.toFixed(2) ?? 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">patients/site/month</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Screen Failure Rate</p>
                    <p className="text-2xl font-bold">
                      {simulationData.summary_statistics?.mean_screen_failure_rate 
                        ? (simulationData.summary_statistics.mean_screen_failure_rate * 100).toFixed(1) + '%'
                        : 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">average across simulations</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Dropout Rate</p>
                    <p className="text-2xl font-bold">
                      {simulationData.summary_statistics?.mean_dropout_rate
                        ? (simulationData.summary_statistics.mean_dropout_rate * 100).toFixed(1) + '%'
                        : 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">average across simulations</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Site Activation</p>
                    <p className="text-2xl font-bold">
                      {simulationData.summary_statistics?.mean_site_activation_weeks?.toFixed(1) ?? 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">weeks average</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Completion Time (P10)</p>
                    <p className="text-2xl font-bold text-green-600">
                      {simulationData.confidence_interval?.completion_time_p10?.toFixed(1) ?? 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">months (optimistic)</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Completion Time (P90)</p>
                    <p className="text-2xl font-bold text-red-600">
                      {simulationData.confidence_interval?.completion_time_p90?.toFixed(1) ?? 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">months (pessimistic)</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Final Enrolled</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {simulationData.summary_statistics?.mean_final_enrolled?.toFixed(0) ?? 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">patients (mean across simulations)</p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground mb-2">Sites Depleted</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {simulationData.summary_statistics?.mean_sites_depleted?.toFixed(1) ?? 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">average sites exhausted</p>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <p className="text-xs text-muted-foreground">
                    Simulation ID: {simulationData.simulation_id}
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Model Parameters & Assumptions */}
          <TabsContent value="model">
            {simulationData.model_assumptions ? (
              <div className="space-y-4">
                {/* Overview Card */}
                <Card>
                  <CardHeader>
                    <CardTitle>Simulation Model Overview</CardTitle>
                    <CardDescription>
                      {simulationData.model_assumptions.simulation_approach}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-4 gap-4">
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground mb-1">Iterations</p>
                        <p className="text-2xl font-bold">{simulationData.model_assumptions.iterations.toLocaleString()}</p>
                      </div>
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground mb-1">Target Enrollment</p>
                        <p className="text-2xl font-bold">{simulationData.model_assumptions.target_enrollment}</p>
                      </div>
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground mb-1">Timeline</p>
                        <p className="text-2xl font-bold">{simulationData.model_assumptions.timeline_months} mo</p>
                      </div>
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground mb-1">Sites</p>
                        <p className="text-2xl font-bold">{simulationData.model_assumptions.number_of_sites}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Data Sources */}
                {simulationData.model_assumptions.data_sources && (
                  <Card className="border-blue-500/50 bg-blue-50/50 dark:bg-blue-950/20">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Info className="h-5 w-5 text-blue-600" />
                        Data Sources & Integration
                      </CardTitle>
                      <CardDescription>
                        This simulation uses real site data and study context
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="border border-blue-200 dark:border-blue-800 rounded-lg p-4 bg-white dark:bg-gray-900">
                          <p className="text-sm font-semibold mb-2 text-blue-700 dark:text-blue-400">Site Selection Data</p>
                          <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.data_sources.site_selection}</p>
                        </div>

                        <div className="border border-blue-200 dark:border-blue-800 rounded-lg p-4 bg-white dark:bg-gray-900">
                          <p className="text-sm font-semibold mb-2 text-blue-700 dark:text-blue-400">Reference Trials</p>
                          <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.data_sources.reference_trials}</p>
                        </div>

                        <div className="border border-blue-200 dark:border-blue-800 rounded-lg p-4 bg-white dark:bg-gray-900">
                          <p className="text-sm font-semibold mb-2 text-blue-700 dark:text-blue-400">Study Context</p>
                          <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.data_sources.study_context}</p>
                        </div>

                        <div className="border border-blue-200 dark:border-blue-800 rounded-lg p-4 bg-white dark:bg-gray-900">
                          <p className="text-sm font-semibold mb-2 text-blue-700 dark:text-blue-400">Integration Approach</p>
                          <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.data_sources.integration}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Site Parameters */}
                <Card>
                  <CardHeader>
                    <CardTitle>Site-Level Parameters</CardTitle>
                    <CardDescription>Each site has unique characteristics (heterogeneity)</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-2">Enrollment Rates</p>
                        <p className="text-xs text-muted-foreground mb-1">Mean: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.enrollment_rates.mean}</span> {simulationData.model_assumptions.site_parameters.enrollment_rates.unit}</p>
                        <p className="text-xs text-muted-foreground mb-1">Std Dev: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.enrollment_rates.std}</span></p>
                        <p className="text-xs text-muted-foreground mb-1">Range: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.enrollment_rates.min} - {simulationData.model_assumptions.site_parameters.enrollment_rates.max}</span></p>
                      </div>

                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-2">Experience Scores</p>
                        <p className="text-xs text-muted-foreground mb-1">Mean: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.experience_scores.mean}</span> ({simulationData.model_assumptions.site_parameters.experience_scores.scale})</p>
                        <p className="text-xs text-muted-foreground mb-1">Range: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.experience_scores.min} - {simulationData.model_assumptions.site_parameters.experience_scores.max}</span></p>
                        <p className="text-xs text-muted-foreground mt-2">Higher experience = faster learning curve</p>
                      </div>

                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-2">Activation Delays</p>
                        <p className="text-xs text-muted-foreground mb-1">Mean: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.activation_delays.mean_weeks} weeks</span></p>
                        <p className="text-xs text-muted-foreground mb-1">Std Dev: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.activation_delays.std_weeks} weeks</span></p>
                        <p className="text-xs text-muted-foreground mb-1">Range: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.activation_delays.min_weeks} - {simulationData.model_assumptions.site_parameters.activation_delays.max_weeks} weeks</span></p>
                      </div>

                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-2">Patient Populations</p>
                        <p className="text-xs text-muted-foreground mb-1">Mean: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.patient_populations.mean.toLocaleString()}</span> ± {simulationData.model_assumptions.site_parameters.patient_populations.std?.toLocaleString() || 'N/A'}</p>
                        <p className="text-xs text-muted-foreground mb-1">Range: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.patient_populations.min?.toLocaleString() || 'N/A'} - {simulationData.model_assumptions.site_parameters.patient_populations.max?.toLocaleString() || 'N/A'}</span></p>
                        <p className="text-xs text-muted-foreground mb-1">Total Available: <span className="font-semibold">{simulationData.model_assumptions.site_parameters.patient_populations.total.toLocaleString()}</span></p>
                        <p className="text-xs text-muted-foreground mt-2">Expected Utilization: <span className="font-semibold text-blue-600">{simulationData.model_assumptions.site_parameters.patient_populations.utilization_estimate || 'N/A'}</span></p>
                      </div>
                    </div>

                    {/* Site-Specific Rates */}
                    {(simulationData.model_assumptions.site_parameters.screen_failure_rates || simulationData.model_assumptions.site_parameters.dropout_rates) && (
                      <div className="grid grid-cols-2 gap-4 mt-4">
                        {simulationData.model_assumptions.site_parameters.screen_failure_rates && (
                          <div className="border border-border rounded-lg p-4">
                            <p className="text-sm font-semibold mb-2">Screen Failure Rates (Site-Specific)</p>
                            <p className="text-xs text-muted-foreground mb-1">Mean: <span className="font-semibold">{(simulationData.model_assumptions.site_parameters.screen_failure_rates.mean * 100).toFixed(1)}%</span></p>
                            <p className="text-xs text-muted-foreground mb-1">Std Dev: <span className="font-semibold">±{(simulationData.model_assumptions.site_parameters.screen_failure_rates.std * 100).toFixed(1)}%</span></p>
                            <p className="text-xs text-muted-foreground">Range: <span className="font-semibold">{(simulationData.model_assumptions.site_parameters.screen_failure_rates.min * 100).toFixed(1)}% - {(simulationData.model_assumptions.site_parameters.screen_failure_rates.max * 100).toFixed(1)}%</span></p>
                          </div>
                        )}

                        {simulationData.model_assumptions.site_parameters.dropout_rates && (
                          <div className="border border-border rounded-lg p-4">
                            <p className="text-sm font-semibold mb-2">Dropout Rates (Site-Specific)</p>
                            <p className="text-xs text-muted-foreground mb-1">Mean: <span className="font-semibold">{(simulationData.model_assumptions.site_parameters.dropout_rates.mean * 100).toFixed(1)}%</span></p>
                            <p className="text-xs text-muted-foreground mb-1">Std Dev: <span className="font-semibold">±{(simulationData.model_assumptions.site_parameters.dropout_rates.std * 100).toFixed(1)}%</span></p>
                            <p className="text-xs text-muted-foreground">Range: <span className="font-semibold">{(simulationData.model_assumptions.site_parameters.dropout_rates.min * 100).toFixed(1)}% - {(simulationData.model_assumptions.site_parameters.dropout_rates.max * 100).toFixed(1)}%</span></p>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Global Parameters */}
                <Card>
                  <CardHeader>
                    <CardTitle>Global Parameters</CardTitle>
                    <CardDescription>Trial-wide rates with site-specific variation</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="border border-border rounded-lg p-4">
                      <p className="text-sm font-semibold mb-1">Screen Failure Rate</p>
                      <p className="text-lg font-bold">{(simulationData.model_assumptions.global_parameters.screen_failure_rate.mean * 100).toFixed(1)}% ± {(simulationData.model_assumptions.global_parameters.screen_failure_rate.std * 100).toFixed(1)}%</p>
                      <p className="text-xs text-muted-foreground mt-1">{simulationData.model_assumptions.global_parameters.screen_failure_rate.description}</p>
                    </div>

                    <div className="border border-border rounded-lg p-4">
                      <p className="text-sm font-semibold mb-1">Dropout Rate</p>
                      <p className="text-lg font-bold">{(simulationData.model_assumptions.global_parameters.dropout_rate.mean * 100).toFixed(1)}% ± {(simulationData.model_assumptions.global_parameters.dropout_rate.std * 100).toFixed(1)}%</p>
                      <p className="text-xs text-muted-foreground mt-1">{simulationData.model_assumptions.global_parameters.dropout_rate.description}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Learning Curve */}
                <Card>
                  <CardHeader>
                    <CardTitle>Learning Curve Model</CardTitle>
                    <CardDescription>Sites improve efficiency over time</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="border border-border rounded-lg p-4">
                      <p className="text-sm mb-3">{simulationData.model_assumptions.learning_curve.description}</p>
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground">Start Efficiency</p>
                          <p className="text-lg font-bold">{simulationData.model_assumptions.learning_curve.start_efficiency}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Duration</p>
                          <p className="text-lg font-bold">{simulationData.model_assumptions.learning_curve.duration_weeks} weeks</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">End Efficiency</p>
                          <p className="text-lg font-bold">{simulationData.model_assumptions.learning_curve.end_efficiency}</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Seasonal Effects */}
                <Card>
                  <CardHeader>
                    <CardTitle>Seasonal Effects</CardTitle>
                    <CardDescription>Enrollment varies by calendar month</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="border border-border rounded-lg p-4">
                      <p className="text-sm mb-3">{simulationData.model_assumptions.seasonal_effects.description}</p>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        {Object.entries(simulationData.model_assumptions.seasonal_effects.multipliers).map(([month, mult]) => (
                          <div key={month} className="flex justify-between">
                            <span className="text-muted-foreground">{month}:</span>
                            <span className="font-semibold">{mult}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Stochastic Variation */}
                <Card>
                  <CardHeader>
                    <CardTitle>Stochastic Variation</CardTitle>
                    <CardDescription>Random variation in enrollment</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="border border-border rounded-lg p-4 space-y-2">
                      <p className="text-sm"><span className="font-semibold">Monthly Variation:</span> {simulationData.model_assumptions.stochastic_variation.monthly_variation}</p>
                      <p className="text-sm"><span className="font-semibold">Sampling Method:</span> Poisson distribution</p>
                      <p className="text-xs text-muted-foreground mt-2">{simulationData.model_assumptions.stochastic_variation.description}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Curve Drivers */}
                <Card>
                  <CardHeader>
                    <CardTitle>What Drives the Curve Shape?</CardTitle>
                    <CardDescription>Understanding the enrollment pattern</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-1">📈 Initial Ramp (Months 1-3)</p>
                        <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.curve_drivers.initial_ramp}</p>
                      </div>
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-1">🎯 Mid Period (Months 4-18)</p>
                        <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.curve_drivers.mid_period}</p>
                      </div>
                      <div className="border border-border rounded-lg p-4">
                        <p className="text-sm font-semibold mb-1">📉 Late Period (Final Months)</p>
                        <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.curve_drivers.late_period}</p>
                      </div>
                      <div className="border border-border rounded-lg p-4 bg-muted/20">
                        <p className="text-sm font-semibold mb-1">🔁 Smoothness</p>
                        <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.curve_drivers.smoothness}</p>
                      </div>
                      {simulationData.model_assumptions.curve_drivers.data_integration && (
                        <div className="border border-blue-500/50 rounded-lg p-4 bg-blue-50/50 dark:bg-blue-950/20">
                          <p className="text-sm font-semibold mb-1 text-blue-700 dark:text-blue-400">🔗 Data Integration</p>
                          <p className="text-xs text-muted-foreground">{simulationData.model_assumptions.curve_drivers.data_integration}</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Alert className="border-blue-500/50 bg-blue-50/50 dark:bg-blue-950/20">
                  <Info className="h-4 w-4 text-blue-600" />
                  <AlertDescription>
                    <span className="font-semibold text-blue-700 dark:text-blue-400">Now using real site data!</span> The simulation leverages historical trial counts, organization types, and therapeutic area expertise from your selected sites. Enrollment rates are informed by reference trials. The "curvey" shape reflects realistic patterns: slow start (site activation + learning), peak enrollment (full efficiency), and tapering (site depletion). Smooth curves result from averaging 5,000 iterations.
                  </AlertDescription>
                </Alert>
              </div>
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  <Info className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Model parameters not available. Run simulation to see detailed assumptions.</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Countries Tab - Advanced Mode Only */}
          {simulationData.simulation_type === 'advanced' && simulationData.country_performance_summary && (
            <TabsContent value="countries">
              <Card>
                <CardHeader>
                  <CardTitle>Country Performance</CardTitle>
                  <CardDescription>
                    Enrollment and regulatory status by country
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {simulationData.country_performance_summary.map((country) => (
                      <div key={country.country_code} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <h4 className="font-semibold text-lg">{country.country_name}</h4>
                            <p className="text-sm text-muted-foreground">Code: {country.country_code}</p>
                          </div>
                          <Badge variant={country.regulatory_status === 'Approved' ? 'default' : 'secondary'}>
                            {country.regulatory_status}
                          </Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-sm text-muted-foreground">Sites</p>
                            <p className="text-2xl font-bold">{country.sites}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Total Enrolled</p>
                            <p className="text-2xl font-bold">{country.total_enrolled}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {advancedOptions.totalBudget && simulationData.budget_exhaustion_probability !== undefined && (
                    <div className="mt-6 pt-6 border-t">
                      <h4 className="font-semibold mb-4">Budget Risk Analysis</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <Card className="border-orange-200 bg-orange-50/50 dark:bg-orange-950/20">
                          <CardContent className="pt-4">
                            <p className="text-sm text-muted-foreground mb-2">Budget Exhaustion Risk</p>
                            <div className="flex items-baseline gap-2">
                              <span className={`text-3xl font-bold ${
                                simulationData.budget_exhaustion_probability > 20 ? 'text-red-600' :
                                simulationData.budget_exhaustion_probability > 10 ? 'text-orange-600' :
                                'text-green-600'
                              }`}>
                                {simulationData.budget_exhaustion_probability.toFixed(1)}%
                              </span>
                            </div>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardContent className="pt-4">
                            <p className="text-sm text-muted-foreground mb-2">Total Budget</p>
                            <div className="text-2xl font-bold">
                              ${advancedOptions.totalBudget.toLocaleString()}
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Regulatory Events Tab - Advanced Mode Only */}
          {simulationData.simulation_type === 'advanced' && simulationData.regulatory_event_summary && (
            <TabsContent value="regulatory">
              <Card>
                <CardHeader>
                  <CardTitle>Regulatory Events</CardTitle>
                  <CardDescription>
                    Simulated regulatory events and their impact on the trial
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="border rounded-lg p-4 hover:bg-red-50/50 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className={`h-5 w-5 ${
                          (simulationData.regulatory_event_summary.clinical_holds || 0) > 0 ? 'text-red-600' : 'text-gray-400'
                        }`} />
                        <h4 className="font-semibold">Clinical Holds</h4>
                      </div>
                      <p className="text-4xl font-bold">
                        {simulationData.regulatory_event_summary.clinical_holds || 0}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Severe impact on enrollment
                      </p>
                    </div>

                    <div className="border rounded-lg p-4 hover:bg-yellow-50/50 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <Calendar className={`h-5 w-5 ${
                          (simulationData.regulatory_event_summary.protocol_amendments || 0) > 0 ? 'text-yellow-600' : 'text-gray-400'
                        }`} />
                        <h4 className="font-semibold">Protocol Amendments</h4>
                      </div>
                      <p className="text-4xl font-bold">
                        {simulationData.regulatory_event_summary.protocol_amendments || 0}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Moderate timeline impact
                      </p>
                    </div>

                    <div className="border rounded-lg p-4 hover:bg-blue-50/50 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <Info className={`h-5 w-5 ${
                          (simulationData.regulatory_event_summary.regulatory_audits || 0) > 0 ? 'text-blue-600' : 'text-gray-400'
                        }`} />
                        <h4 className="font-semibold">Regulatory Audits</h4>
                      </div>
                      <p className="text-4xl font-bold">
                        {simulationData.regulatory_event_summary.regulatory_audits || 0}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Resource drain events
                      </p>
                    </div>

                    <div className="border rounded-lg p-4 hover:bg-purple-50/50 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <Target className={`h-5 w-5 ${
                          (simulationData.regulatory_event_summary.site_audits || 0) > 0 ? 'text-purple-600' : 'text-gray-400'
                        }`} />
                        <h4 className="font-semibold">Site Audits</h4>
                      </div>
                      <p className="text-4xl font-bold">
                        {simulationData.regulatory_event_summary.site_audits || 0}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Site-level monitoring
                      </p>
                    </div>
                  </div>

                  <Alert className="mt-6">
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      These events are probabilistically simulated based on industry standards: Clinical Holds (1%/year), 
                      Protocol Amendments (15%/year), Regulatory Audits (5%/year), Site Audits (10%/year). 
                      Actual occurrence varies by therapeutic area and regulatory region.
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Operational Metrics Tab - Advanced Mode Only */}
          {simulationData.simulation_type === 'advanced' && simulationData.operational_metrics && (
            <TabsContent value="operational">
              <Card>
                <CardHeader>
                  <CardTitle>Operational Metrics</CardTitle>
                  <CardDescription>
                    Resource utilization and operational efficiency
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* CRA Utilization */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <h4 className="font-semibold">CRA (Clinical Research Associate) Utilization</h4>
                        <span className="text-lg font-bold">
                          {(simulationData.operational_metrics.cra_utilization * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                        <div 
                          className={`h-3 rounded-full transition-all ${
                            simulationData.operational_metrics.cra_utilization > 0.9 ? 'bg-red-600' :
                            simulationData.operational_metrics.cra_utilization > 0.7 ? 'bg-yellow-600' :
                            'bg-green-600'
                          }`}
                          style={{width: `${simulationData.operational_metrics.cra_utilization * 100}%`}}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {simulationData.operational_metrics.cra_utilization > 0.9 ? 'Over-capacity: Consider hiring additional CRAs' :
                         simulationData.operational_metrics.cra_utilization > 0.7 ? 'Near capacity: Monitor closely' :
                         'Good capacity: Resources available'}
                      </p>
                    </div>

                    {/* DM Utilization */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <h4 className="font-semibold">Data Manager Utilization</h4>
                        <span className="text-lg font-bold">
                          {(simulationData.operational_metrics.dm_utilization * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                        <div 
                          className={`h-3 rounded-full transition-all ${
                            simulationData.operational_metrics.dm_utilization > 0.9 ? 'bg-red-600' :
                            simulationData.operational_metrics.dm_utilization > 0.7 ? 'bg-yellow-600' :
                            'bg-green-600'
                          }`}
                          style={{width: `${simulationData.operational_metrics.dm_utilization * 100}%`}}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {simulationData.operational_metrics.dm_utilization > 0.9 ? 'Over-capacity: Query backlog risk' :
                         simulationData.operational_metrics.dm_utilization > 0.7 ? 'Near capacity: Monitor workload' :
                         'Good capacity: Queries handled efficiently'}
                      </p>
                    </div>

                    {/* Detailed Metrics Grid */}
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                      <div className="border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground mb-1">Avg Queries per Site</p>
                        <p className="text-3xl font-bold">
                          {simulationData.operational_metrics.average_queries_per_site?.toFixed(1) || 'N/A'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-2">
                          Data quality indicator
                        </p>
                      </div>
                      
                      <div className="border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground mb-1">Site Monitoring Coverage</p>
                        <p className="text-3xl font-bold">
                          {(simulationData.operational_metrics.site_monitoring_coverage * 100).toFixed(1)}%
                        </p>
                        <p className="text-xs text-muted-foreground mt-2">
                          Compliance metric
                        </p>
                      </div>
                    </div>

                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Operational Constraints Model:</strong> Assumes 2 CRAs managing up to 8 sites each, 
                        with average 2 queries per patient. High utilization (&gt;90%) may indicate need for additional resources. 
                        Monitoring coverage reflects visit completion rates across all sites.
                      </AlertDescription>
                    </Alert>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      ) : loading ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-primary" />
            <p className="text-lg font-semibold mb-2">Running Monte Carlo Simulation</p>
            <p className="text-sm text-muted-foreground">
              Analyzing 5,000 iterations to predict enrollment patterns...
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="mb-2">No simulation run yet</p>
            <p className="text-sm">Configure parameters and click "Run Monte Carlo Simulation" to get started</p>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              <p>Error: {error.message}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

