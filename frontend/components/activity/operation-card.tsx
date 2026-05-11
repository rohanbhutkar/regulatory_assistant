"use client"

import React, { useState } from 'react'
import { Operation } from '@/lib/contexts/activity-context'
import { ActivityIcon } from './activity-icon'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { ChevronDown, ChevronUp, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { OperationDetails } from './operation-details'

interface OperationCardProps {
  operation: Operation
  onCancel?: (operationId: string) => void
}

export function OperationCard({ operation, onCancel }: OperationCardProps) {
  const [expanded, setExpanded] = useState(false)

  const getStatusColor = () => {
    switch (operation.status) {
      case 'completed':
        return 'text-green-600'
      case 'error':
        return 'text-red-600'
      case 'cancelled':
        return 'text-gray-600'
      case 'in_progress':
        return 'text-blue-600'
      default:
        return 'text-gray-600'
    }
  }

  const getTypeLabel = () => {
    return operation.type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const getContextLabel = () => {
    const parts: string[] = []
    if (operation.context.assetId) parts.push(`Asset: ${operation.context.assetId}`)
    if (operation.context.studyId) parts.push(`Study: ${operation.context.studyId}`)
    if (operation.context.tab) parts.push(`Tab: ${operation.context.tab}`)
    return parts.join(' • ') || 'Global'
  }

  return (
    <Card className="mb-2">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <ActivityIcon type={operation.type} status={operation.status} className="h-5 w-5 mt-0.5" />
            <div className="flex-1 min-w-0">
              <CardTitle className="text-sm font-medium">{getTypeLabel()}</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">{getContextLabel()}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {operation.status === 'in_progress' && onCancel && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => onCancel(operation.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-2">
          {operation.status === 'in_progress' && (
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className={cn("font-medium", getStatusColor())}>
                  {operation.currentStep || 'Processing...'}
                </span>
                <span className="text-muted-foreground">{Math.round(operation.progress)}%</span>
              </div>
              <Progress value={operation.progress} className="h-1.5" />
            </div>
          )}
          
          {operation.status === 'completed' && (
            <div className="text-xs text-green-600">
              Completed {operation.duration ? `in ${(operation.duration / 1000).toFixed(1)}s` : ''}
            </div>
          )}
          
          {operation.status === 'error' && (
            <div className="text-xs text-red-600">
              {operation.error || 'Operation failed'}
            </div>
          )}
          
          {operation.status === 'cancelled' && (
            <div className="text-xs text-gray-600">
              Cancelled
            </div>
          )}
          
          {expanded && <OperationDetails operation={operation} />}
        </div>
      </CardContent>
    </Card>
  )
}
