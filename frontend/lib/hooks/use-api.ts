/**
 * React hooks for API calls with automatic request cancellation
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import { apiClient, APIError, RequestConfig } from '@/lib/api/enhanced-client'

export interface UseAPIOptions<T> {
  onSuccess?: (data: T) => void
  onError?: (error: APIError) => void
  immediate?: boolean
  requestKey?: string
}

export interface UseAPIState<T> {
  data: T | null
  loading: boolean
  error: APIError | null
}

/**
 * Hook for making API calls with automatic cancellation on unmount
 */
export function useAPI<T = any>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  endpoint: string,
  options: UseAPIOptions<T> = {}
) {
  const [state, setState] = useState<UseAPIState<T>>({
    data: null,
    loading: options.immediate ?? false,
    error: null,
  })

  const baseRequestKey = useRef(options.requestKey || `${method}-${endpoint}`)
  const activeRequestKeyRef = useRef<string | null>(null)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      // Cancel active request on unmount
      if (activeRequestKeyRef.current) {
        apiClient.cancelRequest(activeRequestKeyRef.current)
      }
    }
  }, [])

  const execute = useCallback(
    async (data?: any, config?: RequestConfig) => {
      if (!isMountedRef.current) return

      // Cancel previous request if one is active
      if (activeRequestKeyRef.current) {
        apiClient.cancelRequest(activeRequestKeyRef.current)
      }

      // Generate unique request key for this execution
      const requestKey = `${baseRequestKey.current}-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
      activeRequestKeyRef.current = requestKey

      setState(prev => ({ ...prev, loading: true, error: null }))

      try {
        let result: T
        
        switch (method) {
          case 'get':
            result = await apiClient.get<T>(endpoint, config, requestKey)
            break
          case 'post':
            result = await apiClient.post<T>(endpoint, data, config, requestKey)
            break
          case 'put':
            result = await apiClient.put<T>(endpoint, data, config, requestKey)
            break
          case 'patch':
            result = await apiClient.patch<T>(endpoint, data, config, requestKey)
            break
          case 'delete':
            result = await apiClient.delete<T>(endpoint, config, requestKey)
            break
          default:
            throw new Error(`Unsupported method: ${method}`)
        }

        // Clear active request key on success
        if (activeRequestKeyRef.current === requestKey) {
          activeRequestKeyRef.current = null
        }

        if (isMountedRef.current) {
          setState({ data: result, loading: false, error: null })
          options.onSuccess?.(result)
        }

        return result
      } catch (error) {
        // Clear active request key on error
        if (activeRequestKeyRef.current === requestKey) {
          activeRequestKeyRef.current = null
        }

        const apiError = error instanceof APIError ? error : new APIError('Unknown error')
        
        if (isMountedRef.current) {
          setState({ data: null, loading: false, error: apiError })
          options.onError?.(apiError)
        }

        throw apiError
      }
    },
    [method, endpoint, options]
  )

  // Auto-execute on mount if immediate is true
  useEffect(() => {
    if (options.immediate) {
      execute()
    }
  }, [options.immediate])

  const cancel = useCallback(() => {
    if (activeRequestKeyRef.current) {
      apiClient.cancelRequest(activeRequestKeyRef.current)
      activeRequestKeyRef.current = null
    }
  }, [])

  return {
    ...state,
    execute,
    cancel,
    refetch: execute,
  }
}

/**
 * Convenience hook for GET requests
 */
export function useAPIGet<T = any>(
  endpoint: string,
  options: Omit<UseAPIOptions<T>, 'immediate'> & { immediate?: boolean } = {}
) {
  return useAPI<T>('get', endpoint, { immediate: true, ...options })
}

/**
 * Convenience hook for POST requests
 */
export function useAPIPost<T = any>(
  endpoint: string,
  options: UseAPIOptions<T> = {}
) {
  return useAPI<T>('post', endpoint, options)
}

/**
 * Convenience hook for PUT requests
 */
export function useAPIPut<T = any>(
  endpoint: string,
  options: UseAPIOptions<T> = {}
) {
  return useAPI<T>('put', endpoint, options)
}

/**
 * Convenience hook for PATCH requests
 */
export function useAPIPatch<T = any>(
  endpoint: string,
  options: UseAPIOptions<T> = {}
) {
  return useAPI<T>('patch', endpoint, options)
}

/**
 * Convenience hook for DELETE requests
 */
export function useAPIDelete<T = any>(
  endpoint: string,
  options: UseAPIOptions<T> = {}
) {
  return useAPI<T>('delete', endpoint, options)
}
