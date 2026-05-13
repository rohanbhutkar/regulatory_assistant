"use client"

import { useEffect, useRef } from 'react'
import { useActivityHook } from './use-activity'
import { OperationType, Operation } from '../contexts/activity-context'

interface UseOperationTrackerOptions {
  type: OperationType
  context: Operation['context']
  metadata?: Record<string, any>
  autoStart?: boolean
}

export function useOperationTracker(options: UseOperationTrackerOptions) {
  const { trackOperation, updateProgress, completeOperation, errorOperation, cancelOperation } = useActivityHook()
  const operationIdRef = useRef<string | null>(null)

  const { operations } = useActivityHook()

  useEffect(() => {
    if (options.autoStart !== false) {
      operationIdRef.current = trackOperation(options.type, options.context, options.metadata)
    }

    return () => {
      // Cleanup on unmount - cancel if still in progress
      if (operationIdRef.current) {
        const op = operations.find(o => o.id === operationIdRef.current!)
        if (op && (op.status === 'pending' || op.status === 'in_progress')) {
          cancelOperation(operationIdRef.current)
        }
      }
    }
  }, [])

  const start = () => {
    if (!operationIdRef.current) {
      operationIdRef.current = trackOperation(options.type, options.context, options.metadata)
    }
    return operationIdRef.current
  }

  const update = (progress: number, step?: string, message?: string) => {
    if (operationIdRef.current) {
      updateProgress(operationIdRef.current, progress, step, message)
    }
  }

  const complete = (result?: Record<string, any>) => {
    if (operationIdRef.current) {
      completeOperation(operationIdRef.current, result)
      operationIdRef.current = null
    }
  }

  const error = (errorMessage: string) => {
    if (operationIdRef.current) {
      errorOperation(operationIdRef.current, errorMessage)
      operationIdRef.current = null
    }
  }

  const cancel = () => {
    if (operationIdRef.current) {
      cancelOperation(operationIdRef.current)
      operationIdRef.current = null
    }
  }

  return {
    operationId: operationIdRef.current,
    start,
    update,
    complete,
    error,
    cancel
  }
}
