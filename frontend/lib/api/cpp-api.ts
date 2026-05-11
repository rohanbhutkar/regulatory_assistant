/**
 * CPP API Client
 * Handles all CPP-related API calls
 */

import type {
  ProcedureMappingResponse,
  ProcedureMappingBatchResponse,
  OPALCalculationResponse,
  OPALInput,
  PricingResponse,
  MatrixCalculationResponse,
  CPPCalculationResponse,
  CPPInput,
  RulesPreviewResponse,
  VisitProcedure
} from '@/lib/types/cpp'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

class CPPApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  /**
   * Map a single procedure text to standardized code
   */
  async mapProcedure(
    text: string,
    returnAlternatives: boolean = true
  ): Promise<ProcedureMappingResponse> {
    const response = await fetch(`${this.baseUrl}/api/cpp/map-procedure`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        return_alternatives: returnAlternatives
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to map procedure: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Map multiple procedure texts at once
   */
  async mapProceduresBatch(
    texts: string[],
    returnAlternatives: boolean = true
  ): Promise<ProcedureMappingBatchResponse> {
    const response = await fetch(`${this.baseUrl}/api/cpp/map-procedures-batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        texts,
        return_alternatives: returnAlternatives
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to map procedures: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Calculate OPAL overhead hours
   */
  async calculateOPAL(input: OPALInput): Promise<OPALCalculationResponse> {
    const response = await fetch(`${this.baseUrl}/api/cpp/calculate-opal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input)
    })

    if (!response.ok) {
      throw new Error(`Failed to calculate OPAL: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get Fair Market Value pricing for procedures
   */
  async getPricing(
    procedureCodes: string[],
    countryCode: string = 'USA'
  ): Promise<PricingResponse> {
    const response = await fetch(`${this.baseUrl}/api/cpp/get-pricing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        procedure_codes: procedureCodes,
        country_code: countryCode
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to get pricing: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Calculate cost matrix (Procedures × Visits)
   */
  async calculateMatrix(
    visitProcedures: VisitProcedure[],
    countryCode: string = 'USA',
    cycles?: Record<string, number>,
    visitProbabilities?: Record<string, number>
  ): Promise<MatrixCalculationResponse> {
    const response = await fetch(`${this.baseUrl}/api/cpp/calculate-matrix`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        visit_procedures: visitProcedures,
        country_code: countryCode,
        cycles,
        visit_probabilities: visitProbabilities
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to calculate matrix: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Calculate complete Clinical Per-Patient cost
   */
  async calculateCPP(input: CPPInput): Promise<CPPCalculationResponse> {
    const response = await fetch(`${this.baseUrl}/api/cpp/calculate-cpp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input)
    })

    if (!response.ok) {
      throw new Error(`Failed to calculate CPP: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Preview rules that would apply to a study
   */
  async previewRules(
    countryCode?: string,
    indication?: string,
    phase?: string
  ): Promise<RulesPreviewResponse> {
    const params = new URLSearchParams()
    if (countryCode) params.append('country_code', countryCode)
    if (indication) params.append('indication', indication)
    if (phase) params.append('phase', phase)

    const response = await fetch(
      `${this.baseUrl}/api/cpp/rules/preview?${params.toString()}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to preview rules: ${response.statusText}`)
    }

    return response.json()
  }
}

// Export singleton instance
export const cppApi = new CPPApiClient()

// Export class for custom instances
export default CPPApiClient

