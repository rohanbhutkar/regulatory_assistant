/**
 * Web Worker for site filtering
 * Handles heavy filtering operations off the main thread
 */

import type { SiteLocation, SiteFilterState, WorkerMessage, WorkerResponse } from '../lib/types/site-filter-types'

// Worker state
let allSites: SiteLocation[] = []
let selectedTrialIds: string[] = []

// Helper: Calculate filter options from sites
function calculateFilterOptions(sites: SiteLocation[]) {
  if (!sites || sites.length === 0) {
    return {
      historicalTrialsRange: [0, 0] as [number, number],
      avgEnrollmentRange: [0, 0] as [number, number],
      avgPsmRange: [0, 0] as [number, number],
      plannedPctRange: [0, 100] as [number, number],
      openPctRange: [0, 100] as [number, number],
      completedPctRange: [0, 100] as [number, number],
      unemploymentRateRange: [0, 100] as [number, number],
      vehicleOwnershipRange: [0, 100] as [number, number],
      states: [],
      countries: [],
      householdIncome: [],
      educationLevel: [],
      insuranceCoverage: []
    }
  }

  // Calculate ranges
  const historicalTrials = sites.map(s => s.historical_trials || 0)
  const avgEnrollments = sites.map(s => s.avg_enrollment || 0)
  const avgPsms = sites.map(s => s.avg_psm || 0).filter(v => v > 0)
  const plannedPcts = sites.map(s => s.planned_pct || 0).filter(v => v > 0)
  const openPcts = sites.map(s => s.open_pct || 0).filter(v => v > 0)
  const completedPcts = sites.map(s => s.completed_pct || 0).filter(v => v > 0)
  const unemploymentRates = sites.map(s => s.unemployment_rate || 0).filter(v => v > 0)
  const vehicleOwnerships = sites.map(s => s.vehicle_ownership || 0).filter(v => v > 0)

  // Get unique categorical values
  const states = Array.from(new Set(sites.map(s => s.state).filter(Boolean)))
  const countries = Array.from(new Set(sites.map(s => s.country).filter(Boolean)))
  const regions = Array.from(new Set(sites.map(s => s.region).filter(Boolean)))
  const householdIncomes = Array.from(new Set(sites.map(s => s.household_income).filter(Boolean)))
  const educationLevels = Array.from(new Set(sites.map(s => s.education_level).filter(Boolean)))
  const insuranceCoverages = Array.from(new Set(
    sites.flatMap(s => s.insurance_coverage || [])
  ))
  
  // NEW: Expanded filter options
  const siteTypes = Array.from(new Set(sites.map(s => s.organization_type).filter(Boolean)))
  
  // Therapeutic areas (flatten all disease_areas arrays)
  const allTherapeuticAreas = Array.from(new Set(
    sites.flatMap(s => s.disease_areas || [])
  ))
  
  // Sponsors (flatten all sponsors arrays)
  const allSponsors = Array.from(new Set(
    sites.flatMap(s => s.sponsors || [])
  ))
  
  // Debug logging
  console.log('🔧 Worker: Calculated filter options:', {
    siteTypes: siteTypes.length,
    therapeuticAreas: allTherapeuticAreas.length,
    sponsors: allSponsors.length,
    sampleSiteTypes: siteTypes.slice(0, 3),
    sampleTAs: allTherapeuticAreas.slice(0, 3),
    sampleSponsors: allSponsors.slice(0, 3)
  })
  
  // Trial experience ranges
  const totalTrials = sites.map(s => s.total_trials || 0)
  const ongoingTrials = sites.map(s => s.ongoing_trials || 0)

  return {
    historicalTrialsRange: [
      Math.min(...historicalTrials, 0),
      Math.max(...historicalTrials, 0)
    ] as [number, number],
    avgEnrollmentRange: [
      Math.min(...avgEnrollments, 0),
      Math.max(...avgEnrollments, 0)
    ] as [number, number],
    avgPsmRange: [
      avgPsms.length > 0 ? Math.min(...avgPsms) : 0,
      avgPsms.length > 0 ? Math.max(...avgPsms) : 100
    ] as [number, number],
    plannedPctRange: [
      plannedPcts.length > 0 ? Math.min(...plannedPcts) : 0,
      plannedPcts.length > 0 ? Math.max(...plannedPcts) : 100
    ] as [number, number],
    openPctRange: [
      openPcts.length > 0 ? Math.min(...openPcts) : 0,
      openPcts.length > 0 ? Math.max(...openPcts) : 100
    ] as [number, number],
    completedPctRange: [
      completedPcts.length > 0 ? Math.min(...completedPcts) : 0,
      completedPcts.length > 0 ? Math.max(...completedPcts) : 100
    ] as [number, number],
    unemploymentRateRange: [
      unemploymentRates.length > 0 ? Math.min(...unemploymentRates) : 0,
      unemploymentRates.length > 0 ? Math.max(...unemploymentRates) : 100
    ] as [number, number],
    vehicleOwnershipRange: [
      vehicleOwnerships.length > 0 ? Math.min(...vehicleOwnerships) : 0,
      vehicleOwnerships.length > 0 ? Math.max(...vehicleOwnerships) : 100
    ] as [number, number],
    totalTrialsRange: [
      Math.min(...totalTrials, 0),
      Math.max(...totalTrials, 0)
    ] as [number, number],
    ongoingTrialsRange: [
      Math.min(...ongoingTrials, 0),
      Math.max(...ongoingTrials, 0)
    ] as [number, number],
    states: states.sort(),
    countries: countries.sort(),
    regions: regions.sort(),
    householdIncome: householdIncomes.sort(),
    educationLevel: educationLevels.sort(),
    insuranceCoverage: insuranceCoverages.sort(),
    siteTypes: siteTypes.sort(),
    therapeuticAreas: allTherapeuticAreas.sort(),
    sponsors: allSponsors.sort()
  }
}

// Helper: Apply filters to sites
function applyFilters(sites: SiteLocation[], filters: SiteFilterState): SiteLocation[] {
  if (!filters) return sites

  return sites.filter(site => {
    // Historical trials filter
    if (filters.historicalTrials) {
      const trials = site.historical_trials || 0
      if (trials < filters.historicalTrials[0] || trials > filters.historicalTrials[1]) {
        return false
      }
    }

    // Avg enrollment filter
    if (filters.avgEnrollment) {
      const enrollment = site.avg_enrollment || 0
      if (enrollment < filters.avgEnrollment[0] || enrollment > filters.avgEnrollment[1]) {
        return false
      }
    }

    // Avg PSM filter
    if (filters.avgPsm && site.avg_psm !== undefined) {
      const psm = site.avg_psm
      if (psm < filters.avgPsm[0] || psm > filters.avgPsm[1]) {
        return false
      }
    }

    // States filter
    if (filters.states && filters.states.length > 0) {
      if (!filters.states.includes(site.state)) {
        return false
      }
    }

    // Countries filter
    if (filters.countries && filters.countries.length > 0) {
      if (!filters.countries.includes(site.country)) {
        return false
      }
    }

    // Planned % filter
    if (filters.plannedPct && site.planned_pct !== undefined) {
      const pct = site.planned_pct
      if (pct < filters.plannedPct[0] || pct > filters.plannedPct[1]) {
        return false
      }
    }

    // Open % filter
    if (filters.openPct && site.open_pct !== undefined) {
      const pct = site.open_pct
      if (pct < filters.openPct[0] || pct > filters.openPct[1]) {
        return false
      }
    }

    // Completed % filter
    if (filters.completedPct && site.completed_pct !== undefined) {
      const pct = site.completed_pct
      if (pct < filters.completedPct[0] || pct > filters.completedPct[1]) {
        return false
      }
    }

    // Household income filter
    if (filters.householdIncome && filters.householdIncome.length > 0 && site.household_income) {
      if (!filters.householdIncome.includes(site.household_income)) {
        return false
      }
    }

    // Education level filter
    if (filters.educationLevel && filters.educationLevel.length > 0 && site.education_level) {
      if (!filters.educationLevel.includes(site.education_level)) {
        return false
      }
    }

    // Insurance coverage filter
    if (filters.insuranceCoverage && filters.insuranceCoverage.length > 0 && site.insurance_coverage) {
      const hasMatch = site.insurance_coverage.some(cov => 
        filters.insuranceCoverage?.includes(cov)
      )
      if (!hasMatch) {
        return false
      }
    }

    // Unemployment rate filter
    if (filters.unemploymentRate && site.unemployment_rate !== undefined) {
      const rate = site.unemployment_rate
      if (rate < filters.unemploymentRate[0] || rate > filters.unemploymentRate[1]) {
        return false
      }
    }

    // Vehicle ownership filter
    if (filters.vehicleOwnership && site.vehicle_ownership !== undefined) {
      const ownership = site.vehicle_ownership
      if (ownership < filters.vehicleOwnership[0] || ownership > filters.vehicleOwnership[1]) {
        return false
      }
    }

    // NEW: Regions filter
    if (filters.regions && filters.regions.length > 0) {
      if (!site.region || !filters.regions.includes(site.region)) {
        return false
      }
    }

    // NEW: Site Types filter
    if (filters.siteTypes && filters.siteTypes.length > 0) {
      if (!site.organization_type || !filters.siteTypes.includes(site.organization_type)) {
        return false
      }
    }

    // NEW: Therapeutic Areas filter (site must have at least one matching TA)
    if (filters.therapeuticAreas && filters.therapeuticAreas.length > 0) {
      if (!site.disease_areas || site.disease_areas.length === 0) {
        return false
      }
      const hasMatch = site.disease_areas.some(ta => 
        filters.therapeuticAreas?.includes(ta)
      )
      if (!hasMatch) {
        return false
      }
    }

    // NEW: Sponsors filter (site must have worked with at least one matching sponsor)
    if (filters.sponsors && filters.sponsors.length > 0) {
      if (!site.sponsors || site.sponsors.length === 0) {
        return false
      }
      const hasMatch = site.sponsors.some(sponsor => 
        filters.sponsors?.includes(sponsor)
      )
      if (!hasMatch) {
        return false
      }
    }

    // NEW: Minimum Total Trials filter
    if (filters.minTotalTrials && filters.minTotalTrials > 0) {
      const trials = site.total_trials || 0
      if (trials < filters.minTotalTrials) {
        return false
      }
    }

    // NEW: Minimum Ongoing Trials filter
    if (filters.minOngoingTrials && filters.minOngoingTrials > 0) {
      const ongoing = site.ongoing_trials || 0
      if (ongoing < filters.minOngoingTrials) {
        return false
      }
    }

    return true
  })
}

// Message handler
self.onmessage = (e: MessageEvent<WorkerMessage>) => {
  const { type, sites, filters, selectedTrials } = e.data

  try {
    switch (type) {
      case 'updateSites':
        if (sites) {
          allSites = sites
          selectedTrialIds = selectedTrials || []
          
          // Send progress
          postMessage({
            type: 'progress',
            progress: 50,
            status: 'Sites updated'
          } as WorkerResponse)

          // Calculate and send options
          const options = calculateFilterOptions(sites)
          postMessage({
            type: 'options',
            options
          } as WorkerResponse)

          // Send filtered sites (initially all)
          postMessage({
            type: 'filtered',
            sites: allSites
          } as WorkerResponse)
        }
        break

      case 'applyFilters':
        if (filters) {
          // Send progress start
          postMessage({
            type: 'progress',
            progress: 0,
            status: 'Filtering sites...'
          } as WorkerResponse)

          // Apply filters
          const filteredSites = applyFilters(allSites, filters)

          // Send progress complete
          postMessage({
            type: 'progress',
            progress: 100,
            status: 'Filtering complete'
          } as WorkerResponse)

          // Send filtered results
          postMessage({
            type: 'filtered',
            sites: filteredSites
          } as WorkerResponse)
        }
        break

      case 'calculateOptions':
        const options = calculateFilterOptions(allSites)
        postMessage({
          type: 'options',
          options
        } as WorkerResponse)
        break

      case 'reset':
        postMessage({
          type: 'filtered',
          sites: allSites
        } as WorkerResponse)
        break

      default:
        postMessage({
          type: 'error',
          error: `Unknown message type: ${type}`
        } as WorkerResponse)
    }
  } catch (error) {
    postMessage({
      type: 'error',
      error: error instanceof Error ? error.message : 'Unknown error in worker'
    } as WorkerResponse)
  }
}

// Export empty object to make TypeScript happy
export {}

