"use client"

import { useState, useEffect, useCallback, useMemo } from 'react'
import dynamic from 'next/dynamic'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { useStudyDesigner } from '@/lib/contexts/study-designer-context'
import { useSiteFilterWorker } from '@/lib/hooks/use-site-filter-worker'
import { SiteFilterDialog } from './site-filter-dialog'
import { DemographicFilterDialog } from './demographic-filter-dialog'
import { Loader2, MapPin, CheckCircle2, Download, List, Save, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { API_CONFIG } from '@/lib/config/api'
import type { SiteLocation, SiteFilterState } from '@/lib/types/site-filter-types'

// Dynamically import Leaflet-based map component to avoid SSR issues
const SiteSelectionMap = dynamic(
  () => import('./site-selection-map').then(mod => ({ default: mod.SiteSelectionMap })),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-[600px] bg-secondary/20 rounded-lg">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading map...</p>
        </div>
      </div>
    )
  }
)

export function EnhancedSiteSelectionTabV2() {
  const { 
    studyContext, 
    selectedTrials, 
    inclusionCriteria, 
    exclusionCriteria,
    selectedSites: contextSelectedSites,
    setSelectedSites: setContextSelectedSites
  } = useStudyDesigner()
  
  // State
  const [mapData, setMapData] = useState<{
    sites: SiteLocation[]
    total_sites: number
    total_population: number
    coverage_analysis: any
    population_heatmap?: any[]
  } | null>(null)
  const [selectedSiteIds, setSelectedSiteIds] = useState<Set<string>>(new Set())
  const [currentSites, setCurrentSites] = useState<SiteLocation[]>([]) // Track currently selected site objects
  const [loading, setLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [showSiteFilters, setShowSiteFilters] = useState(false)
  const [showDemographicFilters, setShowDemographicFilters] = useState(false)
  
  // Default filter state
  const [filters, setFilters] = useState<SiteFilterState>({
    historicalTrials: [0, 1000],
    avgEnrollment: [0, 100],
    avgPsm: [0, 100],
    states: [],
    countries: [],
    regions: [],
    plannedPct: [0, 100],
    openPct: [0, 100],
    completedPct: [0, 100],
    householdIncome: [],
    educationLevel: [],
    insuranceCoverage: [],
    unemploymentRate: [0, 100],
    vehicleOwnership: [0, 100],
    // NEW: Expanded filters
    siteTypes: [],
    therapeuticAreas: [],
    sponsors: [],
    minTotalTrials: 0,
    minOngoingTrials: 0
  })

  // Web worker for filtering
  const {
    filteredSites,
    filterOptions,
    isLoading: workerLoading,
    progress,
    status,
    updateSites,
    applyFilters,
    resetFilters
  } = useSiteFilterWorker()

  // Filter for ONLY selected trials (where selected === true)
  const actuallySelectedTrials = useMemo(() => {
    const filtered = selectedTrials.filter(trial => trial.selected === true)
    
    // Debug: Check what IDs we're actually getting
    const sampleTrial = filtered[0]
    if (sampleTrial) {
      console.log('🔍 Sample trial structure:', {
        id: sampleTrial.id,
        trialId: sampleTrial.trialId,
        nctId: sampleTrial.nctId,
        title: sampleTrial.title?.substring(0, 50)
      })
    }
    
    console.log('🎯 Actually selected trials:', {
      total: selectedTrials.length,
      actuallySelected: filtered.length,
      trialIds: filtered.map(t => t.trialId || t.id).slice(0, 5)
    })
    return filtered
  }, [selectedTrials])

  // Calculate average site count from reference trials
  const referenceSiteStats = useMemo(() => {
    if (actuallySelectedTrials.length === 0) {
      return null
    }

    const trialsWithSites = actuallySelectedTrials.filter(trial => {
      const siteCount = trial.reportedSites || trial.identifiedSites || 0
      return siteCount > 0
    })

    if (trialsWithSites.length === 0) {
      return null
    }

    const totalSites = trialsWithSites.reduce((sum, trial) => {
      return sum + (trial.reportedSites || trial.identifiedSites || 0)
    }, 0)
    
    const avgSites = Math.round(totalSites / trialsWithSites.length)
    
    return {
      avgSites,
      trialsAnalyzed: trialsWithSites.length,
      totalTrials: actuallySelectedTrials.length
    }
  }, [actuallySelectedTrials])

  // Load saved sites from context on mount (only once)
  const initialSiteIds = useMemo(() => {
    if (contextSelectedSites && contextSelectedSites.length > 0) {
      return new Set(contextSelectedSites.map(s => s.id))
    }
    return new Set<string>()
  }, []) // Empty deps - only calculate once on mount

  useEffect(() => {
    if (initialSiteIds.size > 0) {
      setSelectedSiteIds(initialSiteIds)
      console.log('✅ Loaded', initialSiteIds.size, 'saved sites from context')
    }
  }, [initialSiteIds])

  // No need to load site data separately - the map component will load and share it

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: SiteFilterState) => {
    setFilters(newFilters)
    applyFilters(newFilters)
  }, [applyFilters])

  // Handle filter reset
  const handleFilterReset = useCallback(() => {
    const defaultFilters: SiteFilterState = {
      historicalTrials: [0, 1000],
      avgEnrollment: [0, 100],
      avgPsm: [0, 100],
      states: [],
      countries: [],
      plannedPct: [0, 100],
      openPct: [0, 100],
      completedPct: [0, 100],
      householdIncome: [],
      educationLevel: [],
      insuranceCoverage: [],
      unemploymentRate: [0, 100],
      vehicleOwnership: [0, 100]
    }
    setFilters(defaultFilters)
    resetFilters()
  }, [resetFilters])

  // Handle state click (select/deselect all sites in state)
  const handleStateClick = useCallback((stateName: string) => {
    const sitesInState = filteredSites.filter(site => site.state === stateName)
    const siteIds = sitesInState.map(site => site.site_id)
    
    const allSelected = siteIds.every(id => selectedSiteIds.has(id))
    
    setSelectedSiteIds(prev => {
      const newSet = new Set(prev)
      if (allSelected) {
        // Deselect all
        siteIds.forEach(id => newSet.delete(id))
        toast.info(`Deselected ${siteIds.length} sites in ${stateName}`)
      } else {
        // Select all
        siteIds.forEach(id => newSet.add(id))
        toast.success(`Selected ${siteIds.length} sites in ${stateName}`)
      }
      return newSet
    })
  }, [filteredSites, selectedSiteIds])

  // Handle individual site selection
  const handleSiteToggle = useCallback((siteId: string) => {
    setSelectedSiteIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(siteId)) {
        newSet.delete(siteId)
      } else {
        newSet.add(siteId)
      }
      return newSet
    })
  }, [])

  // Handle map data loaded from the map component
  const handleMapDataLoaded = useCallback((data: any) => {
    setMapData(data)
    console.log('✅ Received site data from map:', {
      sites: data.sites?.length,
      population_points: data.population_heatmap?.length,
      coverage: data.coverage_analysis?.coverage_percentage
    })
    
    // Debug: Check sample site data structure
    if (data.sites && data.sites.length > 0) {
      const sampleSite = data.sites[0]
      console.log('🔍 Sample site data:', {
        organization_type: sampleSite.organization_type,
        disease_areas: sampleSite.disease_areas?.slice(0, 3),
        sponsors: sampleSite.sponsors?.slice(0, 3),
        total_trials: sampleSite.total_trials,
        ongoing_trials: sampleSite.ongoing_trials
      })
    }
    
    // Feed sites into web worker for filtering (use same data for list view)
    if (data.sites && data.sites.length > 0) {
      updateSites(
        data.sites,
        actuallySelectedTrials?.map(t => t.trialId || t.id) || []
      )
    }
  }, [updateSites, actuallySelectedTrials])

  // Handle sites selected from map
  const handleMapSitesSelected = useCallback((sites: SiteLocation[]) => {
    const siteIds = new Set(sites.map(s => s.site_id))
    
    // Only update if the selection actually changed (avoid circular updates)
    setSelectedSiteIds(prev => {
      if (prev.size !== siteIds.size) return siteIds
      // Check if the sets contain the same elements
      for (const id of siteIds) {
        if (!prev.has(id)) return siteIds
      }
      return prev // No change, return same reference
    })
    
    setCurrentSites(sites)
  }, [])

  // Save selected sites to context
  const handleSaveSites = useCallback(async () => {
    setIsSaving(true)
    try {
      // Get all selected sites from current data
      const allSites = [...(mapData?.sites || []), ...filteredSites]
      const uniqueSites = Array.from(
        new Map(allSites.map(site => [site.site_id, site])).values()
      )
      
      const selectedSiteObjects = uniqueSites.filter(site => 
        selectedSiteIds.has(site.site_id)
      )

      // Convert SiteLocation[] to SelectedSite[] format
      const sitesToSave = selectedSiteObjects.map(site => ({
        id: site.site_id,
        name: site.site_name,
        location: `${site.city}, ${site.state}, ${site.country}`,
        coordinates: { 
          lat: site.latitude, 
          lng: site.longitude 
        },
        score: 85, // Could calculate based on historical_trials
        historicalPerformance: site.historical_trials,
        estimatedEnrollment: Math.round(site.avg_enrollment)
      }))

      setContextSelectedSites(sitesToSave)
      
      toast.success(`Saved ${sitesToSave.length} site${sitesToSave.length !== 1 ? 's' : ''}`)
      console.log('✅ Saved sites to context:', sitesToSave)
    } catch (error) {
      console.error('Error saving sites:', error)
      toast.error('Failed to save sites')
    } finally {
      setIsSaving(false)
    }
  }, [mapData, filteredSites, selectedSiteIds, setContextSelectedSites])

  // Export selected sites to CSV
  const handleExportSites = useCallback(() => {
    const selectedSites = filteredSites.filter(site => selectedSiteIds.has(site.site_id))
    
    if (selectedSites.length === 0) {
      toast.error('No sites selected to export')
      return
    }

    const csvContent = [
      // Headers
      [
        'Site ID',
        'Site Name',
        'Organization',
        'City',
        'State',
        'Country',
        'Latitude',
        'Longitude',
        'Historical Trials',
        'Avg Enrollment',
        'Therapeutic Areas'
      ].join(','),
      // Data
      ...selectedSites.map(site => [
        site.site_id,
        `"${site.site_name}"`,
        `"${site.organization}"`,
        site.city,
        site.state,
        site.country,
        site.latitude,
        site.longitude,
        site.historical_trials,
        site.avg_enrollment,
        `"${site.therapeutic_areas.join('; ')}"`
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `sites_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    toast.success(`Exported ${selectedSites.length} sites to CSV`)
  }, [filteredSites, selectedSiteIds])

  // Select all visible sites
  const handleSelectAllVisible = useCallback(() => {
    const visibleSiteIds = new Set(filteredSites.map(site => site.site_id))
    setSelectedSiteIds(visibleSiteIds)
    toast.success(`Selected ${visibleSiteIds.size} visible site${visibleSiteIds.size !== 1 ? 's' : ''}`)
  }, [filteredSites])

  // Clear selection
  const handleClearSelection = useCallback(() => {
    setSelectedSiteIds(new Set())
    toast.info('Selection cleared')
  }, [])

  // Select all recommended sites (based on reference trial average)
  const handleSelectRecommended = useCallback(() => {
    if (filteredSites.length === 0) {
      toast.error('No sites available to select')
      return
    }

    // Sort sites by quality (historical trials, then enrollment)
    const sortedSites = [...filteredSites].sort((a, b) => {
      // Prioritize by historical trials, then avg enrollment
      if (b.historical_trials !== a.historical_trials) {
        return b.historical_trials - a.historical_trials
      }
      return b.avg_enrollment - a.avg_enrollment
    })

    // Calculate target number of sites from reference trials
    let targetSiteCount = 0
    let referenceSource = 'default (25% of available sites)'

    if (actuallySelectedTrials.length > 0) {
      // Extract site counts from reference trials
      const trialsWithSites = actuallySelectedTrials.filter(trial => {
        const siteCount = trial.reportedSites || trial.identifiedSites || 0
        return siteCount > 0
      })

      if (trialsWithSites.length > 0) {
        // Calculate average number of sites across reference trials
        const totalSites = trialsWithSites.reduce((sum, trial) => {
          return sum + (trial.reportedSites || trial.identifiedSites || 0)
        }, 0)
        
        const avgSitesPerTrial = Math.round(totalSites / trialsWithSites.length)
        targetSiteCount = Math.max(1, avgSitesPerTrial) // At least 1 site
        referenceSource = `reference trials (avg: ${avgSitesPerTrial} sites from ${trialsWithSites.length} trials)`
        
        console.log('📊 Reference trial site counts:', {
          trials_analyzed: trialsWithSites.length,
          total_sites: totalSites,
          average_sites: avgSitesPerTrial,
          site_counts: trialsWithSites.map(t => ({
            nctId: t.nctId,
            sites: t.reportedSites || t.identifiedSites
          }))
        })
      }
    }

    // Fallback: if no reference trial data, use 25% of available sites
    if (targetSiteCount === 0) {
      targetSiteCount = Math.max(1, Math.ceil(filteredSites.length * 0.25))
    }

    // Ensure we don't select more sites than available
    targetSiteCount = Math.min(targetSiteCount, filteredSites.length)

    // Select top N sites
    const sitesToSelect = sortedSites.slice(0, targetSiteCount)
    const siteIds = new Set(sitesToSelect.map(s => s.site_id))
    setSelectedSiteIds(siteIds)
    
    toast.success(`Selected ${siteIds.size} recommended sites`, {
      description: `Based on ${referenceSource}`
    })
    
    console.log('✨ Selected recommended sites:', {
      total_available: filteredSites.length,
      target_count: targetSiteCount,
      selected: siteIds.size,
      reference_source: referenceSource,
      top_sites: sitesToSelect.slice(0, 5).map(s => ({
        name: s.site_name,
        trials: s.historical_trials,
        enrollment: s.avg_enrollment
      }))
    })
  }, [filteredSites, actuallySelectedTrials])

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle>Site Selection</CardTitle>
              <CardDescription>
                Select sites from reference trials with advanced filtering
              </CardDescription>
            </div>
            {referenceSiteStats && (
              <div className="flex flex-col items-end gap-1">
                <Badge variant="secondary" className="text-sm font-semibold px-3 py-1">
                  Avg: {referenceSiteStats.avgSites} sites
                </Badge>
                <span className="text-xs text-muted-foreground">
                  from {referenceSiteStats.trialsAnalyzed} reference trial{referenceSiteStats.trialsAnalyzed !== 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="default"
              size="sm"
              onClick={handleSelectRecommended}
              disabled={loading || workerLoading || filteredSites.length === 0}
              className="gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
            >
              <Sparkles className="h-4 w-4" />
              Select Recommended
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleSelectAllVisible}
              disabled={loading || workerLoading || filteredSites.length === 0}
              className="gap-2"
            >
              <CheckCircle2 className="h-4 w-4" />
              Select All Visible ({filteredSites.length})
            </Button>

            <div className="h-8 w-px bg-border" />

            <SiteFilterDialog
              open={showSiteFilters}
              onOpenChange={setShowSiteFilters}
              filters={filters}
              options={filterOptions}
              onFilterChange={handleFilterChange}
              onReset={handleFilterReset}
            />
            
            <DemographicFilterDialog
              open={showDemographicFilters}
              onOpenChange={setShowDemographicFilters}
              filters={filters}
              options={filterOptions}
              onFilterChange={handleFilterChange}
              onReset={handleFilterReset}
            />

            {selectedSiteIds.size > 0 && (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSaveSites}
                  disabled={isSaving}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? 'Saving...' : `Save Sites (${selectedSiteIds.size})`}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportSites}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  Export ({selectedSiteIds.size})
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearSelection}
                  className="gap-2"
                >
                  Clear Selection
                </Button>
              </>
            )}
          </div>

          {/* Loading Progress */}
          {(loading || workerLoading) && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{status || 'Loading...'}</span>
                <span className="font-medium">{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs defaultValue="markers" className="space-y-4">
        <TabsList>
          <TabsTrigger value="markers">
            <MapPin className="h-4 w-4 mr-2" />
            Map View
          </TabsTrigger>
          <TabsTrigger value="list">
            <List className="h-4 w-4 mr-2" />
            List View
          </TabsTrigger>
        </TabsList>

        {/* Marker Map */}
        <TabsContent value="markers" className="space-y-4">
          <SiteSelectionMap
            reference_trial_ids={actuallySelectedTrials?.map(t => t.trialId || t.id) || []}
            indication={studyContext.indication}
            phase={studyContext.phase}
            therapeutic_area={studyContext.therapeuticArea}
            icd_codes={inclusionCriteria?.flatMap(c => c.icdCodes || []) || []}
            inclusion_criteria={inclusionCriteria?.map(c => c.text || c.criterion) || []}
            exclusion_criteria={exclusionCriteria?.map(c => c.text || c.criterion) || []}
            initialSelectedSiteIds={initialSiteIds}
            filteredSites={filteredSites}
            onSitesSelected={handleMapSitesSelected}
            onMapDataLoaded={handleMapDataLoaded}
          />
        </TabsContent>

        {/* List View */}
        <TabsContent value="list" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredSites.map((site) => (
              <Card
                key={site.site_id}
                className={`cursor-pointer transition-all ${
                  selectedSiteIds.has(site.site_id)
                    ? 'ring-2 ring-green-500 bg-green-50 dark:bg-green-950'
                    : 'hover:bg-secondary/50'
                }`}
                onClick={() => handleSiteToggle(site.site_id)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-base">{site.site_name}</CardTitle>
                      <CardDescription>{site.city}, {site.state}</CardDescription>
                    </div>
                    {selectedSiteIds.has(site.site_id) && (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Historical Trials:</span>
                      <span className="ml-1 font-medium">{site.historical_trials}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Avg Enrollment:</span>
                      <span className="ml-1 font-medium">{site.avg_enrollment.toFixed(0)}</span>
                    </div>
                  </div>
                  {site.therapeutic_areas.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {site.therapeutic_areas.slice(0, 3).map((ta, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {ta}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Loading State */}
      {loading && (
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading site data...</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

