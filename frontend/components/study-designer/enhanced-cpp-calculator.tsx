/**
 * Enhanced Context-Aware CPP Calculator
 * Automatically populates from study context - minimal user input required
 */

"use client"

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2, DollarSign, MapPin, Users, TrendingUp, CheckCircle, AlertTriangle } from 'lucide-react'
import { useStudyDesigner } from '@/lib/contexts/study-designer-context'
import { cppApi } from '@/lib/api/cpp-api'
import type { CPPInput, CPPResult, OPALInput, VisitProcedure, Phase, StudyType } from '@/lib/types/cpp'
import { toast } from 'sonner'

interface CountryAllocation {
  country_code: string
  country_name: string
  site_count: number
  patient_percentage: number
  patient_count: number
}

export function EnhancedCPPCalculator() {
  const {
    studyContext,
    selectedSites,
    studyDesign,
    protocolSections,
    cppResult,
    setCppResult
  } = useStudyDesigner()

  // Auto-populated state
  const [countryAllocations, setCountryAllocations] = useState<CountryAllocation[]>([])
  const [result, setResult] = useState<CPPResult | null>(cppResult)
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Calculate country allocations from selected sites
  useEffect(() => {
    if (selectedSites.length === 0) return

    // Group sites by country
    const sitesByCountry: Record<string, any[]> = {}
    selectedSites.forEach(site => {
      const country = site.country_code || site.country || 'USA'
      if (!sitesByCountry[country]) {
        sitesByCountry[country] = []
      }
      sitesByCountry[country].push(site)
    })

    // Calculate allocations based on site count (can be adjusted by user)
    const totalSites = selectedSites.length
    const totalPatients = studyContext.totalParticipants || studyDesign?.totalParticipants || 300

    const allocations: CountryAllocation[] = Object.entries(sitesByCountry).map(([countryCode, sites]) => {
      const siteCount = sites.length
      const percentage = (siteCount / totalSites) * 100
      const patientCount = Math.round((percentage / 100) * totalPatients)

      return {
        country_code: countryCode,
        country_name: getCountryName(countryCode),
        site_count: siteCount,
        patient_percentage: percentage,
        patient_count: patientCount
      }
    })

    setCountryAllocations(allocations)
  }, [selectedSites, studyContext.totalParticipants, studyDesign?.totalParticipants])

  // Auto-extract procedures from SoA if available
  const extractedProcedures = useMemo(() => {
    const soaSection = protocolSections['schedule_of_activities'] || protocolSections['soa']
    if (!soaSection) return []

    // Simple extraction - look for common procedure patterns
    const procedures: string[] = []
    const lines = soaSection.split('\n')
    
    // Common procedure indicators
    const procedureKeywords = [
      'vital signs', 'blood pressure', 'ecg', 'ekg', 'physical exam',
      'lab', 'laboratory', 'blood draw', 'urine', 'biopsy',
      'mri', 'ct scan', 'x-ray', 'imaging',
      'questionnaire', 'assessment', 'evaluation'
    ]

    lines.forEach(line => {
      const lowerLine = line.toLowerCase()
      procedureKeywords.forEach(keyword => {
        if (lowerLine.includes(keyword) && !procedures.some(p => p.toLowerCase().includes(keyword))) {
          // Extract the procedure text
          const match = line.match(/(?:[-•*]\s*)?([^:|\n]+)/)?.[1]?.trim()
          if (match && match.length > 3 && match.length < 100) {
            procedures.push(match)
          }
        }
      })
    })

    return procedures.slice(0, 20) // Limit to 20 procedures
  }, [protocolSections])

  // Auto-configure OPAL input from study context
  const opalInput: OPALInput = useMemo(() => ({
    study_type: (studyDesign?.studyType || 'Interventional') as StudyType,
    phase: studyContext.phase as Phase || 'Phase III' as Phase,
    num_arms: studyDesign?.arms?.length || 2,
    therapeutic_area: studyContext.therapeuticArea || studyContext.indication,
    has_tissue_biopsy: false, // User can adjust in advanced settings
    has_pk_draws: false,
    has_specialized_procedures: false,
    has_complex_assessments: false,
    num_special_procedures: 0,
    num_complex_procedures: 0
  }), [studyContext, studyDesign])

  // Update patient count when user adjusts percentages
  const updateAllocation = (countryCode: string, newPercentage: number) => {
    setCountryAllocations(prev => {
      const updated = [...prev]
      const index = updated.findIndex(a => a.country_code === countryCode)
      if (index !== -1) {
        const totalPatients = studyContext.totalParticipants || studyDesign?.totalParticipants || 300
        updated[index].patient_percentage = newPercentage
        updated[index].patient_count = Math.round((newPercentage / 100) * totalPatients)
      }
      return updated
    })
  }

  // Normalize percentages to 100%
  const normalizeAllocations = () => {
    const total = countryAllocations.reduce((sum, a) => sum + a.patient_percentage, 0)
    if (Math.abs(total - 100) < 0.01) return // Already normalized

    setCountryAllocations(prev => {
      const factor = 100 / total
      return prev.map(a => ({
        ...a,
        patient_percentage: a.patient_percentage * factor,
        patient_count: Math.round((a.patient_percentage * factor / 100) * (studyContext.totalParticipants || 300))
      }))
    })
  }

  // Calculate CPP for each country
  const handleCalculate = async () => {
    if (countryAllocations.length === 0) {
      setError('No countries selected. Please select sites first.')
      return
    }

    setIsCalculating(true)
    setError(null)

    try {
      // For now, calculate for the primary country (most patients)
      const primaryCountry = countryAllocations.reduce((max, a) => 
        a.patient_count > max.patient_count ? a : max
      )

      // Map extracted procedures
      let mappedProcedures: VisitProcedure[] = []
      if (extractedProcedures.length > 0) {
        toast.info(`Mapping ${extractedProcedures.length} procedures from SoA...`)
        
        const mappingResponse = await cppApi.mapProceduresBatch(extractedProcedures, false)
        mappedProcedures = mappingResponse.matches.map((match, idx) => ({
          visit_name: `Visit ${idx + 1}`,
          visit_number: idx + 1,
          procedure_code: match.matched_code || '*INCO',
          procedure_name: match.matched_description || extractedProcedures[idx],
          frequency: 1.0
        }))
      } else {
        // Use default procedures
        mappedProcedures = [
          {
            visit_name: 'Screening',
            visit_number: 1,
            procedure_code: '*INCO',
            procedure_name: 'Inconvenience Fee',
            frequency: 1.0
          },
          {
            visit_name: 'Baseline',
            visit_number: 2,
            procedure_code: '*RNDO',
            procedure_name: 'Randomization',
            frequency: 1.0
          }
        ]
      }

      // Calculate CPP
      const input: CPPInput = {
        indication: studyContext.indication || 'Unknown',
        phase: studyContext.phase || 'Phase III',
        country_code: primaryCountry.country_code,
        procedures: mappedProcedures,
        opal_input: opalInput,
        study_context: {
          total_patients: studyContext.totalParticipants,
          site_count: selectedSites.length,
          study_design: studyDesign?.studyType,
          country_allocations: countryAllocations
        }
      }

      const response = await cppApi.calculateCPP(input)
      setResult(response.cpp)
      setCppResult(response.cpp) // Save to global context
      toast.success(`CPP calculated for ${primaryCountry.country_name}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate CPP')
      console.error('Error calculating CPP:', err)
      toast.error('Failed to calculate CPP')
    } finally {
      setIsCalculating(false)
    }
  }

  const getCountryName = (code: string): string => {
    const countries: Record<string, string> = {
      'USA': 'United States',
      'GBR': 'United Kingdom',
      'DEU': 'Germany',
      'FRA': 'France',
      'JPN': 'Japan',
      'CHN': 'China',
      'IND': 'India',
      'CAN': 'Canada',
      'AUS': 'Australia'
    }
    return countries[code] || code
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const totalPercentage = countryAllocations.reduce((sum, a) => sum + a.patient_percentage, 0)
  const isValidAllocation = Math.abs(totalPercentage - 100) < 0.01

  return (
    <div className="space-y-6">
      {/* Auto-Populated Context Summary */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-900">
            <CheckCircle className="h-5 w-5" />
            Auto-Populated from Study Context
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-semibold">Indication:</span> {studyContext.indication || 'Not set'}
            </div>
            <div>
              <span className="font-semibold">Phase:</span> {studyContext.phase || 'Not set'}
            </div>
            <div>
              <span className="font-semibold">Total Patients:</span> {studyContext.totalParticipants || studyDesign?.totalParticipants || 'Not set'}
            </div>
            <div>
              <span className="font-semibold">Number of Arms:</span> {studyDesign?.arms?.length || 'Not set'}
            </div>
            <div>
              <span className="font-semibold">Selected Sites:</span> {selectedSites.length}
            </div>
            <div>
              <span className="font-semibold">Procedures Found:</span> {extractedProcedures.length || 'None (using defaults)'}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Country Allocation - User Input Required */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Country Patient Allocation
          </CardTitle>
          <CardDescription>
            Adjust the percentage of patients per country (based on site distribution)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {countryAllocations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertTriangle className="h-12 w-12 mx-auto mb-2 text-yellow-500" />
              <p>No sites selected. Please select sites in the Site Selection tab first.</p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {countryAllocations.map((allocation) => (
                  <div key={allocation.country_code} className="flex items-center gap-4 p-3 border rounded-lg">
                    <div className="flex-1">
                      <div className="font-semibold">{allocation.country_name}</div>
                      <div className="text-sm text-muted-foreground">
                        {allocation.site_count} sites
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        value={allocation.patient_percentage.toFixed(1)}
                        onChange={(e) => updateAllocation(allocation.country_code, parseFloat(e.target.value))}
                        className="w-24"
                      />
                      <span className="text-sm">%</span>
                    </div>
                    <div className="text-right min-w-[100px]">
                      <div className="font-semibold">{allocation.patient_count}</div>
                      <div className="text-sm text-muted-foreground">patients</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Allocation Summary */}
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border-2">
                <div>
                  <span className="font-semibold">Total:</span>
                  <span className="ml-2">{totalPercentage.toFixed(1)}%</span>
                  {!isValidAllocation && (
                    <Badge variant="outline" className="ml-2 border-yellow-500 text-yellow-700">
                      Should equal 100%
                    </Badge>
                  )}
                </div>
                <div>
                  <span className="font-semibold">
                    {countryAllocations.reduce((sum, a) => sum + a.patient_count, 0)} patients
                  </span>
                </div>
              </div>

              {!isValidAllocation && (
                <Button variant="outline" onClick={normalizeAllocations} className="w-full">
                  Normalize to 100%
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Calculate Button */}
      <Card>
        <CardContent className="pt-6">
          <Button
            onClick={handleCalculate}
            disabled={isCalculating || countryAllocations.length === 0 || !isValidAllocation}
            size="lg"
            className="w-full"
          >
            {isCalculating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Calculating CPP...
              </>
            ) : (
              <>
                <DollarSign className="mr-2 h-4 w-4" />
                Calculate Clinical Per-Patient Cost
              </>
            )}
          </Button>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Total CPP */}
          <Card className="border-green-500 border-2">
            <CardHeader>
              <CardTitle className="text-2xl">Clinical Per-Patient Cost</CardTitle>
              <CardDescription>
                {result.country_code} • {result.currency}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-5xl font-bold text-green-600 mb-4">
                {formatCurrency(result.total_cpp)}
              </div>
              
              {/* Total Study Cost */}
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Study Cost</p>
                    <p className="text-2xl font-bold text-blue-900">
                      {formatCurrency(result.total_cpp * (studyContext.totalParticipants || 300))}
                    </p>
                  </div>
                  <Users className="h-8 w-8 text-blue-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Cost Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { label: 'Direct Procedures', value: result.breakdown.direct_procedures },
                  { label: 'Staff Overhead (OPAL)', value: result.breakdown.staff_overhead },
                  { label: 'Administration', value: result.breakdown.administration },
                  { label: 'Travel Stipend', value: result.breakdown.travel_stipend },
                  { label: 'Other Direct Costs', value: result.breakdown.other_direct_costs },
                  { label: 'Country Adjustments', value: result.breakdown.country_adjustments },
                ].map(item => (
                  <div key={item.label} className="flex justify-between items-center py-2 border-b">
                    <span className="text-sm font-medium">{item.label}</span>
                    <span className="text-sm">{formatCurrency(item.value)}</span>
                  </div>
                ))}
                <div className="flex justify-between items-center py-3 text-lg font-bold bg-green-50 px-2 rounded border-2 border-green-500 mt-4">
                  <span>TOTAL CPP</span>
                  <span>{formatCurrency(result.breakdown.total_cpp)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Country-Specific Costs */}
          <Card>
            <CardHeader>
              <CardTitle>Estimated Cost by Country</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {countryAllocations.map(allocation => (
                  <div key={allocation.country_code} className="flex justify-between items-center p-3 border rounded">
                    <div>
                      <div className="font-semibold">{allocation.country_name}</div>
                      <div className="text-sm text-muted-foreground">
                        {allocation.patient_count} patients • {allocation.site_count} sites
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">
                        {formatCurrency(result.total_cpp * allocation.patient_count)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {allocation.patient_percentage.toFixed(1)}% of total
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

