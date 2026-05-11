import { useState } from 'react'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'
import { toast } from 'sonner'

export interface AssetStrategyGenerationRequest {
  asset_id: string
  query?: string
  context?: {
    indication?: string
    therapeutic_area?: string
    market?: string
    moa?: string
    development_stage?: string
  }
  section_type?: string
  current_value?: string
}

export interface AssetStrategyGenerationResponse {
  success: boolean
  content?: string
  updates?: any
  comparators?: any[]
  pricing_parameters?: any
  message?: string
  expected_launch_dates?: Record<string, string>
  key_milestone_dates?: Record<string, string>
  rationale?: string
  historical_context?: string
  confidence?: string
  considerations?: string
}

export const useAssetStrategyGeneration = () => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateWithAI = async (
    endpoint: string,
    request: AssetStrategyGenerationRequest
  ): Promise<AssetStrategyGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          asset_id: request.asset_id,
          query: request.query,
          context: request.context,
          section_type: request.section_type,
          indication: request.context?.indication,
          therapeutic_area: request.context?.therapeutic_area,
          market: request.context?.market,
          current_value: request.current_value
        })
      })

      if (!response.ok) {
        const errorDetail = await response.text()
        throw new Error(`AI generation failed: ${response.status} - ${errorDetail}`)
      }

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.message || 'AI generation failed without specific error.')
      }
      toast.success('AI generated content successfully!')
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred during AI generation'
      setError(errorMessage)
      toast.error(errorMessage)
      console.error('AI Generation Error:', err)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  // Specific generation functions
  const generateAssetOverview = (request: AssetStrategyGenerationRequest) => 
    generateWithAI(assetStrategyAPI.generateAssetOverview(), request)
  
  const generateAssumptionSet = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.generateAssumptionSet(), request)

  const generateComparators = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.generateComparators(), request)

  const generateBenefitHypothesis = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.generateBenefitHypothesis(), request)

  const analyzeEvidenceGaps = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.analyzeEvidenceGaps(), request)

  const generatePricePotential = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.generatePricePotential(), request)

  const suggestPricingParameters = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.suggestPricingParameters(), request)

  const generateHTAAssessment = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.generateHTAAssessment(), request)

  const discoverEvidence = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.discoverEvidence(), request)

  const generateTimeline = (request: AssetStrategyGenerationRequest) =>
    generateWithAI(assetStrategyAPI.generateTimeline(), request)

  return {
    isGenerating,
    error,
    generateAssetOverview,
    generateAssumptionSet,
    generateComparators,
    generateBenefitHypothesis,
    analyzeEvidenceGaps,
    generatePricePotential,
    suggestPricingParameters,
    generateHTAAssessment,
    discoverEvidence,
    generateTimeline,
  }
}

export default useAssetStrategyGeneration

