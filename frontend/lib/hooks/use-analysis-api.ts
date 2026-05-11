import { useState } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface SimulationRequest {
  studyDesign: {
    indication?: string
    phase?: string
    totalParticipants?: number
  }
  sites: unknown[]
  simulationType: string
  parameters: unknown
}

export interface SimulationResponse {
  success: boolean
  data?: {
    quarterly_revenue?: Array<{
      quarter: number
      year: number
      quarter_in_year: number
      revenue: number
    }>
    total_revenue?: number
    peak_revenue?: number
    [key: string]: unknown
  }
  error?: string
}

export interface BudgetAnalysisRequest {
  studyDesign: {
    indication?: string
    phase?: string
    totalParticipants?: number
  }
  sites: unknown[]
}

export interface BudgetAnalysisResponse {
  success: boolean
  data?: {
    cost_breakdown?: Array<{
      category: string
      cost: number
      percentage: number
    }>
    total_cost?: number
    cost_per_patient?: number
    [key: string]: unknown
  }
  error?: string
}

export interface SiteAnalysisRequest {
  studyDesign: {
    indication?: string
    phase?: string
    totalParticipants?: number
  }
  criteria: {
    indication: string
    phase: string
    targetEnrollment: number
  }
}

export interface SiteAnalysisResponse {
  success: boolean
  data?: {
    recommendedSites?: Array<{
      id?: string
      name?: string
      site_name?: string
      location?: string
      city?: string
      state?: string
      coordinates?: { lat: number; lng: number }
      score?: number
      historical_performance?: number
      estimated_enrollment?: number
    }>
    [key: string]: unknown
  }
  error?: string
}

export interface OptimizationRequest {
  optimization_type: string
  study_design: unknown
  constraints: unknown
  objectives: string[]
}

export interface OptimizationResponse {
  success: boolean
  optimized_parameters: unknown
  improvement_metrics: unknown
  recommendations: string[]
}

export const useAnalysisAPI = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSimulation = async (request: SimulationRequest): Promise<SimulationResponse | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/simulation/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error running simulation:', errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  const analyzeBudget = async (request: BudgetAnalysisRequest): Promise<BudgetAnalysisResponse | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/budget/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error analyzing budget:', errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  const analyzeSites = async (request: SiteAnalysisRequest): Promise<SiteAnalysisResponse | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/sites/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error analyzing sites:', errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  const runOptimization = async (request: OptimizationRequest): Promise<OptimizationResponse | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/optimization/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error running optimization:', errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  const getSimulationTemplates = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/simulation/templates`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching simulation templates:', errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  const getBudgetTemplates = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/budget/templates`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching budget templates:', errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    isLoading,
    error,
    runSimulation,
    analyzeBudget,
    analyzeSites,
    runOptimization,
    getSimulationTemplates,
    getBudgetTemplates
  }
}

export default useAnalysisAPI










