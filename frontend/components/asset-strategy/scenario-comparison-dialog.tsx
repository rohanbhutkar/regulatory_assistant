"use client"

import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface ScenarioComparisonDialogProps {
  scenarios: Array<{ scenario_id?: string; name: string }>
  onCompare: (scenario1Id: string, scenario2Id: string) => Promise<any>
  comparisonResults: any
}

export function ScenarioComparisonDialog({ scenarios, onCompare, comparisonResults }: ScenarioComparisonDialogProps) {
  const [scenario1Id, setScenario1Id] = useState<string>('')
  const [scenario2Id, setScenario2Id] = useState<string>('')
  const [isOpen, setIsOpen] = useState(false)
  const [isComparing, setIsComparing] = useState(false)

  const handleCompare = async () => {
    if (!scenario1Id || !scenario2Id) {
      return
    }
    setIsComparing(true)
    try {
      await onCompare(scenario1Id, scenario2Id)
    } finally {
      setIsComparing(false)
    }
  }

  const formatDelta = (value: number) => {
    if (value === 0) return <span className="text-gray-600">No change</span>
    const isPositive = value > 0
    const Icon = isPositive ? TrendingUp : TrendingDown
    const color = isPositive ? 'text-green-600' : 'text-red-600'
    return (
      <span className={`flex items-center gap-1 ${color}`}>
        <Icon className="h-4 w-4" />
        {isPositive ? '+' : ''}{value.toLocaleString()}
      </span>
    )
  }

  const chartData = comparisonResults?.deltas ? [
    {
      metric: 'Net Price',
      delta: comparisonResults.deltas.net_price || 0
    },
    {
      metric: 'NPV',
      delta: comparisonResults.deltas.npv || 0
    },
    {
      metric: 'Peak Sales',
      delta: comparisonResults.deltas.peak_sales || 0
    },
    {
      metric: 'rNPV',
      delta: comparisonResults.deltas.rnpv || 0
    }
  ] : []

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          Compare Scenarios
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Compare Scenarios</DialogTitle>
          <DialogDescription>Select two scenarios to compare their financial outcomes</DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Base Scenario</label>
              <Select value={scenario1Id} onValueChange={setScenario1Id}>
                <SelectTrigger>
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  {scenarios.map((s) => (
                    <SelectItem key={s.scenario_id} value={s.scenario_id!}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Comparison Scenario</label>
              <Select value={scenario2Id} onValueChange={setScenario2Id}>
                <SelectTrigger>
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  {scenarios.map((s) => (
                    <SelectItem key={s.scenario_id} value={s.scenario_id!}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button 
            onClick={handleCompare} 
            disabled={!scenario1Id || !scenario2Id || scenario1Id === scenario2Id || isComparing}
            className="w-full"
          >
            {isComparing ? 'Comparing...' : 'Compare'}
          </Button>

          {comparisonResults && comparisonResults.deltas && (
            <Card>
              <CardHeader>
                <CardTitle>Comparison Results</CardTitle>
                <CardDescription>Differences between scenarios</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Net Price Δ</p>
                      <p className="text-lg font-bold">
                        {formatDelta(comparisonResults.deltas.net_price || 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">NPV Δ</p>
                      <p className="text-lg font-bold">
                        {formatDelta(comparisonResults.deltas.npv || 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Peak Sales Δ</p>
                      <p className="text-lg font-bold">
                        {formatDelta(comparisonResults.deltas.peak_sales || 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">rNPV Δ</p>
                      <p className="text-lg font-bold">
                        {formatDelta(comparisonResults.deltas.rnpv || 0)}
                      </p>
                    </div>
                  </div>

                  {chartData.length > 0 && (
                    <div className="mt-6">
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="metric" />
                          <YAxis />
                          <Tooltip formatter={(value: any) => value.toLocaleString()} />
                          <Legend />
                          <Bar dataKey="delta" fill="#8884d8" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
