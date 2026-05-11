"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'

interface AccessRiskScoreProps {
  assetId: string
  market: string
}

export function AccessRiskScore({ assetId, market }: AccessRiskScoreProps) {
  const [risk, setRisk] = useState<any>(null)

  useEffect(() => {
    loadRisk()
  }, [assetId, market])

  const loadRisk = async () => {
    try {
      const response = await fetch(assetStrategyAPI.getAccessRisk(assetId, market))
      if (response.ok) {
        const data = await response.json()
        setRisk(data)
      }
    } catch (error) {
      console.error('Failed to load risk:', error)
    }
  }

  if (!risk) {
    return <div>Loading...</div>
  }

  const riskScore = risk.access_risk_score
  const riskColor = riskScore < 30 ? 'green' : riskScore < 60 ? 'yellow' : 'red'

  return (
    <Card>
      <CardHeader>
        <CardTitle>Access Risk Score</CardTitle>
        <CardDescription>Risk assessment (0-100)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm">Overall Risk</span>
            <Badge className={riskColor === 'green' ? 'bg-green-100 text-green-800' : riskColor === 'yellow' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}>
              {riskScore.toFixed(0)}/100
            </Badge>
          </div>
          <Progress value={riskScore} className="h-3" />
        </div>

        {risk.breakdown && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Risk Breakdown</div>
            {Object.entries(risk.breakdown).map(([key, value]: [string, any]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-gray-600 capitalize">{key.replace('_', ' ')}</span>
                <span className="font-medium">{value.score.toFixed(0)}/{value.max}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

