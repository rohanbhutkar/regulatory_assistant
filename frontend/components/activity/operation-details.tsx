"use client"

import React from 'react'
import { Operation } from '@/lib/contexts/activity-context'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface OperationDetailsProps {
  operation: Operation
}

export function OperationDetails({ operation }: OperationDetailsProps) {
  const getStepIcon = (status: Operation['steps'][0]['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-3 w-3 text-green-500" />
      case 'in_progress':
        return <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />
      case 'error':
        return <XCircle className="h-3 w-3 text-red-500" />
      default:
        return <Circle className="h-3 w-3 text-gray-400" />
    }
  }

  return (
    <div className="mt-3 pt-3 border-t space-y-2">
      <div className="text-xs font-medium text-muted-foreground mb-2">Steps</div>
      {operation.steps.length > 0 ? (
        <div className="space-y-1.5">
          {operation.steps.map((step, index) => (
            <div key={index} className="flex items-start gap-2 text-xs">
              <div className="mt-0.5">{getStepIcon(step.status)}</div>
              <div className="flex-1">
                <div className={cn(
                  "font-medium",
                  step.status === 'completed' && "text-green-600",
                  step.status === 'in_progress' && "text-blue-600",
                  step.status === 'error' && "text-red-600",
                  step.status === 'pending' && "text-gray-500"
                )}>
                  {step.name}
                </div>
                {step.duration && (
                  <div className="text-muted-foreground text-[10px] mt-0.5">
                    {step.duration.toFixed(1)}s
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">No step details available</div>
      )}
      
      {operation.metadata && Object.keys(operation.metadata).length > 0 && (
        <div className="mt-3 pt-3 border-t">
          <div className="text-xs font-medium text-muted-foreground mb-2">Metadata</div>
          <div className="text-xs space-y-1">
            {Object.entries(operation.metadata).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="text-muted-foreground">{key}:</span>
                <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
