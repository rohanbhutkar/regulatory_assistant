"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'

interface PriceConfidenceWidgetProps {
  assetId: string
  market: string
}

export function PriceConfidenceWidget({ assetId, market }: PriceConfidenceWidgetProps) {
  const [confidence, setConfidence] = useState<any>(null)

  useEffect(() => {
    loadConfidence()
  }, [assetId, market])

  const loadConfidence = async () => {
    try {
      const response = await fetch(`${assetStrategyAPI.getPricePrediction(assetId, market)}?include_uncertainty=true`)
      if (response.ok) {
        const data = await response.json()
        setConfidence(data)
      }
    } catch (error) {
      console.error('Failed to load confidence:', error)
    }
  }

  if (!confidence) {
    return <div>Loading...</div>
  }

  const confidenceScore = (confidence.confidence_score || 0) * 100
  const confidenceColor = confidenceScore >= 80 ? 'green' : confidenceScore >= 60 ? 'yellow' : 'red'

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price Confidence</CardTitle>
        <CardDescription>Uncertainty and data coverage</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm">Confidence Score</span>
            <Badge className={confidenceColor === 'green' ? 'bg-green-100 text-green-800' : confidenceColor === 'yellow' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}>
              {confidenceScore.toFixed(0)}%
            </Badge>
          </div>
          <Progress value={confidenceScore} className="h-2" />
        </div>

        {confidence.net_price_p10 && (
          <div className="space-y-2">
            <div className="text-sm text-gray-500">Confidence Bands</div>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <div className="text-gray-500">P10</div>
                <div className="font-semibold">${confidence.net_price_p10.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500">P50</div>
                <div className="font-semibold">${confidence.net_price_p50.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500">P90</div>
                <div className="font-semibold">${confidence.net_price_p90.toLocaleString()}</div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

