/**
 * Enhanced API Client with Error Handling, Retry Logic, and Request Cancellation
 * This client provides a centralized way to make API calls with consistent error handling
 */

export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

export interface RequestConfig extends RequestInit {
  timeout?: number
  retries?: number
  retryDelay?: number
  onRetry?: (attempt: number, error: Error) => void
}

export interface APIClientConfig {
  baseURL: string
  timeout?: number
  retries?: number
  retryDelay?: number
  onError?: (error: APIError) => void
}

class EnhancedAPIClient {
  private baseURL: string
  private timeout: number
  private retries: number
  private retryDelay: number
  private onError?: (error: APIError) => void
  private activeRequests: Map<string, AbortController>

  constructor(config: APIClientConfig) {
    this.baseURL = config.baseURL
    this.timeout = config.timeout || 30000
    this.retries = config.retries || 3
    this.retryDelay = config.retryDelay || 1000
    this.onError = config.onError
    this.activeRequests = new Map()
  }

  /**
   * Cancel a specific request by key
   */
  cancelRequest(key: string): void {
    const controller = this.activeRequests.get(key)
    if (controller) {
      controller.abort()
      this.activeRequests.delete(key)
    }
  }

  /**
   * Cancel all active requests
   */
  cancelAllRequests(): void {
    this.activeRequests.forEach((controller) => controller.abort())
    this.activeRequests.clear()
  }

  /**
   * Make a request with retry logic and error handling
   */
  private async request<T>(
    endpoint: string,
    config: RequestConfig = {},
    requestKey?: string
  ): Promise<T> {
    const {
      timeout = this.timeout,
      retries = this.retries,
      retryDelay = this.retryDelay,
      onRetry,
      ...fetchConfig
    } = config

    const url = `${this.baseURL}${endpoint}`
    const controller = new AbortController()
    
    // Store controller for cancellation
    const key = requestKey || `${endpoint}-${Date.now()}`
    this.activeRequests.set(key, controller)

    // Track if timeout triggered the abort
    let timeoutTriggered = false
    // Set up timeout
    const timeoutId = setTimeout(() => {
      timeoutTriggered = true
      controller.abort()
    }, timeout)

    let lastError: Error | null = null
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          ...fetchConfig,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...fetchConfig.headers,
          },
        })

        clearTimeout(timeoutId)
        this.activeRequests.delete(key)

        if (!response.ok) {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`
          let errorDetails = null

          try {
            const errorData = await response.json()
            errorMessage = errorData.detail || errorData.message || errorMessage
            errorDetails = errorData
          } catch {
            // Response body is not JSON
          }

          const apiError = new APIError(
            errorMessage,
            response.status,
            errorDetails?.code,
            errorDetails
          )

          // Don't retry on client errors (4xx)
          if (response.status >= 400 && response.status < 500) {
            throw apiError
          }

          throw apiError
        }

        // Handle empty responses
        const contentType = response.headers.get('content-type')
        if (!contentType || !contentType.includes('application/json')) {
          return null as T
        }

        return await response.json()
      } catch (error) {
        lastError = error as Error

        // Don't retry if request was cancelled
        if (error instanceof Error && error.name === 'AbortError') {
          clearTimeout(timeoutId)
          this.activeRequests.delete(key)
          // Distinguish between timeout and manual cancellation
          if (timeoutTriggered) {
            throw new APIError(`Request timed out after ${timeout}ms`, 0, 'REQUEST_TIMEOUT')
          }
          throw new APIError('Request cancelled', 0, 'REQUEST_CANCELLED')
        }

        // Retry logic
        if (attempt < retries) {
          console.warn(`Request failed, retrying (${attempt + 1}/${retries})...`, error)
          onRetry?.(attempt + 1, lastError)
          await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)))
          continue
        }

        // All retries failed
        clearTimeout(timeoutId)
        this.activeRequests.delete(key)
        
        const apiError = error instanceof APIError 
          ? error 
          : new APIError(
              error instanceof Error ? error.message : 'Unknown error',
              0,
              'NETWORK_ERROR'
            )

        this.onError?.(apiError)
        throw apiError
      }
    }

    // This should never be reached, but TypeScript needs it
    throw lastError || new APIError('Request failed', 0, 'UNKNOWN_ERROR')
  }

  // HTTP Methods
  async get<T>(endpoint: string, config?: RequestConfig, requestKey?: string): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'GET' }, requestKey)
  }

  async post<T>(endpoint: string, data?: any, config?: RequestConfig, requestKey?: string): Promise<T> {
    return this.request<T>(
      endpoint,
      {
        ...config,
        method: 'POST',
        body: data ? JSON.stringify(data) : undefined,
      },
      requestKey
    )
  }

  async put<T>(endpoint: string, data?: any, config?: RequestConfig, requestKey?: string): Promise<T> {
    return this.request<T>(
      endpoint,
      {
        ...config,
        method: 'PUT',
        body: data ? JSON.stringify(data) : undefined,
      },
      requestKey
    )
  }

  async patch<T>(endpoint: string, data?: any, config?: RequestConfig, requestKey?: string): Promise<T> {
    return this.request<T>(
      endpoint,
      {
        ...config,
        method: 'PATCH',
        body: data ? JSON.stringify(data) : undefined,
      },
      requestKey
    )
  }

  async delete<T>(endpoint: string, config?: RequestConfig, requestKey?: string): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' }, requestKey)
  }
}

// Create and export singleton instance
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export const apiClient = new EnhancedAPIClient({
  baseURL: API_BASE_URL,
  timeout: 30000,
  retries: 2,
  retryDelay: 1000,
  onError: (error) => {
    console.error('API Error:', error)
    // Additional global error handling can be added here
    // e.g., toast notifications, error tracking
  },
})

export default apiClient












