"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
// Progress component - using simple div-based progress bar
const Progress = ({ value }: { value: number }) => (
  <div className="w-full bg-gray-200 rounded-full h-2">
    <div
      className="bg-primary h-2 rounded-full transition-all"
      style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
    />
  </div>
)
import { TrendingUp, TrendingDown, DollarSign, Users, Calendar, Target } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'

interface AssetSummaryDashboardProps {
  assetId: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export function AssetSummaryDashboard({ assetId }: AssetSummaryDashboardProps) {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSummary()
  }, [assetId])

  const loadSummary = async () => {
    try {
      // Get value summary
      const valueResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/financial/value-summary/${assetId}?market=US`)
      const valueData = valueResponse.ok ? await valueResponse.json() : null

      // Get pricing data
      const pricingResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/pricing/${assetId}/US?include_uncertainty=true`)
      const pricingData = pricingResponse.ok ? await pricingResponse.json() : null

      // Get scenarios count
      const scenariosResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/?asset_id=${assetId}`)
      const scenariosData = scenariosResponse.ok ? await scenariosResponse.json() : null

      setSummary({
        value: valueData,
        pricing: pricingData,
        scenarios: scenariosData
      })
    } catch (error) {
      console.error('Failed to load summary:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8 text-muted-foreground">Loading summary...</div>
  }

  if (!summary) {
    return <div className="text-center py-8 text-muted-foreground">No summary data available</div>
  }

  const metrics = [
    {
      label: 'NPV',
      value: summary.value?.npv || 0,
      icon: DollarSign,
      trend: summary.value?.npv > 0 ? 'up' : 'neutral',
      format: (v: number) => `$${(v / 1000000).toFixed(1)}M`
    },
    {
      label: 'ROI',
      value: (summary.value?.roi || 0) * 100,
      icon: Target,
      trend: summary.value?.roi > 0 ? 'up' : 'neutral',
      format: (v: number) => `${v.toFixed(1)}%`
    },
    {
      label: 'Peak Sales',
      value: summary.value?.peak_sales || 0,
      icon: TrendingUp,
      trend: 'up',
      format: (v: number) => `$${(v / 1000000).toFixed(1)}M`
    },
    {
      label: 'Treated Patients',
      value: summary.value?.treated_patients || 0,
      icon: Users,
      trend: 'up',
      format: (v: number) => v.toLocaleString()
    },
    {
      label: 'Net Price',
      value: summary.pricing?.net_price || 0,
      icon: DollarSign,
      trend: 'neutral',
      format: (v: number) => `$${v.toLocaleString()}`
    },
    {
      label: 'Scenarios',
      value: summary.scenarios?.scenarios?.length || 0,
      icon: Calendar,
      trend: 'neutral',
      format: (v: number) => v.toString()
    }
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {metrics.map((metric) => {
          const Icon = metric.icon
          return (
            <Card key={metric.label}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{metric.label}</p>
                    <p className="text-2xl font-bold">{metric.format(metric.value)}</p>
                  </div>
                  <Icon className="h-8 w-8 text-muted-foreground" />
                </div>
                {metric.trend === 'up' && metric.value > 0 && (
                  <div className="flex items-center gap-1 mt-2 text-green-600 text-sm">
                    <TrendingUp className="h-3 w-3" />
                    <span>Positive</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Key Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Financial Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">NPV</span>
                <span className="text-sm font-medium">${(summary.value?.npv || 0).toLocaleString()}</span>
              </div>
              <Progress value={Math.min((summary.value?.npv || 0) / 100000000 * 100, 100)} />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">ROI</span>
                <span className="text-sm font-medium">{(summary.value?.roi || 0) * 100}%</span>
              </div>
              <Progress value={Math.min((summary.value?.roi || 0) * 100, 100)} />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Peak Sales</span>
                <span className="text-sm font-medium">${(summary.value?.peak_sales || 0).toLocaleString()}</span>
              </div>
              <Progress value={Math.min((summary.value?.peak_sales || 0) / 10000000 * 100, 100)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Patient & Market</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Treated Patients</span>
                <span className="text-sm font-medium">{(summary.value?.treated_patients || 0).toLocaleString()}</span>
              </div>
              <Progress value={Math.min((summary.value?.treated_patients || 0) / 100000 * 100, 100)} />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Net Price</span>
                <span className="text-sm font-medium">${(summary.pricing?.net_price || 0).toLocaleString()}</span>
              </div>
              <Progress value={Math.min((summary.pricing?.net_price || 0) / 200000 * 100, 100)} />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">GTN %</span>
                <span className="text-sm font-medium">
                  {summary.pricing?.waterfall_components?.gtn_percent?.toFixed(1) || '0'}%
                </span>
              </div>
              <Progress value={summary.pricing?.waterfall_components?.gtn_percent || 0} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
