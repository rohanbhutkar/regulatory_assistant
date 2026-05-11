"use client"

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { getActivityWebSocketClient } from '../api/activity-websocket'

export type OperationType = 
  | 'ai_generation' 
  | 'data_search' 
  | 'simulation' 
  | 'evidence_discovery' 
  | 'budget_calc'
  | 'site_filtering'
  | 'population_analysis'
  | 'pricing_calc'
  | 'hta_assessment'

export type OperationStatus = 'pending' | 'in_progress' | 'completed' | 'error' | 'cancelled'

export interface OperationStep {
  name: string
  status: 'pending' | 'in_progress' | 'completed' | 'error'
  start_time?: string
  end_time?: string
  duration?: number
}

export interface Operation {
  id: string
  type: OperationType
  context: {
    assetId?: string
    studyId?: string
    tab?: string
  }
  status: OperationStatus
  progress: number
  currentStep: string
  steps: OperationStep[]
  startTime: Date
  endTime?: Date
  error?: string
  metadata?: Record<string, any>
  duration?: number
}

interface ActivityContextType {
  operations: Operation[]
  addOperation: (operation: Omit<Operation, 'id' | 'startTime' | 'status' | 'progress' | 'currentStep' | 'steps'>) => string
  updateOperation: (operationId: string, updates: Partial<Operation>) => void
  cancelOperation: (operationId: string) => void
  getOperationsByContext: (context: Partial<Operation['context']>) => Operation[]
  clearCompleted: () => void
}

const ActivityContext = createContext<ActivityContextType | undefined>(undefined)

const MAX_OPERATIONS = 100
const AUTO_DISMISS_DELAY = 5000 // 5 seconds

export function ActivityProvider({ children }: { children: React.ReactNode }) {
  const [operations, setOperations] = useState<Operation[]>([])
  const dismissTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const wsClientRef = useRef<ReturnType<typeof getActivityWebSocketClient> | null>(null)

  // Load persisted operations on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem('activity_operations')
      if (stored) {
        const parsed = JSON.parse(stored)
        const restored = parsed.map((op: any) => ({
          ...op,
          startTime: new Date(op.startTime),
          endTime: op.endTime ? new Date(op.endTime) : undefined
        }))
        setOperations(restored)
      }
    } catch (e) {
      console.error('Error loading persisted operations:', e)
    }
  }, [])

  // Persist operations to sessionStorage
  useEffect(() => {
    try {
      const toStore = operations.map(op => ({
        ...op,
        startTime: op.startTime.toISOString(),
        endTime: op.endTime?.toISOString()
      }))
      sessionStorage.setItem('activity_operations', JSON.stringify(toStore))
    } catch (e) {
      console.error('Error persisting operations:', e)
    }
  }, [operations])

  const addOperation = useCallback((
    operation: Omit<Operation, 'id' | 'startTime' | 'status' | 'progress' | 'currentStep' | 'steps'>
  ): string => {
    const id = `${operation.type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const newOperation: Operation = {
      ...operation,
      id,
      startTime: new Date(),
      status: 'pending',
      progress: 0,
      currentStep: '',
      steps: []
    }

    setOperations(prev => {
      const updated = [newOperation, ...prev]
      // Limit to MAX_OPERATIONS
      if (updated.length > MAX_OPERATIONS) {
        // Remove oldest completed operations first
        const completed = updated.filter(op => op.status === 'completed' || op.status === 'error')
        if (completed.length > 0) {
          completed.sort((a, b) => (a.endTime?.getTime() || 0) - (b.endTime?.getTime() || 0))
          const toRemove = completed[0]
          return updated.filter(op => op.id !== toRemove.id)
        }
        // If no completed operations, remove oldest
        return updated.slice(0, MAX_OPERATIONS)
      }
      return updated
    })

    return id
  }, [])

  const updateOperation = useCallback((operationId: string, updates: Partial<Operation>) => {
    setOperations(prev => {
      const updated = prev.map(op => {
        if (op.id === operationId) {
          const updatedOp = { ...op, ...updates }
          
          // If operation is completed, set endTime and calculate duration
          if (updates.status === 'completed' || updates.status === 'error') {
            updatedOp.endTime = new Date()
            updatedOp.duration = updatedOp.endTime.getTime() - op.startTime.getTime()
            
            // Auto-dismiss after delay
            const timeout = setTimeout(() => {
              setOperations(current => current.filter(o => o.id !== operationId))
            }, AUTO_DISMISS_DELAY)
            
            // Clear any existing timeout
            const existing = dismissTimeoutsRef.current.get(operationId)
            if (existing) {
              clearTimeout(existing)
            }
            dismissTimeoutsRef.current.set(operationId, timeout)
          }
          
          return updatedOp
        }
        return op
      })
      return updated
    })
  }, [])

  const cancelOperation = useCallback((operationId: string) => {
    setOperations(prev => {
      const updated = prev.map(op => {
        if (op.id === operationId) {
          return {
            ...op,
            status: 'cancelled' as OperationStatus,
            endTime: new Date(),
            duration: new Date().getTime() - op.startTime.getTime()
          }
        }
        return op
      })
      return updated
    })
  }, [])

  const getOperationsByContext = useCallback((context: Partial<Operation['context']>): Operation[] => {
    return operations.filter(op => {
      if (context.assetId && op.context.assetId !== context.assetId) return false
      if (context.studyId && op.context.studyId !== context.studyId) return false
      if (context.tab && op.context.tab !== context.tab) return false
      return true
    })
  }, [operations])

  const clearCompleted = useCallback(() => {
    setOperations(prev => prev.filter(op => 
      op.status !== 'completed' && op.status !== 'error' && op.status !== 'cancelled'
    ))
  }, [])

  // Connect to WebSocket for activity events
  useEffect(() => {
    const wsClient = getActivityWebSocketClient()
    wsClientRef.current = wsClient

    wsClient.connect((event) => {
      const operationId = event.operation_id
      const eventType = event.event_type

      if (eventType === 'operation_start') {
        // Check if operation already exists
        setOperations(prev => {
          const exists = prev.find(op => op.id === operationId)
          if (exists) return prev

          const newOp: Operation = {
            id: operationId,
            type: event.operation_type as OperationType,
            context: {
              assetId: event.context.asset_id,
              studyId: event.context.study_id,
              tab: event.context.tab
            },
            status: 'pending',
            progress: 0,
            currentStep: event.step,
            steps: [],
            startTime: new Date(event.timestamp),
            metadata: event.metadata
          }
          return [newOp, ...prev]
        })
      } else if (eventType === 'operation_progress' || eventType === 'step_start') {
        setOperations(prev => prev.map(op => {
          if (op.id === operationId) {
            const updated = { ...op }
            updated.status = 'in_progress'
            updated.progress = event.progress
            updated.currentStep = event.step

            // Update or add step
            if (eventType === 'step_start') {
              const stepExists = updated.steps.find(s => s.name === event.step)
              if (!stepExists) {
                updated.steps.push({
                  name: event.step,
                  status: 'in_progress',
                  start_time: event.timestamp
                })
              } else {
                updated.steps = updated.steps.map(s =>
                  s.name === event.step ? { ...s, status: 'in_progress', start_time: event.timestamp } : s
                )
              }
            }

            return updated
          }
          return op
        }))
      } else if (eventType === 'step_complete') {
        setOperations(prev => prev.map(op => {
          if (op.id === operationId) {
            const updated = { ...op }
            updated.steps = updated.steps.map(s => {
              if (s.name === event.step) {
                return {
                  ...s,
                  status: 'completed',
                  end_time: event.timestamp,
                  duration: s.start_time ? 
                    (new Date(event.timestamp).getTime() - new Date(s.start_time).getTime()) / 1000 : undefined
                }
              }
              return s
            })
            return updated
          }
          return op
        }))
      } else if (eventType === 'operation_complete') {
        setOperations(prev => prev.map(op => {
          if (op.id === operationId) {
            return {
              ...op,
              status: 'completed',
              progress: 100,
              endTime: new Date(event.timestamp),
              duration: op.startTime ? 
                (new Date(event.timestamp).getTime() - op.startTime.getTime()) / 1000 : undefined,
              metadata: { ...op.metadata, ...event.metadata }
            }
          }
          return op
        }))
      } else if (eventType === 'operation_error') {
        setOperations(prev => prev.map(op => {
          if (op.id === operationId) {
            return {
              ...op,
              status: 'error',
              error: event.message,
              endTime: new Date(event.timestamp),
              duration: op.startTime ? 
                (new Date(event.timestamp).getTime() - op.startTime.getTime()) / 1000 : undefined
            }
          }
          return op
        }))
      } else if (eventType === 'operation_cancelled') {
        setOperations(prev => prev.map(op => {
          if (op.id === operationId) {
            return {
              ...op,
              status: 'cancelled',
              endTime: new Date(event.timestamp),
              duration: op.startTime ? 
                (new Date(event.timestamp).getTime() - op.startTime.getTime()) / 1000 : undefined
            }
          }
          return op
        }))
      }
    })

    return () => {
      wsClient.disconnect()
    }
  }, [])

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      dismissTimeoutsRef.current.forEach(timeout => clearTimeout(timeout))
      if (wsClientRef.current) {
        wsClientRef.current.disconnect()
      }
    }
  }, [])

  return (
    <ActivityContext.Provider
      value={{
        operations,
        addOperation,
        updateOperation,
        cancelOperation,
        getOperationsByContext,
        clearCompleted
      }}
    >
      {children}
    </ActivityContext.Provider>
  )
}

export function useActivity() {
  const context = useContext(ActivityContext)
  if (context === undefined) {
    throw new Error('useActivity must be used within an ActivityProvider')
  }
  return context
}
