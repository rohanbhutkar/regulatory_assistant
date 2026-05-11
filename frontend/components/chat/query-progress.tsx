import React from 'react'
import { CheckCircle2, Circle, Loader2 } from 'lucide-react'

export interface QueryStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'in-progress' | 'completed' | 'error'
  agent: string
}

interface QueryProgressProps {
  steps: QueryStep[]
  currentStep?: string
}

export function QueryProgress({ steps, currentStep }: QueryProgressProps) {
  return (
    <div className="bg-muted/50 border border-border/40 rounded-lg p-4 max-w-2xl space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span className="text-sm font-medium text-foreground">Processing Query</span>
      </div>
      
      <div className="space-y-2">
        {steps.map((step, index) => {
          const isCurrentStep = step.id === currentStep
          const isCompleted = step.status === 'completed'
          const isError = step.status === 'error'
          
          return (
            <div
              key={step.id}
              className={`flex items-start gap-3 p-2 rounded-md transition-colors ${
                isCurrentStep ? 'bg-primary/10' : ''
              }`}
            >
              <div className="mt-0.5">
                {isCompleted ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : isCurrentStep ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : isError ? (
                  <Circle className="h-4 w-4 text-destructive" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground/40" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${
                    isCompleted ? 'text-muted-foreground' : 
                    isCurrentStep ? 'text-foreground' : 
                    'text-muted-foreground/60'
                  }`}>
                    {index + 1}. {step.name}
                  </span>
                  {step.agent && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {step.agent}
                    </span>
                  )}
                </div>
                {step.description && (
                  <p className={`text-xs mt-0.5 ${
                    isCurrentStep ? 'text-muted-foreground' : 'text-muted-foreground/60'
                  }`}>
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
