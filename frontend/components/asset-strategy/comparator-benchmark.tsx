"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts'
import { toast } from 'sonner'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'

interface ComparatorBenchmarkProps {
  assetId: string
  market: string
  predictedPrice: number
}

export function ComparatorBenchmark({ assetId, market, predictedPrice }: ComparatorBenchmarkProps) {
  const [benchmark, setBenchmark] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBenchmark()
  }, [assetId, market, predictedPrice])

  const loadBenchmark = async () => {
    setLoading(true)
    setError(null)
    try {
      console.log('📊 Loading comparator benchmark:', { assetId, market, predictedPrice })
      const url = `${assetStrategyAPI.getComparators(assetId, market)}${predictedPrice ? `&predicted_net_price=${predictedPrice}` : ''}`
      const response = await fetch(url)
      
      if (response.ok) {
        const data = await response.json()
        console.log('📊 Benchmark data received:', data)
        setBenchmark(data)
      } else {
        const errorText = await response.text()
        console.error('❌ Failed to load benchmark:', response.status, errorText)
        setError(`Failed to load: ${response.statusText}`)
      }
    } catch (error) {
      console.error('❌ Error loading benchmark:', error)
      setError('Failed to load comparator benchmark')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <div className="text-center text-gray-500">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
              <p>Loading comparator benchmark...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !benchmark) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Comparator Benchmark</CardTitle>
          <CardDescription>Price positioning vs comparators</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <p>{error || 'No benchmark data available'}</p>
            <p className="text-xs mt-2">{benchmark?.message || 'Generate price prediction first to see benchmarks'}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Use individual comparators for chart if available, otherwise use percentiles
  const chartData = benchmark.comparators && benchmark.comparators.length > 0
    ? benchmark.comparators
        .filter((comp: any) => comp.price && comp.price > 0)
        .map((comp: any, idx: number) => ({
          name: comp.drug || comp.name || `Comparator ${idx + 1}`,
          value: comp.price || 0,
          drug: comp.drug || comp.name,
          coverage: comp.coverage?.coverage_level || "Unknown"
        }))
        .sort((a: any, b: any) => a.value - b.value) // Sort by price
    : benchmark.percentiles && Object.keys(benchmark.percentiles).length > 0
    ? [
        { name: 'P10', value: benchmark.percentiles.p10 },
        { name: 'P25', value: benchmark.percentiles.p25 },
        { name: 'P50', value: benchmark.percentiles.p50 },
        { name: 'P75', value: benchmark.percentiles.p75 },
        { name: 'P90', value: benchmark.percentiles.p90 }
      ]
    : []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comparator Benchmark</CardTitle>
        <CardDescription>Price positioning vs comparators</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {chartData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="name" 
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 11 }}
                  interval={0}
                />
                <YAxis 
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip 
                  formatter={(value: number, payload: any) => {
                    const data = payload?.payload
                    if (data?.coverage) {
                      return [`$${value.toLocaleString()}`, `Coverage: ${data.coverage}`]
                    }
                    return `$${value.toLocaleString()}`
                  }}
                  labelStyle={{ fontWeight: 'bold' }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry: any, index: number) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.coverage === "Unrestricted" ? "#10b981" : 
                            entry.coverage === "Restricted" ? "#f59e0b" :
                            entry.coverage === "Not Covered" ? "#ef4444" : "#3b82f6"} 
                    />
                  ))}
                </Bar>
                {predictedPrice > 0 && (
                  <ReferenceLine
                    y={predictedPrice}
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    label={{ 
                      value: 'Predicted', 
                      position: 'top',
                      fill: '#10b981',
                      fontSize: 12,
                      fontWeight: 'bold'
                    }}
                  />
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
            <div className="text-center text-gray-500">
              <p className="font-medium mb-1">No comparator data available</p>
              <p className="text-xs mb-3">{benchmark.message || 'Generate comparators with pricing data to see benchmarks'}</p>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => {
                  // Navigate to overview tab to generate comparators
                  const url = window.location.href.split('?')[0]
                  window.location.href = `${url}?tab=overview`
                  toast.info('Navigate to Overview tab and click "Generate Comparators"')
                }}
              >
                Go to Overview Tab
              </Button>
            </div>
          </div>
        )}

        {benchmark.premium_discount && (
          <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded">
            <div>
              <div className="text-sm text-gray-500">Premium/Discount</div>
              <div className={`text-lg font-semibold ${benchmark.premium_discount.percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {benchmark.premium_discount.percent >= 0 ? '+' : ''}{benchmark.premium_discount.percent.toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">vs Median</div>
              <div className="text-lg font-semibold">
                ${Math.abs(benchmark.premium_discount.absolute).toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Comparators</div>
              <div className="text-lg font-semibold">{benchmark.comparator_count}</div>
            </div>
          </div>
        )}

        {/* Comparator Coverage Information */}
        {benchmark.comparators && benchmark.comparators.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-semibold mb-2">Comparator Coverage Information</h4>
            <div className="max-h-64 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Drug</TableHead>
                    <TableHead className="text-xs">Price</TableHead>
                    <TableHead className="text-xs">Coverage</TableHead>
                    <TableHead className="text-xs">Restrictions</TableHead>
                    <TableHead className="text-xs">Tier</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {benchmark.comparators.slice(0, 10).map((comp: any, idx: number) => (
                    <TableRow key={idx}>
                      <TableCell className="text-xs font-medium">{comp.drug || comp.name || "Unknown"}</TableCell>
                      <TableCell className="text-xs">${(comp.price || 0).toLocaleString()}</TableCell>
                      <TableCell className="text-xs">
                        <Badge variant="outline" className="text-xs">
                          {comp.coverage?.coverage_level || comp.coverage_level || "Unknown"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        {comp.coverage?.restrictions && Array.isArray(comp.coverage.restrictions) && comp.coverage.restrictions.length > 0
                          ? comp.coverage.restrictions.join(", ")
                          : comp.coverage?.restrictions && typeof comp.coverage.restrictions === 'object'
                          ? Object.keys(comp.coverage.restrictions).filter((k: string) => comp.coverage.restrictions[k] > 0).join(", ")
                          : "None"
                        }
                      </TableCell>
                      <TableCell className="text-xs">{comp.coverage?.tier || comp.tier || "N/A"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

