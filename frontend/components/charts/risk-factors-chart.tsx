"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { AlertTriangle, AlertCircle, Info } from 'lucide-react'

interface RiskFactor {
  factor: string
  probability: number
  impact: string
  mitigation: string
  severity: 'Low' | 'Medium' | 'High'
}

interface RiskFactorsChartProps {
  riskFactors: RiskFactor[]
  title?: string
  description?: string
}

export function RiskFactorsChart({ 
  riskFactors, 
  title = "Risk Assessment",
  description = "Identified risk factors and mitigation strategies"
}: RiskFactorsChartProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'High':
        return 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20'
      case 'Medium':
        return 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20'
      case 'Low':
        return 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20'
      default:
        return 'bg-muted text-muted-foreground'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'High':
        return <AlertTriangle className="h-4 w-4" />
      case 'Medium':
        return <AlertCircle className="h-4 w-4" />
      case 'Low':
        return <Info className="h-4 w-4" />
      default:
        return null
    }
  }

  const getProbabilityColor = (probability: number) => {
    if (probability >= 0.7) return 'bg-red-500'
    if (probability >= 0.4) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  // Sort by severity then probability
  const sortedRisks = [...riskFactors].sort((a, b) => {
    const severityOrder = { High: 0, Medium: 1, Low: 2 }
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity]
    if (severityDiff !== 0) return severityDiff
    return b.probability - a.probability
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        {sortedRisks.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Info className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No significant risks identified</p>
          </div>
        ) : (
          sortedRisks.map((risk, index) => (
            <div
              key={index}
              className="border border-border rounded-lg p-4 space-y-3 hover:bg-muted/50 transition-colors"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <div className={`mt-0.5 ${getSeverityColor(risk.severity)}`}>
                    {getSeverityIcon(risk.severity)}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-foreground">{risk.factor}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{risk.impact}</p>
                  </div>
                </div>
                <Badge 
                  variant="outline" 
                  className={getSeverityColor(risk.severity)}
                >
                  {risk.severity}
                </Badge>
              </div>

              {/* Probability Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Probability</span>
                  <span className="font-medium">{(risk.probability * 100).toFixed(0)}%</span>
                </div>
                <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full ${getProbabilityColor(risk.probability)} transition-all`}
                    style={{ width: `${risk.probability * 100}%` }}
                  />
                </div>
              </div>

              {/* Mitigation */}
              <div className="bg-muted/50 rounded-md p-3 space-y-1">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Mitigation Strategy
                </p>
                <p className="text-sm text-foreground">{risk.mitigation}</p>
              </div>
            </div>
          ))
        )}

        {/* Summary Stats */}
        {sortedRisks.length > 0 && (
          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {sortedRisks.filter(r => r.severity === 'High').length}
              </div>
              <div className="text-xs text-muted-foreground mt-1">High Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {sortedRisks.filter(r => r.severity === 'Medium').length}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Medium Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {sortedRisks.filter(r => r.severity === 'Low').length}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Low Risk</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}









