"use client"

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Sparkles, Loader2, Info, Database, TrendingDown } from 'lucide-react'
import { toast } from 'sonner'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'
import { useAssetStrategy } from '@/lib/contexts/asset-strategy-context'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface PriceWaterfallProps {
  assetId: string
  market: string
  priceData?: any // Optional priceData from parent (AI generation)
}

export function PriceWaterfall({ assetId, market, priceData }: PriceWaterfallProps) {
  const { getTabContent } = useAssetStrategy()
  const [waterfall, setWaterfall] = useState<any>(null)
  const [listPrice, setListPrice] = useState(100000)
  const [mandatoryDiscount, setMandatoryDiscount] = useState(0)
  const [rebates, setRebates] = useState(0)
  const [clawbacks, setClawbacks] = useState(0)
  const [programAdjustments, setProgramAdjustments] = useState(0)
  const [loading, setLoading] = useState(false)
  // Default to showing details if we have GTN breakdown or data sources
  const [showDetails, setShowDetails] = useState(false)
  const { suggestPricingParameters, isGenerating } = useAssetStrategyGeneration()
  
  // Load saved state
  const savedState = getTabContent('pricing') || {}
  
  // Auto-expand details if we have GTN breakdown data
  useEffect(() => {
    if (waterfall?.gtn_breakdown && Object.keys(waterfall.gtn_breakdown).length > 0) {
      setShowDetails(true)
    }
  }, [waterfall?.gtn_breakdown])

  const handleAIGeneratePricing = async () => {
    const response = await suggestPricingParameters({
      asset_id: assetId,
      context: { market }
    })
    
    if (response?.content) {
      // Try to extract pricing recommendations from AI response
      // This is a simplified extraction - in production, would parse structured response
      const content = response.content.toLowerCase()
      
      // Look for price mentions
      const priceMatch = content.match(/\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)/)
      if (priceMatch) {
        const suggestedPrice = parseFloat(priceMatch[1].replace(/,/g, ''))
        if (suggestedPrice > 0) {
          setListPrice(suggestedPrice)
          toast.success(`AI suggested list price: $${suggestedPrice.toLocaleString()}`)
        }
      }
      
      // Look for discount/rebate percentages
      const discountMatch = content.match(/(\d+(?:\.\d+)?)\s*%?\s*(?:discount|rebate)/i)
      if (discountMatch) {
        const suggestedDiscount = parseFloat(discountMatch[1])
        if (suggestedDiscount > 0 && suggestedDiscount < 100) {
          setMandatoryDiscount(suggestedDiscount)
        }
      }
      
      toast.info('AI pricing recommendations applied. Review and adjust as needed.')
    } else {
      toast.error('Failed to generate pricing recommendations')
    }
  }

  const calculateWaterfall = useCallback(async () => {
    setLoading(true)
    try {
      console.log('📊 Calculating waterfall with:', { assetId, market, listPrice, mandatoryDiscount, rebates, clawbacks })
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/pricing/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          market: market,
          list_price: listPrice,
          mandatory_discount_pct: mandatoryDiscount,
          expected_rebates: rebates,
          clawbacks: clawbacks,
          program_adjustments: programAdjustments,
          include_uncertainty: false
        })
      })

      if (response.ok) {
        const data = await response.json()
        console.log('📊 Waterfall response:', data)
        
        if (data.waterfall_components) {
          setWaterfall(data.waterfall_components)
          
          // Log transparency info
          if (data.waterfall_components.data_sources_used?.length > 0) {
            console.log('📊 Data sources used:', data.waterfall_components.data_sources_used)
            toast.info(`GTN calculated using: ${data.waterfall_components.data_sources_used.join(', ')}`)
          }
        } else {
          // Fallback to waterfall endpoint
          const waterfallResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/pricing/waterfall`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              asset_id: assetId,
              market: market,
              list_price: listPrice,
              mandatory_discount_pct: mandatoryDiscount,
              expected_rebates: rebates,
              clawbacks: clawbacks,
              program_adjustments: programAdjustments
            })
          })
          
          if (waterfallResponse.ok) {
            const waterfallData = await waterfallResponse.json()
            setWaterfall(waterfallData)
            console.log('📊 Waterfall calculated (fallback):', waterfallData)
          }
        }
      } else {
        const errorText = await response.text()
        console.error('❌ Waterfall calculation failed:', response.status, errorText)
        toast.error(`Failed to calculate waterfall: ${response.statusText}`)
      }
    } catch (error) {
      console.error('❌ Failed to calculate waterfall:', error)
      toast.error('Failed to calculate waterfall')
    } finally {
      setLoading(false)
    }
  }, [assetId, market, listPrice, mandatoryDiscount, rebates, clawbacks, programAdjustments])

  // Update from priceData prop when AI generation completes
  useEffect(() => {
    if (priceData?.waterfall_components) {
      console.log('📊 PriceWaterfall: Received priceData from AI generation', priceData)
      const components = priceData.waterfall_components
      setWaterfall(components)
      setListPrice(components.list_price || listPrice)
      setMandatoryDiscount(components.mandatory_discount?.percent || 0)
      setRebates(components.expected_rebates || 0)
      setClawbacks(components.clawbacks || 0)
      setProgramAdjustments(components.program_adjustments || 0)
      
      // Log transparency info
      if (components.data_sources_used && components.data_sources_used.length > 0) {
        console.log('📊 Data sources used:', components.data_sources_used)
        toast.info(`GTN calculated using: ${components.data_sources_used.join(', ')}`)
      }
      if (components.gtn_breakdown && Object.keys(components.gtn_breakdown).length > 0) {
        console.log('📊 GTN Breakdown:', components.gtn_breakdown)
      }
    }
  }, [priceData, listPrice])

  // Initial load or manual calculation
  useEffect(() => {
    if (!priceData?.waterfall_components) {
      calculateWaterfall()
    }
  }, [assetId, market, priceData, calculateWaterfall])

  if (!waterfall && loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            <span>Calculating price waterfall...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!waterfall) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-gray-500">
            <p>No waterfall data available</p>
            <Button onClick={calculateWaterfall} className="mt-4" size="sm">
              Calculate Waterfall
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Build chart data from waterfall components
  // Handle both object and direct value structures
  const mandatoryDiscountValue = typeof waterfall.mandatory_discount === 'object' 
    ? (waterfall.mandatory_discount?.value || 0)
    : (waterfall.mandatory_discount || 0)
  
  const chartData = [
    {
      name: 'List Price',
      value: waterfall.list_price || 0,
      type: 'positive',
      label: `$${(waterfall.list_price || 0).toLocaleString()}`
    },
    {
      name: 'Mandatory Discount',
      value: -mandatoryDiscountValue,
      type: 'negative',
      label: `-$${Math.abs(mandatoryDiscountValue).toLocaleString()}`
    },
    {
      name: 'Rebates',
      value: -(waterfall.expected_rebates || 0),
      type: 'negative',
      label: `-$${Math.abs(waterfall.expected_rebates || 0).toLocaleString()}`
    },
    {
      name: 'Clawbacks',
      value: -(waterfall.clawbacks || 0),
      type: 'negative',
      label: `-$${Math.abs(waterfall.clawbacks || 0).toLocaleString()}`
    },
    {
      name: 'Program Adjustments',
      value: -(waterfall.program_adjustments || 0),
      type: 'negative',
      label: `-$${Math.abs(waterfall.program_adjustments || 0).toLocaleString()}`
    },
    {
      name: 'Net Price',
      value: waterfall.net_price || 0,
      type: 'positive',
      label: `$${(waterfall.net_price || 0).toLocaleString()}`
    }
  ].filter(item => {
    // Always show List Price and Net Price, filter out zero-value deductions
    if (item.name === 'List Price' || item.name === 'Net Price') return true
    return Math.abs(item.value) > 0.01 // Show if value is significant (>$0.01)
  })

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Price Waterfall</CardTitle>
            <CardDescription>List-to-Net price breakdown</CardDescription>
          </div>
          <Button
            onClick={handleAIGeneratePricing}
            disabled={isGenerating}
            size="sm"
            variant="outline"
            className="gap-2"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                AI Suggest Pricing
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>List Price (ExM)</Label>
            <Input
              type="number"
              value={listPrice}
              onChange={(e) => setListPrice(parseFloat(e.target.value) || 0)}
            />
          </div>
          <div>
            <Label>Mandatory Discount (%)</Label>
            <Input
              type="number"
              value={mandatoryDiscount}
              onChange={(e) => setMandatoryDiscount(parseFloat(e.target.value) || 0)}
            />
          </div>
          <div>
            <Label>Expected Rebates</Label>
            <Input
              type="number"
              value={rebates}
              onChange={(e) => setRebates(parseFloat(e.target.value) || 0)}
            />
          </div>
          <div>
            <Label>Clawbacks</Label>
            <Input
              type="number"
              value={clawbacks}
              onChange={(e) => setClawbacks(parseFloat(e.target.value) || 0)}
            />
          </div>
          <div>
            <Label>Program Adjustments</Label>
            <Input
              type="number"
              value={programAdjustments}
              onChange={(e) => setProgramAdjustments(parseFloat(e.target.value) || 0)}
            />
          </div>
        </div>
        <Button onClick={calculateWaterfall} disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Calculating...
            </>
          ) : (
            'Calculate'
          )}
        </Button>

        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                angle={-45}
                textAnchor="end"
                height={80}
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip 
                formatter={(value: number) => `$${value.toLocaleString()}`}
                labelStyle={{ fontWeight: 'bold' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.type === 'positive' ? '#10b981' : '#ef4444'} 
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-gray-500 text-xs">List Price</div>
            <div className="font-semibold text-lg">${(waterfall.list_price || 0).toLocaleString()}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs">Net Price</div>
            <div className="font-semibold text-lg text-green-600">${(waterfall.net_price || 0).toLocaleString()}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs">GTN %</div>
            <div className="font-semibold text-lg">
              {waterfall.gtn_percent !== undefined 
                ? `${waterfall.gtn_percent.toFixed(1)}%`
                : waterfall.list_price && waterfall.net_price
                  ? `${(((waterfall.list_price - waterfall.net_price) / waterfall.list_price * 100)).toFixed(1)}%`
                  : '0.0%'
              }
            </div>
          </div>
          <div>
            <div className="text-gray-500 text-xs">GTN Amount</div>
            <div className="font-semibold text-lg text-red-600">${((waterfall.list_price || 0) - (waterfall.net_price || 0)).toLocaleString()}</div>
          </div>
        </div>
        
        {/* Component Breakdown */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs border-t pt-4">
          <div>
            <div className="text-gray-500">Mandatory Discount</div>
            <div className="font-medium">
              {typeof waterfall.mandatory_discount === 'object' && waterfall.mandatory_discount
                ? `${waterfall.mandatory_discount.percent?.toFixed(1) || 0}% ($${Math.abs(waterfall.mandatory_discount.value || 0).toLocaleString()})`
                : `$${Math.abs(waterfall.mandatory_discount || 0).toLocaleString()}`
              }
            </div>
          </div>
          <div>
            <div className="text-gray-500">Expected Rebates</div>
            <div className="font-medium">${Math.abs(waterfall.expected_rebates || 0).toLocaleString()}</div>
          </div>
          <div>
            <div className="text-gray-500">Clawbacks</div>
            <div className="font-medium">${Math.abs(waterfall.clawbacks || 0).toLocaleString()}</div>
          </div>
          <div>
            <div className="text-gray-500">Program Adjustments</div>
            <div className="font-medium">${Math.abs(waterfall.program_adjustments || 0).toLocaleString()}</div>
          </div>
        </div>

        {/* Transparency Section - Always show if there's any data */}
        {(waterfall.data_sources_used?.length > 0 || (waterfall.gtn_breakdown && Object.keys(waterfall.gtn_breakdown).length > 0)) && (
          <Collapsible open={showDetails} onOpenChange={setShowDetails}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between">
                <span className="flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Calculation Details & Data Sources
                </span>
                {showDetails ? '−' : '+'}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-4 pt-4 border-t overflow-hidden">
              <div className="space-y-4">
              {waterfall.data_sources_used && waterfall.data_sources_used.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-sm">Data Sources Used:</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {waterfall.data_sources_used.map((source: string, idx: number) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {source}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {waterfall.gtn_breakdown && Object.keys(waterfall.gtn_breakdown).length > 0 ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingDown className="h-4 w-4 text-orange-600" />
                    <span className="font-medium text-sm">GTN Breakdown:</span>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3 text-sm border border-gray-200">
                    {waterfall.gtn_breakdown.coverage_distribution && (
                      <div className="pb-2 border-b border-gray-200">
                        <span className="font-semibold text-gray-700">Coverage Distribution: </span>
                        <div className="mt-1 text-gray-600 space-y-1">
                          {Object.entries(waterfall.gtn_breakdown.coverage_distribution).map(([level, data]: [string, any]) => {
                            const pct = data.percentage * 100
                            const restrictions = data.restrictions || {}
                            return (
                              <div key={level} className="ml-2">
                                <div className="font-medium">{level}: {pct.toFixed(1)}%</div>
                                {level === "Restricted" && Object.keys(restrictions).length > 0 && (
                                  <div className="ml-4 text-xs">
                                    Restrictions: {Object.entries(restrictions)
                                      .filter(([_, val]: [string, any]) => val > 0)
                                      .map(([restriction, val]: [string, any]) => 
                                        `${restriction}: ${(val * 100).toFixed(1)}%`
                                      ).join(", ") || "None"}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                    {waterfall.gtn_breakdown.tier_distribution && !waterfall.gtn_breakdown.coverage_distribution && (
                      <div className="pb-2 border-b border-gray-200">
                        <span className="font-semibold text-gray-700">Tier Distribution: </span>
                        <div className="mt-1 text-gray-600">
                          {typeof waterfall.gtn_breakdown.tier_distribution === 'object' 
                            ? Object.entries(waterfall.gtn_breakdown.tier_distribution).map(([tier, pct]: [string, any]) => (
                                <div key={tier} className="ml-2">
                                  {tier}: {(pct * 100).toFixed(1)}%
                                </div>
                              ))
                            : JSON.stringify(waterfall.gtn_breakdown.tier_distribution)
                          }
                        </div>
                      </div>
                    )}
                    {waterfall.gtn_breakdown.rebate_calculation && (
                      <div className="pb-2 border-b border-gray-200">
                        <span className="font-semibold text-gray-700">Rebate Calculation (Top-Down): </span>
                        <div className="mt-1 text-gray-600 space-y-1 text-xs">
                          {waterfall.gtn_breakdown.rebate_calculation.channel_breakdown && 
                            Object.entries(waterfall.gtn_breakdown.rebate_calculation.channel_breakdown).map(([channel, data]: [string, any]) => (
                              <div key={channel} className="ml-2">
                                {channel}: {data.effective_rebate_rate?.toFixed(1)}% (Mix: {data.mix_percentage?.toFixed(1)}%)
                              </div>
                            ))
                          }
                          <div className="ml-2 font-medium mt-1">
                            Total Effective Rebate: {waterfall.gtn_breakdown.rebate_calculation.effective_rebate_pct?.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    )}
                    {waterfall.gtn_breakdown.full_gtn?.components && (
                      <div className="pb-2 border-b border-gray-200">
                        <span className="font-semibold text-gray-700">Full GTN Components: </span>
                        <div className="mt-1 text-gray-600 space-y-1 text-xs">
                          {Object.entries(waterfall.gtn_breakdown.full_gtn.components).map(([component, data]: [string, any]) => (
                            <div key={component} className="ml-2">
                              {component.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}: 
                              ${data.amount?.toLocaleString()} ({data.percent?.toFixed(2)}%)
                            </div>
                          ))}
                          <div className="ml-2 font-medium mt-1">
                            Total GTN: ${waterfall.gtn_breakdown.full_gtn.total_gtn?.toLocaleString()} 
                            ({waterfall.gtn_breakdown.full_gtn.gtn_percent?.toFixed(1)}%)
                          </div>
                        </div>
                      </div>
                    )}
                    {waterfall.gtn_breakdown.weighted_rebate_pct !== undefined && (
                      <div className="pb-2 border-b border-gray-200">
                        <span className="font-semibold text-gray-700">Weighted Rebate %: </span>
                        <span className="text-gray-600">{waterfall.gtn_breakdown.weighted_rebate_pct.toFixed(2)}%</span>
                      </div>
                    )}
                    {waterfall.gtn_breakdown.comparator_adjustment !== undefined && (
                      <div>
                        <span className="font-semibold text-gray-700">Comparator Adjustment: </span>
                        <span className="text-gray-600">${waterfall.gtn_breakdown.comparator_adjustment.toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic">
                  No GTN breakdown data available. GTN was calculated using manual inputs.
                </div>
              )}

              <div className="text-xs text-gray-600 space-y-1">
                <div><strong>Calculation Method:</strong></div>
                <div>Net Price = List Price × (1 - Mandatory Discount%) - Expected Rebates - Clawbacks - Program Adjustments</div>
                <div>GTN % = (List Price - Net Price) / List Price × 100</div>
                {waterfall.data_sources_used?.length > 0 && (
                  <div className="mt-2 text-green-700">
                    ✓ Using data-driven GTN calculations from real formulary, payer, and comparator data
                  </div>
                )}
                {(!waterfall.data_sources_used || waterfall.data_sources_used.length === 0) && (
                  <div className="mt-2 text-orange-700">
                    ⚠ Using manual/default inputs. Enable data sources for data-driven calculations.
                  </div>
                )}
              </div>
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
        
        {/* Always show GTN breakdown if available, even if collapsible is closed */}
        {waterfall.gtn_breakdown && Object.keys(waterfall.gtn_breakdown).length > 0 && !showDetails && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="h-4 w-4 text-blue-600" />
              <span className="font-medium text-sm text-blue-900">GTN Breakdown Available</span>
            </div>
            <p className="text-xs text-blue-700 mb-2">
              Click "Calculation Details & Data Sources" above to view detailed GTN breakdown including tier distribution, rebate percentages, and comparator adjustments.
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setShowDetails(true)}
              className="text-xs"
            >
              Show GTN Breakdown
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

