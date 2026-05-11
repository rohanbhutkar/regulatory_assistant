"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Sparkles, Loader2, Download, FileSpreadsheet, ChevronDown, ChevronUp, Info } from 'lucide-react'
import { toast } from 'sonner'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'
import { InlineActivityIndicator } from '@/components/activity/inline-activity-indicator'
import { ExportManager } from './export-manager'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { useAssetStrategy } from '@/lib/contexts/asset-strategy-context'

interface FinancialValueTabProps {
  assetId: string
  market: string
  asset?: {
    asset_name?: string
    indication?: string
    therapeutic_area?: string
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export function FinancialValueTab({ assetId, market, asset }: FinancialValueTabProps) {
  const [financialData, setFinancialData] = useState<any>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [prevalenceDetailsOpen, setPrevalenceDetailsOpen] = useState(false)
  const { getTabContent } = useAssetStrategy()

  const calculateFinancialMetrics = async () => {
    setIsCalculating(true)
    try {
      // Get price prediction first
      const priceResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/pricing/${assetId}/${market}?include_uncertainty=true`)
      let netPrice = null
      let listPrice = null
      let gtnBreakdown = null
      
      if (priceResponse.ok) {
        const priceData = await priceResponse.json()
        netPrice = priceData.net_price
        listPrice = priceData.list_price
        gtnBreakdown = priceData.waterfall_components?.gtn_breakdown || priceData.gtn_breakdown
      }
      
      // Also try to get from saved pricing tab content
      if (!gtnBreakdown) {
        const pricingTabContent = getTabContent('pricing')
        if (pricingTabContent?.priceData?.waterfall_components?.gtn_breakdown) {
          gtnBreakdown = pricingTabContent.priceData.waterfall_components.gtn_breakdown
        }
      }
      
      // Auto-calculate all financial metrics with integration data
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/financial/auto-calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          market: market,
          indication: asset?.indication || asset?.therapeutic_area,
          list_price: listPrice,
          net_price: netPrice,
          launch_date: asset?.expected_launch_dates?.[market],
          expected_launch_dates: asset?.expected_launch_dates,
          key_milestone_dates: asset?.key_milestone_dates,
          asset_data: {
            asset_name: asset?.asset_name,
            drug_name: asset?.asset_name,
            indication: asset?.indication || asset?.therapeutic_area,
            therapeutic_area: asset?.therapeutic_area
          },
          comparators: asset?.comparators || [],
          hta_outcome: asset?.hta_outcome,
          gtn_breakdown: gtnBreakdown
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setFinancialData(data)
        setRefreshKey(prev => prev + 1)
        toast.success('Financial metrics calculated successfully')
      } else {
        toast.error('Failed to calculate financial metrics')
      }
    } catch (error) {
      console.error('Failed to calculate financial metrics:', error)
      toast.error('Failed to calculate financial metrics')
    } finally {
      setIsCalculating(false)
    }
  }

  // Auto-calculate when component mounts if we have indication
  useEffect(() => {
    if (asset?.indication || asset?.therapeutic_area) {
      calculateFinancialMetrics()
    }
  }, [assetId, market])

  const patientFunnel = financialData?.patient_funnel
  const revenue = financialData?.revenue
  const npv = financialData?.npv
  const roi = financialData?.roi
  const roiCurves = financialData?.roi_curves

  const exportFinancialData = (format: 'json' | 'csv') => {
    if (!financialData) {
      toast.error('No financial data to export')
      return
    }
    
    if (format === 'json') {
      const dataStr = JSON.stringify(financialData, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `financial-data-${assetId}-${new Date().toISOString().split('T')[0]}.json`
      link.click()
      URL.revokeObjectURL(url)
      toast.success('Financial data exported as JSON')
    } else if (format === 'csv') {
      // Simple CSV export
      const csvRows = []
      csvRows.push('Metric,Value')
      if (patientFunnel) {
        csvRows.push(`Prevalence,${patientFunnel.prevalence || ''}`)
        csvRows.push(`Diagnosed,${patientFunnel.diagnosed || ''}`)
        csvRows.push(`Eligible,${patientFunnel.eligible || ''}`)
        csvRows.push(`Accessible,${patientFunnel.accessible || ''}`)
        csvRows.push(`Treated,${patientFunnel.treated || ''}`)
      }
      if (revenue) {
        csvRows.push(`Peak Sales,${revenue.peak_sales || ''}`)
        csvRows.push(`Time to Peak,${revenue.time_to_peak_years || ''}`)
      }
      if (npv) {
        csvRows.push(`NPV,${npv.npv || ''}`)
        csvRows.push(`rNPV,${npv.rnpv || ''}`)
      }
      if (roi) {
        csvRows.push(`ROI,${roi.roi || ''}`)
      }
      
      const csvContent = csvRows.join('\n')
      const dataBlob = new Blob([csvContent], { type: 'text/csv' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `financial-data-${assetId}-${new Date().toISOString().split('T')[0]}.csv`
      link.click()
      URL.revokeObjectURL(url)
      toast.success('Financial data exported as CSV')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">Financial Value & ROI Analysis</h3>
          <p className="text-sm text-muted-foreground">Patient funnel, revenue projections, NPV, and ROI curves</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={calculateFinancialMetrics}
            disabled={isCalculating}
            className="gap-2 bg-primary hover:bg-primary/90"
          >
            {isCalculating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Calculating...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Calculate Metrics
              </>
            )}
          </Button>
          {financialData && (
            <>
              <Button
                onClick={() => exportFinancialData('json')}
                variant="outline"
                className="gap-2"
                disabled={isCalculating}
              >
                <Download className="h-4 w-4" />
                Export JSON
              </Button>
              <Button
                onClick={() => exportFinancialData('csv')}
                variant="outline"
                className="gap-2"
                disabled={isCalculating}
              >
                <FileSpreadsheet className="h-4 w-4" />
                Export CSV
              </Button>
            </>
          )}
        </div>
      </div>

      <InlineActivityIndicator
        operationType="financial_calc"
        context={{ assetId, tab: 'financial' }}
      />

      {/* Patient Funnel */}
      {patientFunnel && (
        <Card key={`patient-funnel-${refreshKey}`}>
          <CardHeader>
            <CardTitle>Patient Funnel</CardTitle>
            <CardDescription>
              {patientFunnel.prevalence_source === 'claims_data' 
                ? 'Calculated from claims data' 
                : 'Manual calculation'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Prevalence</p>
                  <p className="text-2xl font-bold">
                    {patientFunnel.prevalence ? (patientFunnel.prevalence * 100).toFixed(2) : 'N/A'}%
                  </p>
                  {patientFunnel.prevalence_calculation_details && (
                    <Collapsible open={prevalenceDetailsOpen} onOpenChange={setPrevalenceDetailsOpen} className="mt-2">
                      <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                        <Info className="h-3 w-3" />
                        <span>Calculation details</span>
                        {prevalenceDetailsOpen ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 space-y-2 text-xs">
                        <div className="bg-muted p-3 rounded-lg space-y-2">
                          <div>
                            <p className="font-semibold">Data Source:</p>
                            <p className="text-muted-foreground">{patientFunnel.prevalence_calculation_details.data_source}</p>
                          </div>
                          <div>
                            <p className="font-semibold">Search Method:</p>
                            <p className="text-muted-foreground">{patientFunnel.prevalence_calculation_details.search_method}</p>
                          </div>
                          <div>
                            <p className="font-semibold">Indication Searched:</p>
                            <p className="text-muted-foreground">{patientFunnel.prevalence_calculation_details.indication_searched}</p>
                          </div>
                          {patientFunnel.prevalence_calculation_details.diagnosis_columns_searched && (
                            <div>
                              <p className="font-semibold">Diagnosis Columns Searched:</p>
                              <p className="text-muted-foreground">
                                {patientFunnel.prevalence_calculation_details.diagnosis_columns_searched.join(', ')}
                              </p>
                            </div>
                          )}
                          {patientFunnel.prevalence_calculation_details.matched_icd_codes && 
                           patientFunnel.prevalence_calculation_details.matched_icd_codes.length > 0 && (
                            <div>
                              <p className="font-semibold">
                                Matched ICD Codes ({patientFunnel.prevalence_calculation_details.total_matched_icd_codes} total):
                              </p>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {patientFunnel.prevalence_calculation_details.matched_icd_codes.slice(0, 20).map((code: string, idx: number) => (
                                  <span key={idx} className="bg-background px-2 py-1 rounded text-xs">
                                    {code}
                                  </span>
                                ))}
                                {patientFunnel.prevalence_calculation_details.matched_icd_codes.length > 20 && (
                                  <span className="text-muted-foreground text-xs">
                                    +{patientFunnel.prevalence_calculation_details.matched_icd_codes.length - 20} more
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                          {patientFunnel.prevalence_calculation_details.calculation_steps && (
                            <div>
                              <p className="font-semibold">Calculation Steps:</p>
                              <ol className="list-decimal list-inside space-y-1 mt-1 text-muted-foreground">
                                {patientFunnel.prevalence_calculation_details.calculation_steps.map((step: string, idx: number) => (
                                  <li key={idx}>{step}</li>
                                ))}
                              </ol>
                            </div>
                          )}
                          {patientFunnel.prevalence_calculation_details.sample_statistics && (
                            <div>
                              <p className="font-semibold">Sample Statistics:</p>
                              <ul className="list-disc list-inside space-y-1 mt-1 text-muted-foreground">
                                <li>Total Claims in Sample: {patientFunnel.prevalence_calculation_details.sample_statistics.total_claims_in_sample?.toLocaleString()}</li>
                                <li>Unique Patients in Sample: {patientFunnel.prevalence_calculation_details.sample_statistics.unique_patients_in_sample?.toLocaleString()}</li>
                                <li>Estimated US Patients: {patientFunnel.prevalence_calculation_details.sample_statistics.estimated_us_patients?.toLocaleString()}</li>
                                <li>Sample Rate: {(patientFunnel.prevalence_calculation_details.claims_sample_rate * 100).toFixed(0)}%</li>
                                <li>US Total Population: {patientFunnel.prevalence_calculation_details.us_total_population?.toLocaleString()}</li>
                              </ul>
                            </div>
                          )}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Diagnosed</p>
                  <p className="text-2xl font-bold">
                    {patientFunnel.diagnosed ? patientFunnel.diagnosed.toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Eligible</p>
                  <p className="text-2xl font-bold">
                    {patientFunnel.eligible ? patientFunnel.eligible.toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Accessible</p>
                  <p className="text-2xl font-bold">
                    {patientFunnel.accessible ? patientFunnel.accessible.toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Treated</p>
                  <p className="text-2xl font-bold">
                    {patientFunnel.treated ? patientFunnel.treated.toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Market Share</p>
                  <p className="text-2xl font-bold">
                    {patientFunnel.units ? patientFunnel.units.toLocaleString() : 'N/A'}
                  </p>
                </div>
              </div>
              
              {patientFunnel.funnel_stages && (
                <div className="mt-6">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={patientFunnel.funnel_stages}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="stage" />
                      <YAxis />
                      <Tooltip formatter={(value: any) => value.toLocaleString()} />
                      <Bar dataKey="count" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Revenue Projection */}
      {revenue && (
        <Card key={`revenue-${refreshKey}`}>
          <CardHeader>
            <CardTitle>Revenue Projection</CardTitle>
            <CardDescription>
              Peak Sales: ${revenue.peak_sales?.toLocaleString() || 0} | 
              Time to Peak: {revenue.time_to_peak_years || 0} years
            </CardDescription>
          </CardHeader>
          <CardContent>
            {revenue.revenue_trajectory && (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={revenue.revenue_trajectory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="year" 
                    label={{ value: 'Year', position: 'insideBottom', offset: -5 }}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis 
                    label={{ value: 'Revenue ($)', angle: -90, position: 'insideLeft' }}
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
                  />
                  <Tooltip 
                    formatter={(value: any) => `$${value.toLocaleString()}`}
                    labelFormatter={(label) => `Year: ${label}`}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#8884d8" 
                    name="Revenue" 
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* NPV and ROI Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {npv && (
          <Card key={`npv-${refreshKey}`}>
            <CardHeader>
              <CardTitle>NPV / rNPV</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">NPV</p>
                  <p className="text-3xl font-bold">
                    ${npv.npv ? npv.npv.toLocaleString() : '0'}
                  </p>
                </div>
                {npv.rnpv !== null && (
                  <div>
                    <p className="text-sm text-muted-foreground">rNPV (60% PoS)</p>
                    <p className="text-3xl font-bold">
                      ${npv.rnpv ? npv.rnpv.toLocaleString() : '0'}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-muted-foreground">Discount Rate</p>
                  <p className="text-lg">{(npv.discount_rate * 100).toFixed(1)}%</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {roi && (
          <Card key={`roi-${refreshKey}`}>
            <CardHeader>
              <CardTitle>ROI</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">ROI</p>
                  <p className="text-3xl font-bold">
                    {(roi.roi * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Investment</p>
                  <p className="text-lg">${roi.total_investment?.toLocaleString() || '0'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Benefits</p>
                  <p className="text-lg">${roi.total_benefits?.toLocaleString() || '0'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ROI Curves */}
      {roiCurves && roiCurves.scenarios && (
        <Card key={`roi-curves-${refreshKey}`}>
          <CardHeader>
            <CardTitle>ROI Curves - Multiple Scenarios</CardTitle>
            <CardDescription>Base, Optimistic, and Pessimistic scenarios</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="year" 
                  label={{ value: 'Year', position: 'insideBottom', offset: -5 }}
                  tick={{ fontSize: 12 }}
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  scale="linear"
                />
                <YAxis 
                  label={{ value: 'ROI (%)', angle: -90, position: 'insideLeft' }}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                />
                <Tooltip 
                  formatter={(value: any) => `${(value * 100).toFixed(1)}%`}
                  labelFormatter={(label) => `Year: ${label}`}
                />
                <Legend />
                {roiCurves.scenarios.base?.roi_curve && (
                  <Line 
                    type="monotone" 
                    data={roiCurves.scenarios.base.roi_curve}
                    dataKey="roi" 
                    stroke="#8884d8" 
                    name="Base Scenario"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                )}
                {roiCurves.scenarios.optimistic?.roi_curve && (
                  <Line 
                    type="monotone" 
                    data={roiCurves.scenarios.optimistic.roi_curve}
                    dataKey="roi" 
                    stroke="#82ca9d" 
                    name="Optimistic"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                )}
                {roiCurves.scenarios.pessimistic?.roi_curve && (
                  <Line 
                    type="monotone" 
                    data={roiCurves.scenarios.pessimistic.roi_curve}
                    dataKey="roi" 
                    stroke="#ffc658" 
                    name="Pessimistic"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {!financialData && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>Click "Calculate Metrics" to generate financial analysis</p>
            <p className="text-sm mt-2">Requires pricing data and indication</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
