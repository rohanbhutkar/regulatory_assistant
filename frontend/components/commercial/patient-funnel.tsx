"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PatientFunnel } from "@/lib/types/commercial-types"
import { Users } from "lucide-react"

interface PatientFunnelProps {
  funnel: PatientFunnel[]
}

export function PatientFunnelVisualization({ funnel }: PatientFunnelProps) {
  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          Patient Funnel Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {funnel.map((stage, index) => (
          <div key={stage.stage} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">{stage.stage}</span>
              <div className="text-right">
                <span className="text-lg font-bold text-foreground">{stage.patients.toLocaleString()}</span>
                <span className="text-xs text-muted-foreground ml-2">({stage.percentage.toFixed(1)}%)</span>
              </div>
            </div>
            <div className="relative h-12 bg-secondary rounded-lg overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 flex items-center justify-center text-white font-semibold text-sm transition-all duration-500"
                style={{
                  width: `${stage.percentage}%`,
                  backgroundColor: stage.color,
                }}
              >
                {stage.percentage > 15 && `${stage.percentage.toFixed(1)}%`}
              </div>
            </div>
            {index < funnel.length - 1 && (
              <div className="flex justify-center">
                <div className="h-4 w-0.5 bg-border" />
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}





















