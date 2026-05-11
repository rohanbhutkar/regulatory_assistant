/**
 * Comprehensive Budget Tab with Detailed Views
 * Includes: Summary, Patient Costs, Procedure Mapping, OPAL, Site Costs, Timeline
 */

"use client"

import { useState, useEffect, useRef, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Check, ChevronsUpDown, Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'
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
  Briefcase,
  Activity,
  Calendar,
  AlertCircle,
  Check,
  X
} from 'lucide-react'
import { useStudyDesigner } from '@/lib/contexts/study-designer-context'
import { toast } from 'sonner'
import { EnhancedOverheadDisplay } from './enhanced-overhead-display'
import { BudgetExportManager } from './budget-export-manager'
import { CountryAllocationManager } from './country-allocation-manager'
import { ProcedureSelectorDropdown } from './procedure-selector-dropdown'

interface BudgetData {
  success: boolean
  budget: {
    grand_total: number
    currency: string
    patient_costs: {
      cpp_base: number
      total_patients: number
      total: number
      breakdown: any
    }
    site_costs: {
      total: number
      breakdown: any
    }
    operational_costs: {
      total: number
      breakdown: any
    }
    overhead: {
      total: number
      percentage: number
      breakdown: any
    }
    contingency: {
      total: number
      percentage: number
    }
    timeline?: {
      total_months: number
      monthly_cashflow: any[]
    }
  }
  procedure_mappings?: Array<{
    original_text: string
    mapped_code: string
    mapped_name: string
    confidence_score: number
    category: string
    alternatives: Array<{
      code: string
      name: string
      confidence_score: number
    }>
  }>
  opal_calculation?: {
    total_hours: number
    staff_breakdown: any
    complexity_modifiers: any
  }
  soa_line_costs?: Array<{
    visit: string
    procedure: string
    cost: number
    quantity: number
    total: number
  }>
}

export function ComprehensiveBudgetTab() {
  const {
    studyContext,
    selectedSites,
    studyDesign,
    simulationResult,
    protocolSections
  } = useStudyDesigner()

  const [budgetData, setBudgetData] = useState<BudgetData | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('summary')
  const isInitialMount = useRef(true)
  const [allProcedures, setAllProcedures] = useState<Array<{code: string, name: string, description?: string}>>([])
  const [loadingProcedures, setLoadingProcedures] = useState(false)

  const totalPatients = studyContext.totalParticipants || studyDesign?.totalParticipants || 300
  const totalSites = selectedSites.length || 100
  const durationMonths = simulationResult?.expected_duration_months || studyContext.duration_months || 24

  // Load all procedures on mount
  useEffect(() => {
    const loadProcedures = async () => {
      setLoadingProcedures(true)
      try {
        const response = await fetch('http://localhost:8001/api/cpp/procedures/all')
        const data = await response.json()
        if (data.success && data.procedures) {
          setAllProcedures(data.procedures)
          console.log(`✅ Loaded ${data.total} procedure codes`)
        }
      } catch (error) {
        console.error('Error loading procedures:', error)
      } finally {
        setLoadingProcedures(false)
      }
    }
    loadProcedures()
  }, [])

  // Track when procedure mappings change to notify user
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    
    if (budgetData?.procedure_mappings) {
      console.log('🔄 Procedure mappings updated')
      toast.info('Procedure updated. Click "Calculate Budget" to recalculate costs with the new procedure.')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [budgetData?.procedure_mappings])

  // Parse SoA data from protocolSections
  const getSoAData = () => {
    try {
      if (protocolSections?.soa) {
        const parsed = JSON.parse(protocolSections.soa)
        console.log('✅ Parsed SoA data for budget:', { 
          visits: parsed.visits?.length, 
          activities: parsed.activities?.length 
        })
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
      const soaData = getSoAData()
      console.log('🔍 Budget calculation request:', {
        has_soa: !!soaData.visits,
        soa_visits: soaData.visits?.length,
        soa_activities: soaData.activities?.length,
        total_patients: totalPatients,
        total_sites: totalSites
      })

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
          soa_data: soaData,
          procedure_mappings: budgetData?.procedure_mappings || null,  // Send user-selected mappings
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
        const errorText = await response.text()
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ Budget calculation response:', data)
      setBudgetData(data)
      toast.success('Budget calculated successfully')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to calculate budget'
      setError(errorMsg)
      console.error('Error calculating budget:', err)
      toast.error(errorMsg)
    } finally {
      setIsCalculating(false)
    }
  }

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null || isNaN(amount)) return '$0'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null || isNaN(num)) return '0'
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
                    <AlertCircle className="mr-1 h-3 w-3" />
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
                className="bg-green-600 hover:bg-green-700"
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
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <p className="font-semibold text-red-800">Error Calculating Budget</p>
                <p className="text-red-700 text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {!budgetData && !isCalculating && (
        <Card>
          <CardContent className="pt-12 pb-12 text-center text-muted-foreground">
            <Calculator className="h-16 w-16 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium mb-2">No Budget Calculated Yet</p>
            <p className="text-sm">Click "Calculate Budget" to generate comprehensive budget breakdown</p>
          </CardContent>
        </Card>
      )}

      {budgetData && budgetData.success && (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-12 gap-1 p-1">
            <TabsTrigger value="summary" className="text-xs">Summary</TabsTrigger>
            <TabsTrigger value="patient" className="text-xs">Patient</TabsTrigger>
            <TabsTrigger value="additional" className="text-xs">Additional</TabsTrigger>
            <TabsTrigger value="drug" className="text-xs">Drug Supply</TabsTrigger>
            <TabsTrigger value="procedures" className="text-xs">Procedures</TabsTrigger>
            <TabsTrigger value="opal" className="text-xs">OPAL</TabsTrigger>
            <TabsTrigger value="sites" className="text-xs">Sites</TabsTrigger>
            <TabsTrigger value="operational" className="text-xs">Operational</TabsTrigger>
            <TabsTrigger value="overhead" className="text-xs">Overhead</TabsTrigger>
            <TabsTrigger value="countries" className="text-xs">Countries</TabsTrigger>
            <TabsTrigger value="timeline" className="text-xs">Timeline</TabsTrigger>
            <TabsTrigger value="export" className="text-xs">Export</TabsTrigger>
          </TabsList>

          {/* SUMMARY TAB */}
          <TabsContent value="summary" className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Patient Costs</p>
                      <p className="text-2xl font-bold">
                        {formatCurrency(budgetData.budget.patient_costs.total)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatCurrency(budgetData.budget.patient_costs.cpp_base)} per patient
                      </p>
                    </div>
                    <Users className="h-8 w-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Site Costs</p>
                      <p className="text-2xl font-bold">
                        {formatCurrency(budgetData.budget.site_costs.total)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {totalSites} sites
                      </p>
                    </div>
                    <Building2 className="h-8 w-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Operational</p>
                      <p className="text-2xl font-bold">
                        {formatCurrency(budgetData.budget.operational_costs.total)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {durationMonths} months
                      </p>
                    </div>
                    <Briefcase className="h-8 w-8 text-orange-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Cost Breakdown Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Cost Breakdown</CardTitle>
                <CardDescription>Distribution of total budget across categories</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Patient Costs */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Patient Costs</span>
                      <span className="text-sm font-semibold">
                        {formatCurrency(budgetData.budget.patient_costs.total)}
                        <span className="text-gray-500 ml-2">
                          ({((budgetData.budget.patient_costs.total / budgetData.budget.grand_total) * 100).toFixed(1)}%)
                        </span>
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-blue-500 h-3 rounded-full" 
                        style={{ width: `${(budgetData.budget.patient_costs.total / budgetData.budget.grand_total) * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Site Costs */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Site Costs</span>
                      <span className="text-sm font-semibold">
                        {formatCurrency(budgetData.budget.site_costs.total)}
                        <span className="text-gray-500 ml-2">
                          ({((budgetData.budget.site_costs.total / budgetData.budget.grand_total) * 100).toFixed(1)}%)
                        </span>
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-purple-500 h-3 rounded-full" 
                        style={{ width: `${(budgetData.budget.site_costs.total / budgetData.budget.grand_total) * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Operational Costs */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Operational Costs</span>
                      <span className="text-sm font-semibold">
                        {formatCurrency(budgetData.budget.operational_costs.total)}
                        <span className="text-gray-500 ml-2">
                          ({((budgetData.budget.operational_costs.total / budgetData.budget.grand_total) * 100).toFixed(1)}%)
                        </span>
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-orange-500 h-3 rounded-full" 
                        style={{ width: `${(budgetData.budget.operational_costs.total / budgetData.budget.grand_total) * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Overhead */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Overhead</span>
                      <span className="text-sm font-semibold">
                        {formatCurrency(budgetData.budget.overhead.total)}
                        <span className="text-gray-500 ml-2">
                          ({(budgetData.budget.overhead.percentage * 100).toFixed(1)}%)
                        </span>
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-gray-500 h-3 rounded-full" 
                        style={{ width: `${(budgetData.budget.overhead.total / budgetData.budget.grand_total) * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Contingency */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Contingency</span>
                      <span className="text-sm font-semibold">
                        {formatCurrency(budgetData.budget.contingency.total)}
                        <span className="text-gray-500 ml-2">
                          ({(budgetData.budget.contingency.percentage * 100).toFixed(1)}%)
                        </span>
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-red-500 h-3 rounded-full" 
                        style={{ width: `${(budgetData.budget.contingency.total / budgetData.budget.grand_total) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* PATIENT COSTS TAB */}
          <TabsContent value="patient" className="space-y-4">
            <Card>
              <CardHeader className="bg-blue-50">
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-blue-600" />
                  Patient Costs Breakdown
                </CardTitle>
                <CardDescription>
                  Detailed per-patient costs across all study activities
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Total Patients</p>
                    <p className="text-3xl font-bold text-blue-600">
                      {formatNumber(budgetData.budget.patient_costs.total_patients)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Cost Per Patient (CPP)</p>
                    <p className="text-3xl font-bold text-green-600">
                      {formatCurrency(budgetData.budget.patient_costs.cpp_base)}
                    </p>
                  </div>
                </div>

                <Separator className="my-6" />

                <div className="space-y-3">
                  <h3 className="font-semibold text-lg mb-4">Per-Patient Cost Components</h3>
                  
                  {budgetData.budget.patient_costs.breakdown && Object.entries(budgetData.budget.patient_costs.breakdown).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-700 capitalize">
                        {key.replace(/_/g, ' ').replace('per patient ', '')}
                      </span>
                      <span className="font-semibold">{formatCurrency(value as number)}</span>
                    </div>
                  ))}
                  
                  <div className="flex justify-between items-center py-3 bg-blue-50 px-4 rounded-lg mt-4">
                    <span className="font-bold text-blue-900">Total Patient Costs</span>
                    <span className="font-bold text-2xl text-blue-600">
                      {formatCurrency(budgetData.budget.patient_costs.total)}
                    </span>
                  </div>
                </div>

                {/* SoA Line-Level Costs */}
                {budgetData.soa_line_costs && budgetData.soa_line_costs.length > 0 && (
                  <>
                    <Separator className="my-6" />
                    <h3 className="font-semibold text-lg mb-4">SoA Line-Level Costs</h3>
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Visit</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Procedure</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Unit Cost</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Quantity</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {budgetData.soa_line_costs.map((line, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm">{line.visit}</td>
                              <td className="px-4 py-3 text-sm">{line.procedure}</td>
                              <td className="px-4 py-3 text-sm text-right">{formatCurrency(line.cost)}</td>
                              <td className="px-4 py-3 text-sm text-right">{line.quantity}</td>
                              <td className="px-4 py-3 text-sm text-right font-semibold">{formatCurrency(line.total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* PROCEDURES TAB */}
          <TabsContent value="procedures" className="space-y-4">
            <Card>
              <CardHeader className="bg-purple-50">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-purple-600" />
                  Procedure Mappings
                </CardTitle>
                <CardDescription>
                  AI-powered fuzzy matching of SoA procedures to standard codes
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.procedure_mappings && budgetData.procedure_mappings.length > 0 ? (
                  <div className="space-y-4">
                    {budgetData.procedure_mappings.map((mapping, idx) => {
                      // Build options list: matched alternatives (sorted by confidence) + all other procedures
                      const matchedCodes = new Set([
                        mapping.mapped_code,
                        ...(mapping.alternatives || []).map(alt => alt.code)
                      ])
                      
                      const matchedOptions = [
                        {
                          code: mapping.mapped_code,
                          name: mapping.mapped_name,
                          confidence_score: mapping.confidence_score,
                          isMatched: true,
                          isCurrent: true
                        },
                        ...(mapping.alternatives || [])
                          .filter(alt => alt.code !== mapping.mapped_code)
                          .map(alt => ({
                            code: alt.code,
                            name: alt.name,
                            confidence_score: alt.confidence_score,
                            isMatched: true,
                            isCurrent: false
                          }))
                      ].sort((a, b) => b.confidence_score - a.confidence_score)
                      
                      // All other procedures not in the matched list
                      const otherProcedures = allProcedures
                        .filter(proc => !matchedCodes.has(proc.code))
                        .map(proc => ({
                          code: proc.code,
                          name: proc.name,
                          confidence_score: 0,
                          isMatched: false,
                          isCurrent: false
                        }))

                      return (
                        <div key={idx} className="border rounded-lg p-4 hover:bg-gray-50">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                              <p className="font-medium text-gray-900 mb-3">{mapping.original_text}</p>
                              
                              {/* Searchable Procedure Dropdown */}
                              <div className="space-y-2">
                                <Label className="text-xs text-gray-500">Selected Procedure Code:</Label>
                                <ProcedureSelectorDropdown
                                  currentCode={mapping.mapped_code}
                                  currentName={mapping.mapped_name}
                                  matchedOptions={matchedOptions}
                                  otherProcedures={otherProcedures}
                                  onSelect={(code, name, confidenceScore) => {
                                    // Update the mapping
                                    const updatedMappings = [...budgetData.procedure_mappings]
                                    updatedMappings[idx] = {
                                      ...mapping,
                                      mapped_code: code,
                                      mapped_name: name,
                                      confidence_score: confidenceScore || 0
                                    }
                                    
                                    // Update budget data
                                    setBudgetData({
                                      ...budgetData,
                                      procedure_mappings: updatedMappings
                                    })
                                    
                                    console.log(`✅ Updated procedure mapping: ${mapping.original_text} -> ${code}`)
                                  }}
                                />
                              </div>
                            </div>
                            <div className="flex items-center gap-2 ml-4">
                              <Badge 
                                variant={mapping.confidence_score >= 0.8 ? "default" : "secondary"}
                                className={mapping.confidence_score >= 0.8 ? "bg-green-600" : "bg-amber-600"}
                              >
                                {(mapping.confidence_score * 100).toFixed(0)}% Match
                              </Badge>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Activity className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No procedure mappings available</p>
                    <p className="text-sm mt-1">Procedure mappings will appear here when SoA data is processed</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* OPAL TAB */}
          <TabsContent value="opal" className="space-y-4">
            <Card>
              <CardHeader className="bg-indigo-50">
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5 text-indigo-600" />
                  OPAL Overhead Calculation
                </CardTitle>
                <CardDescription>
                  Overhead Personnel and Administrative Logistics
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.opal_calculation ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-3 gap-4">
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-sm text-gray-600 mb-1">Total OPAL Hours</p>
                          <p className="text-3xl font-bold text-indigo-600">
                            {formatNumber(budgetData.opal_calculation.total_hours)}
                          </p>
                        </CardContent>
                      </Card>
                    </div>

                    {budgetData.opal_calculation.staff_breakdown && (
                      <>
                        <Separator />
                        <div>
                          <h3 className="font-semibold text-lg mb-4">Staff Hours Breakdown</h3>
                          <div className="border rounded-lg overflow-hidden">
                            <table className="w-full">
                              <thead className="bg-gray-50">
                                <tr>
                                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Hours</th>
                                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Percentage</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-200">
                                {Object.entries(budgetData.opal_calculation.staff_breakdown).map(([role, hours]) => (
                                  <tr key={role} className="hover:bg-gray-50">
                                    <td className="px-4 py-3 text-sm capitalize">{role.replace(/_/g, ' ')}</td>
                                    <td className="px-4 py-3 text-sm text-right font-semibold">{hours as number}</td>
                                    <td className="px-4 py-3 text-sm text-right text-gray-600">
                                      {((hours as number / budgetData.opal_calculation!.total_hours) * 100).toFixed(1)}%
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </>
                    )}

                    {budgetData.opal_calculation.complexity_modifiers && (
                      <>
                        <Separator />
                        <div>
                          <h3 className="font-semibold text-lg mb-4">Complexity Modifiers</h3>
                          <div className="space-y-2">
                            {Object.entries(budgetData.opal_calculation.complexity_modifiers).map(([modifier, value]) => (
                              <div key={modifier} className="flex justify-between items-center py-2 border-b border-gray-100">
                                <span className="text-gray-700 capitalize">{modifier.replace(/_/g, ' ')}</span>
                                <Badge variant="outline">×{value}</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Briefcase className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No OPAL calculation data available</p>
                    <p className="text-sm mt-1">OPAL calculation will appear here when budget is calculated</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* SITE COSTS TAB */}
          <TabsContent value="sites" className="space-y-4">
            <Card>
              <CardHeader className="bg-purple-50">
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-purple-600" />
                  Site Costs
                </CardTitle>
                <CardDescription>
                  Initiation, monitoring, and closeout costs per site
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Total Sites</p>
                    <p className="text-3xl font-bold text-purple-600">{totalSites}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Total Site Costs</p>
                    <p className="text-3xl font-bold text-green-600">
                      {formatCurrency(budgetData.budget.site_costs.total)}
                    </p>
                  </div>
                </div>

                <Separator className="my-6" />

                {budgetData.budget.site_costs.breakdown && Object.keys(budgetData.budget.site_costs.breakdown).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(budgetData.budget.site_costs.breakdown).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center py-3 border-b border-gray-100">
                        <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="font-semibold">{formatCurrency(value as number)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No detailed site cost breakdown available</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* OPERATIONAL TAB */}
          <TabsContent value="operational" className="space-y-4">
            <Card>
              <CardHeader className="bg-orange-50">
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5 text-orange-600" />
                  Operational Costs
                </CardTitle>
                <CardDescription>
                  CRAs, data management, systems, and regulatory costs
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Study Duration</p>
                    <p className="text-3xl font-bold text-orange-600">{durationMonths} months</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Total Operational Costs</p>
                    <p className="text-3xl font-bold text-green-600">
                      {formatCurrency(budgetData.budget.operational_costs.total)}
                    </p>
                  </div>
                </div>

                <Separator className="my-6" />

                {budgetData.budget.operational_costs.breakdown && Object.keys(budgetData.budget.operational_costs.breakdown).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(budgetData.budget.operational_costs.breakdown).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center py-3 border-b border-gray-100">
                        <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="font-semibold">{formatCurrency(value as number)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No detailed operational cost breakdown available</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ADDITIONAL COSTS TAB */}
          <TabsContent value="additional" className="space-y-4">
            {/* Section 1: Additional CRF Payments */}
            <Card>
              <CardHeader className="bg-indigo-50">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-indigo-600" />
                  Additional CRF-Based Payments
                </CardTitle>
                <CardDescription>
                  Per-CRF or per-event payments beyond the base CPP
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.additional_crf_payments && budgetData.budget.additional_crf_payments.items ? (
                  <div className="space-y-3">
                    {budgetData.budget.additional_crf_payments.items.map((item: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
                        <div>
                          <div className="text-gray-700 font-medium">{item.category}</div>
                          <div className="text-sm text-gray-500">{item.description}</div>
                          {item.per_patient && (
                            <div className="text-xs text-gray-400 mt-1">Per event: {formatCurrency(item.per_patient)}</div>
                          )}
                        </div>
                        <span className="font-semibold text-lg">{formatCurrency(item.amount)}</span>
                      </div>
                    ))}
                    
                    <Separator className="my-4" />
                    
                    <div className="flex justify-between items-center text-lg font-bold bg-indigo-100 p-4 rounded-lg">
                      <span>Total Additional CRF Payments</span>
                      <span className="text-indigo-700">{formatCurrency(budgetData.budget.additional_crf_payments.total)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No additional CRF payment data available</p>
                )}
              </CardContent>
            </Card>

            {/* Section 2: Invoice Items */}
            <Card>
              <CardHeader className="bg-pink-50">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-pink-600" />
                  Items Paid by Invoice
                </CardTitle>
                <CardDescription>
                  Vendor services and systems paid by invoice
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.invoice_items && budgetData.budget.invoice_items.items ? (
                  <div className="space-y-3">
                    {budgetData.budget.invoice_items.items.map((item: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
                        <div>
                          <div className="text-gray-700 font-medium">{item.category}</div>
                          <div className="text-sm text-gray-500">{item.description}</div>
                        </div>
                        <span className="font-semibold text-lg">{formatCurrency(item.amount)}</span>
                      </div>
                    ))}
                    
                    <Separator className="my-4" />
                    
                    <div className="flex justify-between items-center text-lg font-bold bg-pink-100 p-4 rounded-lg">
                      <span>Total Invoice Items</span>
                      <span className="text-pink-700">{formatCurrency(budgetData.budget.invoice_items.total)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No invoice item data available</p>
                )}
              </CardContent>
            </Card>

            {/* Section 3: Study-Level Fees */}
            <Card>
              <CardHeader className="bg-amber-50">
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-amber-600" />
                  Study-Level Fees
                </CardTitle>
                <CardDescription>
                  Study-level fees and one-time costs
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.study_level_fees && budgetData.budget.study_level_fees.items ? (
                  <div className="space-y-3">
                    {budgetData.budget.study_level_fees.items.map((item: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
                        <div>
                          <div className="text-gray-700 font-medium">{item.category}</div>
                          <div className="text-sm text-gray-500">{item.description}</div>
                        </div>
                        <span className="font-semibold text-lg">{formatCurrency(item.amount)}</span>
                      </div>
                    ))}
                    
                    <Separator className="my-4" />
                    
                    <div className="flex justify-between items-center text-lg font-bold bg-amber-100 p-4 rounded-lg">
                      <span>Total Study-Level Fees</span>
                      <span className="text-amber-700">{formatCurrency(budgetData.budget.study_level_fees.total)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No study-level fee data available</p>
                )}
              </CardContent>
            </Card>

            {/* Section 4: Total Additional Costs Summary */}
            <Card className="border-2 border-indigo-500">
              <CardHeader className="bg-indigo-100">
                <CardTitle className="text-xl flex items-center gap-2">
                  <TrendingUp className="h-6 w-6 text-indigo-600" />
                  Total Additional Costs (Estimated)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-gray-700">
                    <span>Additional CRF Payments</span>
                    <span className="font-semibold">{formatCurrency(budgetData.budget.additional_crf_payments?.total || 0)}</span>
                  </div>
                  <div className="flex justify-between items-center text-gray-700">
                    <span>Invoice Items</span>
                    <span className="font-semibold">{formatCurrency(budgetData.budget.invoice_items?.total || 0)}</span>
                  </div>
                  <div className="flex justify-between items-center text-gray-700">
                    <span>Study-Level Fees</span>
                    <span className="font-semibold">{formatCurrency(budgetData.budget.study_level_fees?.total || 0)}</span>
                  </div>
                  
                  <Separator className="my-4" />
                  
                  <div className="flex justify-between items-center text-2xl font-bold bg-indigo-50 p-4 rounded-lg">
                    <span>Total Additional Costs</span>
                    <span className="text-indigo-700">{formatCurrency(budgetData.budget.total_additional_costs || 0)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* DRUG SUPPLY TAB */}
          <TabsContent value="drug" className="space-y-4">
            <Card>
              <CardHeader className="bg-purple-50">
                <CardTitle className="flex items-center gap-2">
                  <Pill className="h-5 w-5 text-purple-600" />
                  Drug Supply Chain Costs
                </CardTitle>
                <CardDescription>
                  Complete drug supply chain from manufacturing to patient
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.drug_supply_chain && budgetData.budget.drug_supply_chain.breakdown ? (
                  <div className="space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Total Drug Costs</p>
                        <p className="text-3xl font-bold text-purple-600">
                          {formatCurrency(budgetData.budget.drug_supply_chain.total)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 mb-1">Per Patient Drug Cost</p>
                        <p className="text-3xl font-bold text-green-600">
                          {formatCurrency(budgetData.budget.drug_supply_chain.per_patient)}
                        </p>
                      </div>
                    </div>

                    <Separator />

                    {/* Breakdown */}
                    <div className="space-y-3">
                      <h3 className="font-semibold text-lg mb-4">Cost Breakdown</h3>
                      {Object.entries(budgetData.budget.drug_supply_chain.breakdown).map(([key, value]: [string, any], idx: number) => (
                        <div key={idx} className="flex justify-between items-center py-3 border-b border-gray-100">
                          <span className="text-gray-700 capitalize">{key.replace(/_/g, ' ')}</span>
                          <span className="font-semibold text-lg">{formatCurrency(value)}</span>
                        </div>
                      ))}
                      
                      <Separator className="my-4" />
                      
                      <div className="flex justify-between items-center text-xl font-bold bg-purple-100 p-4 rounded-lg">
                        <span>Total Drug Supply Chain</span>
                        <span className="text-purple-700">{formatCurrency(budgetData.budget.drug_supply_chain.total)}</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No drug supply chain data available</p>
                )}
              </CardContent>
            </Card>

            {/* Screening & Dropout Detail */}
            <Card>
              <CardHeader className="bg-blue-50">
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-blue-600" />
                  Screening & Dropout Analysis
                </CardTitle>
                <CardDescription>
                  Detailed attrition costs and patient replacement
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.screening_and_dropout ? (
                  <div className="space-y-6">
                    {/* Screening Section */}
                    {budgetData.budget.screening_and_dropout.screening && (
                      <div>
                        <h3 className="font-semibold text-lg mb-4">Screening</h3>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Total Screened</p>
                            <p className="text-2xl font-bold">{formatNumber(budgetData.budget.screening_and_dropout.screening.total_screened)}</p>
                          </div>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Screen Failures</p>
                            <p className="text-2xl font-bold text-red-600">{formatNumber(budgetData.budget.screening_and_dropout.screening.screen_failures)}</p>
                          </div>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Failure Rate</p>
                            <p className="text-2xl font-bold">{(budgetData.budget.screening_and_dropout.screening.screen_failure_rate * 100).toFixed(1)}%</p>
                          </div>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Screening Costs</p>
                            <p className="text-2xl font-bold text-orange-600">{formatCurrency(budgetData.budget.screening_and_dropout.screening.total_screening_costs)}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    <Separator />

                    {/* Dropout Section */}
                    {budgetData.budget.screening_and_dropout.dropout && (
                      <div>
                        <h3 className="font-semibold text-lg mb-4">Dropout & Replacement</h3>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Dropouts</p>
                            <p className="text-2xl font-bold text-red-600">{formatNumber(budgetData.budget.screening_and_dropout.dropout.num_dropouts)}</p>
                          </div>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Dropout Rate</p>
                            <p className="text-2xl font-bold">{(budgetData.budget.screening_and_dropout.dropout.dropout_rate * 100).toFixed(1)}%</p>
                          </div>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Replacements</p>
                            <p className="text-2xl font-bold text-blue-600">{formatNumber(budgetData.budget.screening_and_dropout.dropout.num_replacements)}</p>
                          </div>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Total Dropout Costs</p>
                            <p className="text-2xl font-bold text-orange-600">{formatCurrency(budgetData.budget.screening_and_dropout.dropout.total_dropout_costs)}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    <Separator />

                    {/* Total Attrition */}
                    <div className="bg-red-50 p-6 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="text-lg font-semibold text-gray-900">Total Attrition Costs</span>
                        <span className="text-3xl font-bold text-red-600">
                          {formatCurrency(budgetData.budget.screening_and_dropout.total_attrition_costs || 0)}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No screening/dropout data available</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* COUNTRIES TAB */}
          <TabsContent value="countries" className="space-y-4">
            {/* Country Breakdown */}
            <Card>
              <CardHeader className="bg-blue-50">
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5 text-blue-600" />
                  Country Breakdown
                </CardTitle>
                <CardDescription>
                  Patient allocation and costs by country with exchange rates
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.country_budgets && budgetData.budget.country_budgets.length > 0 ? (
                  <div className="space-y-6">
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Country</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Patients</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sites</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Currency</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total (Local)</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total (USD)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {budgetData.budget.country_budgets.map((country: any, idx: number) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                {country.country_name} ({country.country_code})
                              </td>
                              <td className="px-4 py-3 text-sm text-right text-gray-700">{formatNumber(country.num_patients)}</td>
                              <td className="px-4 py-3 text-sm text-right text-gray-700">{formatNumber(country.num_sites)}</td>
                              <td className="px-4 py-3 text-sm text-right text-gray-700">{country.currency}</td>
                              <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                                {new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(country.total_local)}
                              </td>
                              <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                                {formatCurrency(country.total_usd)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">No country breakdown available (defaulting to 100% USA)</p>
                )}
              </CardContent>
            </Card>

            {/* Globalized Total */}
            <Card className="border-4 border-blue-500">
              <CardHeader className="bg-blue-100">
                <CardTitle className="text-2xl flex items-center gap-2">
                  <Globe className="h-6 w-6 text-blue-600" />
                  Globalized Grand Total
                </CardTitle>
                <CardDescription className="text-base">
                  Includes exchange rate buffer and country-specific adjustments
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="flex justify-between items-center text-gray-700 text-lg">
                    <span>Base Grand Total (USD)</span>
                    <span className="font-semibold">{formatCurrency(budgetData.budget.updated_grand_total || budgetData.budget.grand_total)}</span>
                  </div>
                  <div className="flex justify-between items-center text-gray-700 text-lg">
                    <span>Exchange Rate Buffer</span>
                    <span className="font-semibold text-amber-600">+12%</span>
                  </div>
                  
                  <Separator className="my-4" />
                  
                  <div className="text-center py-6 bg-blue-50 rounded-lg">
                    <p className="text-lg text-gray-600 mb-2">Globalized Total (USD)</p>
                    <p className="text-5xl font-bold text-blue-600">
                      {formatCurrency(budgetData.budget.globalized_total_usd || budgetData.budget.updated_grand_total)}
                    </p>
                    <p className="text-sm text-gray-500 mt-2">
                      Final budget including all costs, country adjustments, and currency risk buffer
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* TIMELINE TAB */}
          <TabsContent value="timeline" className="space-y-4">
            <Card>
              <CardHeader className="bg-teal-50">
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-teal-600" />
                  Timeline & Cashflow
                </CardTitle>
                <CardDescription>
                  Monthly cost projections and cumulative spend
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                {budgetData.budget.timeline && budgetData.budget.timeline.monthly_cashflow && budgetData.budget.timeline.monthly_cashflow.length > 0 ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-3 gap-4">
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-sm text-gray-600 mb-1">Total Duration</p>
                          <p className="text-2xl font-bold text-teal-600">
                            {budgetData.budget.timeline.total_months} months
                          </p>
                        </CardContent>
                      </Card>
                    </div>

                    <Separator />

                    <div className="border rounded-lg overflow-hidden max-h-96 overflow-y-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Month</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Monthly Cost</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cumulative</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {budgetData.budget.timeline.monthly_cashflow.map((month: any, idx: number) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm">Month {idx + 1}</td>
                              <td className="px-4 py-3 text-sm text-right font-semibold">
                                {formatCurrency(month.monthly_cost || 0)}
                              </td>
                              <td className="px-4 py-3 text-sm text-right text-gray-600">
                                {formatCurrency(month.cumulative_spend || 0)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Calendar className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No timeline data available</p>
                    <p className="text-sm mt-1">Monthly cashflow projections will appear here when calculated</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* OVERHEAD TAB */}
          <TabsContent value="overhead" className="space-y-4">
            <EnhancedOverheadDisplay 
              overheadData={budgetData.budget.overhead}
              totalBudget={budgetData.budget.grand_total}
            />
          </TabsContent>

          {/* EXPORT TAB */}
          <TabsContent value="export" className="space-y-4">
            <BudgetExportManager 
              budgetData={budgetData.budget}
              studyName={`${studyContext.indication || 'Study'} - Phase ${studyContext.phase || 'III'}`}
            />
            
            {/* Country Allocation Manager */}
            <CountryAllocationManager
              totalPatients={totalPatients}
              totalBudget={budgetData.budget.grand_total}
              onAllocationChange={(allocations) => {
                console.log('Country allocations updated:', allocations)
              }}
            />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

