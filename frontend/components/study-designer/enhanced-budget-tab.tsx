/**
 * Enhanced Budget Tab
 * Comprehensive budget visualization with detailed breakdowns
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  DollarSign, 
  Users, 
  Building2, 
  TrendingUp, 
  FileText, 
  Download,
  Calculator,
  CheckCircle,
  Loader2,
  Globe,
  Pill,
  Briefcase
} from 'lucide-react'
import { useStudyDesigner } from '@/lib/contexts/study-designer-context'
import { toast } from 'sonner'

interface BudgetResponse {
  success: boolean
  budget: {
    grand_total: number
    currency: string
    patient_costs: {
      cpp_base: number
      total_patients: number
      total: number
      breakdown: {
        per_patient_procedures: number
        per_patient_visits: number
        per_patient_drug_cost: number
        travel_stipend: number
      }
    }
    site_costs: {
      total: number
      breakdown: {
        initiation: number
        closeout: number
        monitoring: number
        training: number
        regulatory: number
      }
    }
    operational_costs: {
      total: number
      breakdown: {
        irb_fees: number
        drug_packaging: number
        lab_services: number
        data_management: number
        other: number
      }
    }
    drug_costs: {
      total: number
      breakdown: {
        active_drug: number
        placebo: number
        packaging: number
        shipping: number
      }
    }
    overhead: {
      total: number
      percentage: number
      breakdown: {
        indirect_costs: number
        administrative: number
        management_fee: number
      }
    }
    contingency: {
      total: number
      percentage: number
    }
    breakdown_by_phase: Array<{
      phase: string
      months: number
      cost: number
      percentage: number
    }>
    timeline: {
      total_months: number
      phases: Array<{
        name: string
        months: number
        start_month: number
        end_month: number
      }>
    }
  }
}

export function EnhancedBudgetTab() {
  const {
    studyContext,
    selectedSites,
    studyDesign,
    simulationResult,
    protocolSections
  } = useStudyDesigner()

  const [budgetData, setBudgetData] = useState<BudgetResponse | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const totalPatients = studyContext.totalParticipants || studyDesign?.totalParticipants || 300
  const totalSites = selectedSites.length || 100
  const durationMonths = simulationResult?.expected_duration_months || studyContext.duration_months || 24

  // Parse SoA data from protocolSections
  const getSoAData = () => {
    try {
      if (protocolSections?.soa) {
        const parsed = JSON.parse(protocolSections.soa)
        console.log('✅ Parsed SoA data for budget:', { visits: parsed.visits?.length, activities: parsed.activities?.length })
        return parsed
      }
    } catch (e) {
      console.error('Error parsing SoA data:', e)
    }
    return {}
  }

  const handleCalculate = async () => {
    setIsCalculating(true)
    setError(null)

    try {
      const response = await fetch('http://localhost:8001/api/analysis/budget/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          study_context: {
            indication: studyContext.indication || 'Unknown',
            phase: studyContext.phase || 'Phase III',
            therapeutic_area: studyContext.therapeuticArea || 'General'
          },
          reference_trials: studyContext.referenceTrials || [],
          study_design: {
            totalParticipants: totalPatients,
            duration_months: durationMonths,
            arms: studyDesign?.arms || []
          },
          ie_criteria: studyContext.ieCriteria || {},
          endpoints: studyContext.endpoints || [],
          soa_data: getSoAData(),
          selected_sites: selectedSites.map(site => ({
            name: site.name,
            country: site.country || site.country_code || 'USA',
            patients: Math.round(totalPatients / totalSites)
          })),
          simulation_results: simulationResult || {
            expected_duration_months: durationMonths,
            enrollment_curve: []
          }
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setBudgetData(data)
      toast.success('Budget calculated successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate budget')
      console.error('Error calculating budget:', err)
      toast.error('Failed to calculate budget')
    } finally {
      setIsCalculating(false)
    }
  }

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '$0.00'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return '0'
    return new Intl.NumberFormat('en-US').format(num)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <DollarSign className="h-6 w-6 text-green-600" />
                Comprehensive Study Budget
              </CardTitle>
              <CardDescription className="mt-2">
                {studyContext.indication} • {studyContext.phase} • {totalPatients} Patients • {totalSites} Sites
              </CardDescription>
              <div className="flex items-center gap-2 mt-2">
                {protocolSections?.soa ? (
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                    <CheckCircle className="mr-1 h-3 w-3" />
                    SoA Data Available
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                    Using Default CPP
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={!budgetData}>
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <Button 
                onClick={handleCalculate}
                disabled={isCalculating}
                size="sm"
              >
                {isCalculating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Calculator className="mr-2 h-4 w-4" />
                    Calculate Budget
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-800">{error}</p>
          </CardContent>
        </Card>
      )}

      {!budgetData && !isCalculating && (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <Calculator className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>Click "Calculate Budget" to generate comprehensive budget breakdown</p>
          </CardContent>
        </Card>
      )}

      {budgetData && budgetData.success && (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Patients</p>
                    <p className="text-2xl font-bold">{formatNumber(totalPatients)}</p>
                  </div>
                  <Users className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Sites</p>
                    <p className="text-2xl font-bold">{formatNumber(totalSites)}</p>
                  </div>
                  <Building2 className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">CPP (Base)</p>
                    <p className="text-2xl font-bold">
                      {formatCurrency(budgetData.budget.patient_costs.cpp_base)}
                    </p>
                  </div>
                  <DollarSign className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-2 border-green-500">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Grand Total</p>
                    <p className="text-2xl font-bold text-green-600">
                      {formatCurrency(budgetData.budget.grand_total)}
                    </p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Section 1: Patient Costs */}
          <Card>
            <CardHeader className="bg-blue-50">
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-600" />
                Patient Costs
              </CardTitle>
              <CardDescription>
                Direct costs per patient across all study activities
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-gray-700">Per Patient Procedures</span>
                  <span className="font-semibold">
                    {formatCurrency(budgetData.budget.patient_costs.breakdown.per_patient_procedures)}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-gray-700">Per Patient Visits</span>
                  <span className="font-semibold">
                    {formatCurrency(budgetData.budget.patient_costs.breakdown.per_patient_visits)}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-gray-700">Per Patient Drug Cost</span>
                  <span className="font-semibold">
                    {formatCurrency(budgetData.budget.patient_costs.breakdown.per_patient_drug_cost)}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-gray-700">Travel Stipend</span>
                  <span className="font-semibold">
                    {formatCurrency(budgetData.budget.patient_costs.breakdown.travel_stipend)}
                  </span>
                </div>
                
                <Separator className="my-4" />
                
                <div className="flex justify-between items-center text-lg font-bold bg-blue-100 p-3 rounded">
                  <span>Base CPP (per patient)</span>
                  <span>{formatCurrency(budgetData.budget.patient_costs.cpp_base)}</span>
                </div>
                
                <div className="flex justify-between items-center text-gray-600 px-3">
                  <span>× {formatNumber(totalPatients)} patients</span>
                  <span></span>
                </div>
                
                <div className="flex justify-between items-center text-xl font-bold bg-blue-200 p-4 rounded">
                  <span>Total Patient Costs</span>
                  <span>{formatCurrency(budgetData.budget.patient_costs.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Site Costs */}
          <Card>
            <CardHeader className="bg-purple-50">
              <CardTitle className="text-lg flex items-center gap-2">
                <Building2 className="h-5 w-5 text-purple-600" />
                Site Costs
              </CardTitle>
              <CardDescription>
                Site initiation, management, and closeout costs
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {Object.entries(budgetData.budget.site_costs.breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                    <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-semibold">{formatCurrency(value)}</span>
                  </div>
                ))}
                
                <Separator className="my-4" />
                
                <div className="flex justify-between items-center text-lg font-bold bg-purple-100 p-3 rounded">
                  <span>Total Site Costs</span>
                  <span>{formatCurrency(budgetData.budget.site_costs.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 3: Operational Costs */}
          <Card>
            <CardHeader className="bg-indigo-50">
              <CardTitle className="text-lg flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-indigo-600" />
                Operational Costs
              </CardTitle>
              <CardDescription>
                Study-level operational and administrative costs
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {Object.entries(budgetData.budget.operational_costs.breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                    <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-semibold">{formatCurrency(value)}</span>
                  </div>
                ))}
                
                <Separator className="my-4" />
                
                <div className="flex justify-between items-center text-lg font-bold bg-indigo-100 p-3 rounded">
                  <span>Total Operational Costs</span>
                  <span>{formatCurrency(budgetData.budget.operational_costs.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 4: Drug Costs */}
          {budgetData.budget.drug_costs && budgetData.budget.drug_costs.total > 0 && (
            <Card>
              <CardHeader className="bg-orange-50">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Pill className="h-5 w-5 text-orange-600" />
                  Drug Costs
                </CardTitle>
                <CardDescription>
                  Active drug, placebo, packaging, and distribution
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  {Object.entries(budgetData.budget.drug_costs.breakdown).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                      <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="font-semibold">{formatCurrency(value)}</span>
                    </div>
                  ))}
                  
                  <Separator className="my-4" />
                  
                  <div className="flex justify-between items-center text-lg font-bold bg-orange-100 p-3 rounded">
                    <span>Total Drug Costs</span>
                    <span>{formatCurrency(budgetData.budget.drug_costs.total)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Section 5: Overhead */}
          <Card>
            <CardHeader className="bg-amber-50">
              <CardTitle className="text-lg flex items-center gap-2">
                <Globe className="h-5 w-5 text-amber-600" />
                Overhead
              </CardTitle>
              <CardDescription>
                {(budgetData.budget.overhead.percentage * 100).toFixed(0)}% overhead on direct costs
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {Object.entries(budgetData.budget.overhead.breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                    <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-semibold">{formatCurrency(value)}</span>
                  </div>
                ))}
                
                <Separator className="my-4" />
                
                <div className="flex justify-between items-center text-lg font-bold bg-amber-100 p-3 rounded">
                  <span>Total Overhead</span>
                  <span>{formatCurrency(budgetData.budget.overhead.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 6: Contingency */}
          {budgetData.budget.contingency && budgetData.budget.contingency.total > 0 && (
            <Card>
              <CardHeader className="bg-yellow-50">
                <CardTitle className="text-lg">Contingency</CardTitle>
                <CardDescription>
                  {(budgetData.budget.contingency.percentage * 100).toFixed(0)}% contingency reserve
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="flex justify-between items-center text-lg font-bold bg-yellow-100 p-3 rounded">
                  <span>Total Contingency</span>
                  <span>{formatCurrency(budgetData.budget.contingency.total)}</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Section 7: Grand Total */}
          <Card className="border-4 border-green-500">
            <CardHeader className="bg-green-100">
              <CardTitle className="text-2xl flex items-center gap-2">
                <TrendingUp className="h-6 w-6 text-green-600" />
                Grand Total Study Budget
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div className="flex justify-between items-center text-gray-700">
                  <span className="text-lg">Patient Costs</span>
                  <span className="text-lg font-semibold">
                    {formatCurrency(budgetData.budget.patient_costs.total)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-gray-700">
                  <span className="text-lg">Site Costs</span>
                  <span className="text-lg font-semibold">
                    {formatCurrency(budgetData.budget.site_costs.total)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-gray-700">
                  <span className="text-lg">Operational Costs</span>
                  <span className="text-lg font-semibold">
                    {formatCurrency(budgetData.budget.operational_costs.total)}
                  </span>
                </div>
                {budgetData.budget.drug_costs && budgetData.budget.drug_costs.total > 0 && (
                  <div className="flex justify-between items-center text-gray-700">
                    <span className="text-lg">Drug Costs</span>
                    <span className="text-lg font-semibold">
                      {formatCurrency(budgetData.budget.drug_costs.total)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between items-center text-gray-700">
                  <span className="text-lg">Overhead</span>
                  <span className="text-lg font-semibold">
                    {formatCurrency(budgetData.budget.overhead.total)}
                  </span>
                </div>
                
                <Separator className="my-4" />
                
                <div className="text-center py-6 bg-green-50 rounded-lg">
                  <p className="text-lg text-gray-600 mb-2">Grand Total (USD)</p>
                  <p className="text-5xl font-bold text-green-600">
                    {formatCurrency(budgetData.budget.grand_total)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 8: Timeline & Phase Breakdown */}
          {budgetData.budget.breakdown_by_phase && budgetData.budget.breakdown_by_phase.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Cost by Study Phase</CardTitle>
                <CardDescription>
                  {budgetData.budget.timeline?.total_months || durationMonths} months total duration
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {budgetData.budget.breakdown_by_phase.map((phase, idx) => (
                    <div key={idx} className="p-3 border rounded-lg">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="font-semibold">{phase.phase}</div>
                          <div className="text-sm text-gray-500">{phase.months} months</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">{formatCurrency(phase.cost)}</div>
                          <div className="text-sm text-gray-500">
                            {phase.percentage.toFixed(1)}% of total
                          </div>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${phase.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
