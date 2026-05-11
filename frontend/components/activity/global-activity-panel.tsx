"use client"

import React, { useState, useMemo } from 'react'
import { useActivity } from '@/lib/contexts/activity-context'
import { OperationCard } from './operation-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X, Activity, Filter } from 'lucide-react'
import { cn } from '@/lib/utils'

export function GlobalActivityPanel() {
  const { operations, cancelOperation, clearCompleted } = useActivity()
  const [isOpen, setIsOpen] = useState(false)
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('active')

  const activeOperations = useMemo(() => {
    return operations.filter(op => 
      op.status === 'pending' || op.status === 'in_progress'
    )
  }, [operations])

  const filteredOperations = useMemo(() => {
    switch (filter) {
      case 'active':
        return operations.filter(op => 
          op.status === 'pending' || op.status === 'in_progress'
        )
      case 'completed':
        return operations.filter(op => 
          op.status === 'completed' || op.status === 'error' || op.status === 'cancelled'
        )
      default:
        return operations
    }
  }, [operations, filter])

  if (!isOpen && activeOperations.length === 0) {
    return null
  }

  return (
    <>
      {/* Floating button to open panel */}
      {!isOpen && activeOperations.length > 0 && (
        <div className="fixed bottom-4 right-4 z-50">
          <Button
            onClick={() => setIsOpen(true)}
            className="rounded-full h-12 w-12 shadow-lg"
            size="icon"
          >
            <Activity className="h-5 w-5" />
            {activeOperations.length > 0 && (
              <Badge 
                className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
                variant="destructive"
              >
                {activeOperations.length}
              </Badge>
            )}
          </Button>
        </div>
      )}

      {/* Activity Panel */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 z-50 w-96 max-h-[600px]">
          <Card className="shadow-2xl">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  <CardTitle className="text-lg">Activity</CardTitle>
                  {activeOperations.length > 0 && (
                    <Badge variant="secondary">{activeOperations.length} active</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setFilter(filter === 'all' ? 'active' : filter === 'active' ? 'completed' : 'all')}
                    title="Filter"
                  >
                    <Filter className="h-4 w-4" />
                  </Button>
                  {filter === 'completed' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearCompleted}
                      className="text-xs"
                    >
                      Clear
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setIsOpen(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {/* Filter tabs */}
              <div className="flex gap-1 mt-2">
                <Button
                  variant={filter === 'all' ? 'default' : 'ghost'}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter('all')}
                >
                  All ({operations.length})
                </Button>
                <Button
                  variant={filter === 'active' ? 'default' : 'ghost'}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter('active')}
                >
                  Active ({activeOperations.length})
                </Button>
                <Button
                  variant={filter === 'completed' ? 'default' : 'ghost'}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter('completed')}
                >
                  Completed ({operations.filter(op => op.status === 'completed' || op.status === 'error' || op.status === 'cancelled').length})
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-3 overflow-y-auto max-h-[500px]">
              {filteredOperations.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground py-8">
                  No {filter === 'all' ? '' : filter} operations
                </div>
              ) : (
                <div>
                  {filteredOperations.map(operation => (
                    <OperationCard
                      key={operation.id}
                      operation={operation}
                      onCancel={cancelOperation}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </>
  )
}
