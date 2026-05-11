"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface HTAOutcomeLikelihoodProps {
  assetId: string
  market: string
}

const COLORS = {
  approval: '#10b981',
  restriction: '#f59e0b',
  rejection: '#ef4444'
}

export function HTAOutcomeLikelihood({ assetId, market }: HTAOutcomeLikelihoodProps) {
  const [outcome, setOutcome] = useState<any>(null)

  useEffect(() => {
    loadOutcome()
  }, [assetId, market])

  const loadOutcome = async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/hta/outcome-likelihood`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          market: market,
          evidence_strength: 0.7,
          comparator_clarity: 0.6,
          precedent_strength: 0.5,
          policy_environment: 'moderate'
        })
      })

      if (response.ok) {
        const data = await response.json()
        setOutcome(data)
      }
    } catch (error) {
      console.error('Failed to load outcome:', error)
    }
  }

  if (!outcome) {
    return <div>Loading...</div>
  }

  const chartData = [
    { name: 'Approval', value: outcome.outcome_likelihood.approval * 100, color: COLORS.approval },
    { name: 'Restriction', value: outcome.outcome_likelihood.restriction * 100, color: COLORS.restriction },
    { name: 'Rejection', value: outcome.outcome_likelihood.rejection * 100, color: COLORS.rejection }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>HTA Outcome Likelihood</CardTitle>
        <CardDescription>Predicted outcome distribution</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">Confidence</div>
          <div className="text-lg font-semibold">{(outcome.confidence * 100).toFixed(0)}%</div>
        </div>
      </CardContent>
    </Card>
  )
}


