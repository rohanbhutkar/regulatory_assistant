/**
 * Type definitions for site filtering system
 */

export interface SiteLocation {
  site_id: string
  site_name: string
  organization: string
  city: string
  state: string
  country: string
  latitude: number
  longitude: number
  historical_trials: number
  avg_enrollment: number
  therapeutic_areas: string[]
  recent_trials: any[]
  selected: boolean
  // Organization details
  organization_type?: string  // e.g., "Academic Hospital / Clinic"
  organization_address?: string  // Full address
  postal_code?: string  // ZIP/Postal code
  phones?: string  // Phone number(s)
  faxes?: string  // Fax number(s)
  region?: string  // Geographic region
  npi_number?: string  // National Provider Identifier
  // Trial metrics
  total_trials: number  // Total trial count
  ongoing_trials: number  // Number of ongoing trials
  planned_trials?: number
  total_matching_trials?: number
  ongoing_matching_trials?: number
  planned_matching_trials?: number
  total_investigators?: number
  last_trial_start_date?: string
  // Specialization
  disease_areas?: string[]  // Therapeutic areas from SiteTrove
  sponsors?: string[]  // Companies/sponsors the site has worked with
  // Parent organization
  parent_organization_name?: string
  parent_organization_type?: string
  parent_total_trials?: number
  // URLs
  record_url?: string
  supporting_urls?: string
  // Additional fields from SiteTrove
  avg_psm?: number
  planned_pct?: number
  open_pct?: number
  closed_pct?: number
  terminated_pct?: number
  completed_pct?: number
  // Demographics
  household_income?: string
  education_level?: string
  insurance_coverage?: string[]
  unemployment_rate?: number
  vehicle_ownership?: number
}

export interface SiteFilterState {
  // Site metrics
  historicalTrials: [number, number]
  avgEnrollment: [number, number]
  avgPsm: [number, number]
  
  // Location
  states: string[]
  countries: string[]
  regions: string[]
  
  // Trial status
  plannedPct: [number, number]
  openPct: [number, number]
  completedPct: [number, number]
  
  // Demographics (SDOH)
  householdIncome: string[]
  educationLevel: string[]
  insuranceCoverage: string[]
  unemploymentRate: [number, number]
  vehicleOwnership: [number, number]
  
  // NEW: Expanded filters
  siteTypes: string[]  // e.g., ["Academic Hospital / Clinic", "Clinical Trial Center"]
  therapeuticAreas: string[]  // Disease areas
  sponsors: string[]  // Companies/sponsors
  minTotalTrials: number  // Minimum trial experience
  minOngoingTrials: number  // Minimum ongoing trials
}

export interface SiteFilterOptions {
  // Ranges
  historicalTrialsRange: [number, number]
  avgEnrollmentRange: [number, number]
  avgPsmRange: [number, number]
  plannedPctRange: [number, number]
  openPctRange: [number, number]
  completedPctRange: [number, number]
  unemploymentRateRange: [number, number]
  vehicleOwnershipRange: [number, number]
  totalTrialsRange: [number, number]
  ongoingTrialsRange: [number, number]
  
  // Categorical options
  states: string[]
  countries: string[]
  regions: string[]
  householdIncome: string[]
  educationLevel: string[]
  insuranceCoverage: string[]
  siteTypes: string[]  // Available site types
  therapeuticAreas: string[]  // All therapeutic areas found
  sponsors: string[]  // All sponsors found
}

export interface WorkerMessage {
  type: 'updateSites' | 'applyFilters' | 'calculateOptions' | 'reset'
  sites?: SiteLocation[]
  filters?: SiteFilterState
  selectedTrials?: string[]
}

export interface WorkerResponse {
  type: 'filtered' | 'options' | 'progress' | 'error'
  sites?: SiteLocation[]
  options?: SiteFilterOptions
  progress?: number
  status?: string
  error?: string
}

