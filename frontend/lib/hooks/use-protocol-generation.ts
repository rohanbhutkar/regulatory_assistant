import { useState } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export interface ProtocolGenerationRequest {
  section_type?: string
  trials?: unknown[]
  reference_info?: string
  study_context?: unknown
  criteria_type?: 'inclusion' | 'exclusion'
}

export interface ProtocolGenerationResponse {
  success: boolean
  content?: string
  section_type?: string
  objectives?: string
  endpoints?: string
  criteria?: string
  soa?: string
  schema?: unknown
  trials_used?: number
  context?: unknown
  criteria_type?: string
  message?: string
}

export const useProtocolGeneration = () => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateProtocolSection = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-section`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          section_type: request.section_type,
          trials: request.trials || [],
          reference_info: request.reference_info || ''
        })
      })

      if (!response.ok) {
        // Try to get detailed error message from response
        let errorDetail = `HTTP error! status: ${response.status}`
        try {
          const errorData = await response.json()
          if (errorData.detail) {
            errorDetail = errorData.detail
          }
        } catch {
          // Couldn't parse error response, use status
        }
        throw new Error(errorDetail)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error generating protocol section:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateFullProtocol = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-full`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trials: request.trials || [],
          reference_info: request.reference_info || ''
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error generating full protocol:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateStudySchema = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      console.log("🌐 API Call - generateStudySchema:", {
        endpoint: `${API_BASE_URL}/api/protocol/generate-schema`,
        trialsCount: request.trials?.length || 0,
        hasReferenceInfo: !!request.reference_info
      })
      
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-schema`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trials: request.trials || [],
          reference_info: request.reference_info || ''
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("❌ API Error Response:", errorText)
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("✅ API Response received:", { success: data.success, contentLength: data.content?.length || 0 })
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('❌ Error generating study schema:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateObjectives = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      console.log("🌐 API Call - generateObjectives:", {
        endpoint: `${API_BASE_URL}/api/protocol/generate-objectives`,
        trialsCount: request.trials?.length || 0,
        hasReferenceInfo: !!request.reference_info
      })
      
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-objectives`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          study_context: request.study_context || {},
          trials: request.trials || [],
          reference_info: request.reference_info || ''
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("❌ API Error Response:", errorText)
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("✅ API Response received:", { success: data.success, contentLength: data.content?.length || 0 })
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('❌ Error generating objectives:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateEndpoints = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      console.log("🌐 API Call - generateEndpoints:", {
        endpoint: `${API_BASE_URL}/api/protocol/generate-endpoints`,
        trialsCount: request.trials?.length || 0,
        hasReferenceInfo: !!request.reference_info
      })
      
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-endpoints`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          study_context: request.study_context || {},
          trials: request.trials || [],
          reference_info: request.reference_info || ''
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("❌ API Error Response:", errorText)
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("✅ API Response received:", { success: data.success, contentLength: data.content?.length || 0 })
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('❌ Error generating endpoints:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateCriteria = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-criteria`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          study_context: request.study_context || {},
          criteria_type: request.criteria_type || 'inclusion',
          trials: request.trials || []
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error generating criteria:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateSoA = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      console.log("🌐 API Call - generateSoA:", {
        endpoint: `${API_BASE_URL}/api/protocol/generate-soa`,
        trialsCount: request.trials?.length || 0,
        hasReferenceInfo: !!request.reference_info
      })
      
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-soa`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trials: request.trials || [],
          reference_info: request.reference_info || ''
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("❌ API Error Response:", errorText)
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("✅ API Response received:", { success: data.success, contentLength: data.content?.length || 0 })
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('❌ Error generating SOA:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  const generateStudyDesign = async (request: ProtocolGenerationRequest): Promise<ProtocolGenerationResponse | null> => {
    setIsGenerating(true)
    setError(null)

    try {
      console.log("🌐 API Call - generateStudyDesign:", {
        endpoint: `${API_BASE_URL}/api/protocol/generate-study-design`,
        trialsCount: request.trials?.length || 0,
        hasReferenceInfo: !!request.reference_info,
        studyContext: request.study_context
      })
      
      const response = await fetch(`${API_BASE_URL}/api/protocol/generate-study-design`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trials: request.trials || [],
          reference_info: request.reference_info || '',
          study_context: request.study_context || {}
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("❌ API Error Response:", errorText)
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("✅ API Response received:", { success: data.success, contentLength: data.content?.length || 0 })
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('❌ Error generating study design:', errorMessage)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  return {
    isGenerating,
    error,
    generateProtocolSection,
    generateFullProtocol,
    generateStudySchema,
    generateObjectives,
    generateEndpoints,
    generateCriteria,
    generateSoA,
    generateStudyDesign
  }
}

export default useProtocolGeneration
































