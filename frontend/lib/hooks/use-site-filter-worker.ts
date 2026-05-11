/**
 * React hook to manage site filtering web worker
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import type { SiteLocation, SiteFilterState, SiteFilterOptions, WorkerMessage, WorkerResponse } from '../types/site-filter-types'

interface WorkerState {
  allSites: SiteLocation[]
  filteredSites: SiteLocation[]
  filterOptions: SiteFilterOptions | null
  isLoading: boolean
  progress: number
  status: string
  error: string | null
}

export function useSiteFilterWorker() {
  const workerRef = useRef<Worker | null>(null)
  const [workerState, setWorkerState] = useState<WorkerState>({
    allSites: [],
    filteredSites: [],
    filterOptions: null,
    isLoading: false,
    progress: 0,
    status: '',
    error: null
  })

  // Initialize worker
  useEffect(() => {
    // Create worker
    try {
      workerRef.current = new Worker(
        new URL('../../workers/site-filter.worker.ts', import.meta.url),
        { type: 'module' }
      )

      // Handle messages from worker
      workerRef.current.onmessage = (e: MessageEvent<WorkerResponse>) => {
        const { type, sites, options, progress, status, error } = e.data

        switch (type) {
          case 'filtered':
            setWorkerState(prev => ({
              ...prev,
              filteredSites: sites || [],
              isLoading: false
            }))
            break

          case 'options':
            setWorkerState(prev => ({
              ...prev,
              filterOptions: options || null
            }))
            break

          case 'progress':
            setWorkerState(prev => ({
              ...prev,
              progress: progress || 0,
              status: status || '',
              isLoading: progress !== undefined && progress < 100
            }))
            break

          case 'error':
            console.error('Worker error:', error)
            setWorkerState(prev => ({
              ...prev,
              error: error || 'Unknown error',
              isLoading: false
            }))
            break
        }
      }

      // Handle worker errors
      workerRef.current.onerror = (error) => {
        console.error('Worker error:', error)
        setWorkerState(prev => ({
          ...prev,
          error: error.message || 'Worker error',
          isLoading: false
        }))
      }

      console.log('✅ Site filter worker initialized')
    } catch (error) {
      console.error('Failed to initialize worker:', error)
      setWorkerState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to initialize worker'
      }))
    }

    // Cleanup
    return () => {
      if (workerRef.current) {
        workerRef.current.terminate()
        console.log('🔴 Site filter worker terminated')
      }
    }
  }, [])

  // Update sites
  const updateSites = useCallback((sites: SiteLocation[], selectedTrials: string[] = []) => {
    if (!workerRef.current) return

    setWorkerState(prev => ({
      ...prev,
      allSites: sites,
      isLoading: true
    }))

    const message: WorkerMessage = {
      type: 'updateSites',
      sites,
      selectedTrials
    }

    workerRef.current.postMessage(message)
    console.log('📤 Updated sites in worker:', sites.length)
  }, [])

  // Apply filters
  const applyFilters = useCallback((filters: SiteFilterState) => {
    if (!workerRef.current) return

    setWorkerState(prev => ({
      ...prev,
      isLoading: true
    }))

    const message: WorkerMessage = {
      type: 'applyFilters',
      filters
    }

    workerRef.current.postMessage(message)
    console.log('🔍 Applying filters:', filters)
  }, [])

  // Calculate options
  const calculateOptions = useCallback(() => {
    if (!workerRef.current) return

    const message: WorkerMessage = {
      type: 'calculateOptions'
    }

    workerRef.current.postMessage(message)
    console.log('📊 Calculating filter options')
  }, [])

  // Reset filters
  const resetFilters = useCallback(() => {
    if (!workerRef.current) return

    const message: WorkerMessage = {
      type: 'reset'
    }

    workerRef.current.postMessage(message)
    console.log('🔄 Resetting filters')
  }, [])

  return {
    ...workerState,
    updateSites,
    applyFilters,
    calculateOptions,
    resetFilters
  }
}











