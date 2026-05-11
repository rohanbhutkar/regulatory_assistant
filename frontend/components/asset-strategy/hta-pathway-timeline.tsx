"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Timeline, CheckCircle } from 'lucide-react'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'

interface HTAPathwayTimelineProps {
  assetId: string
  market: string
}

export function HTAPathwayTimeline({ assetId, market }: HTAPathwayTimelineProps) {
  const [pathway, setPathway] = useState<any>(null)
  const [selectedMarket, setSelectedMarket] = useState(market)

  useEffect(() => {
    loadPathway()
  }, [assetId, selectedMarket])

  const loadPathway = async () => {
    try {
      const response = await fetch(assetStrategyAPI.getHTAPathway(assetId, selectedMarket))
      if (response.ok) {
        const data = await response.json()
        setPathway(data)
      }
    } catch (error) {
      console.error('Failed to load pathway:', error)
    }
  }

  if (!pathway) {
    return <div>Loading...</div>
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>HTA Pathway Timeline</CardTitle>
            <CardDescription>{pathway.hta_body} - {selectedMarket}</CardDescription>
          </div>
          <Select value={selectedMarket} onValueChange={setSelectedMarket}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="CN">CN</SelectItem>
              <SelectItem value="DE">DE</SelectItem>
              <SelectItem value="JP">JP</SelectItem>
              <SelectItem value="US">US</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {pathway.steps?.map((step: any, idx: number) => (
            <div key={idx} className="flex items-start gap-4">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <CheckCircle className="h-5 w-5 text-blue-600" />
                </div>
                {idx < pathway.steps.length - 1 && (
                  <div className="w-0.5 h-12 bg-gray-200 mt-2" />
                )}
              </div>
              <div className="flex-1 pb-4">
                <div className="font-medium">{step.step}</div>
                <div className="text-sm text-gray-500">
                  Duration: {step.duration_months} months
                </div>
                {step.required_inputs && step.required_inputs.length > 0 && (
                  <div className="text-sm text-gray-600 mt-1">
                    Required: {step.required_inputs.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div className="pt-4 border-t">
            <div className="text-sm text-gray-500">Total Timeline</div>
            <div className="text-lg font-semibold">{pathway.total_timeline_months} months</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

