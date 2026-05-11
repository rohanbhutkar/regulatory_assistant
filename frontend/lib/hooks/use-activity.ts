"use client"

import { useActivity, Operation, OperationType, OperationStatus } from '../contexts/activity-context'
import { useCallback } from 'react'

export function useActivityHook() {
  const {
    operations,
    addOperation,
    updateOperation,
    cancelOperation,
    getOperationsByContext,
    clearCompleted
  } = useActivity()

  const trackOperation = useCallback((
    type: OperationType,
    context: Operation['context'],
    metadata?: Record<string, any>
  ): string => {
    return addOperation({
      type,
      context,
      metadata
    })
  }, [addOperation])

  const updateProgress = useCallback((
    operationId: string,
    progress: number,
    step?: string,
    message?: string
  ) => {
    updateOperation(operationId, {
      progress: Math.max(0, Math.min(100, progress)),
      currentStep: step || '',
      status: 'in_progress',
      ...(message && { metadata: { message } })
    })
  }, [updateOperation])

  const completeOperation = useCallback((
    operationId: string,
    result?: Record<string, any>
  ) => {
    updateOperation(operationId, {
      status: 'completed',
      progress: 100,
      metadata: result ? { ...result } : undefined
    })
  }, [updateOperation])

  const errorOperation = useCallback((
    operationId: string,
    error: string
  ) => {
    updateOperation(operationId, {
      status: 'error',
      error
    })
  }, [updateOperation])

  return {
    operations,
    trackOperation,
    updateProgress,
    completeOperation,
    errorOperation,
    cancelOperation,
    getOperationsByContext,
    clearCompleted
  }
}
