"use client"

import React from 'react'
import { useActivity } from '@/lib/contexts/activity-context'
import { OperationType } from '@/lib/contexts/activity-context'
import { ActivityIcon } from './activity-icon'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

interface InlineActivityIndicatorProps {
  operationType: OperationType
  context: {
    assetId?: string
    studyId?: string
    tab?: string
  }
  compact?: boolean
}

export function InlineActivityIndicator({ 
  operationType, 
  context, 
  compact = false 
}: InlineActivityIndicatorProps) {
  const { getOperationsByContext } = useActivity()
  
  const relevantOperations = getOperationsByContext(context).filter(
    op => op.type === operationType && (op.status === 'pending' || op.status === 'in_progress')
  )

  if (relevantOperations.length === 0) {
    return null
  }

  // Show the most recent active operation
  const operation = relevantOperations[0]

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ActivityIcon type={operation.type} status={operation.status} className="h-3 w-3" />
        <span>{operation.currentStep || 'Processing...'}</span>
        {operation.status === 'in_progress' && (
          <span className="text-muted-foreground">{Math.round(operation.progress)}%</span>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2 p-3 border rounded-lg bg-muted/50">
      <div className="flex items-center gap-2">
        <ActivityIcon type={operation.type} status={operation.status} className="h-4 w-4" />
        <div className="flex-1">
          <div className="text-sm font-medium">
            {operation.type
              .split('_')
              .map(word => word.charAt(0).toUpperCase() + word.slice(1))
              .join(' ')}
          </div>
          {operation.currentStep && (
            <div className="text-xs text-muted-foreground mt-0.5">
              {operation.currentStep}
            </div>
          )}
        </div>
        {operation.status === 'in_progress' && (
          <div className="text-xs text-muted-foreground">
            {Math.round(operation.progress)}%
          </div>
        )}
      </div>
      {operation.status === 'in_progress' && (
        <Progress value={operation.progress} className="h-1.5" />
      )}
    </div>
  )
}
