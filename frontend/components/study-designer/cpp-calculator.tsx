/**
 * CPP Calculator Component
 * Complete Clinical Per-Patient cost calculation
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2, DollarSign, Info, TrendingUp, FileText } from 'lucide-react'
import { cppApi } from '@/lib/api/cpp-api'
import type { CPPInput, CPPResult, OPALInput, VisitProcedure, Phase, StudyType } from '@/lib/types/cpp'
import { ProcedureMapper } from './procedure-mapper'
import { OPALCalculatorWidget } from './opal-calculator-widget'

interface CPPCalculatorProps {
  indication?: string
  phase?: string
  onCalculationComplete?: (result: CPPResult) => void
}

export function CPPCalculator({ indication: initialIndication, phase: initialPhase, onCalculationComplete }: CPPCalculatorProps) {
  const [indication, setIndication] = useState(initialIndication || '')
  const [phase, setPhase] = useState<string>(initialPhase || 'Phase III')
  const [countryCode, setCountryCode] = useState('USA')
  const [visitProcedures, setVisitProcedures] = useState<VisitProcedure[]>([])
  const [opalInput, setOpalInput] = useState<OPALInput | null>(null)
  const [result, setResult] = useState<CPPResult | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCalculate = async () => {
    if (!indication || !phase || visitProcedures.length === 0 || !opalInput) {
      setError('Please complete all sections before calculating')
      return
    }

    setIsCalculating(true)
    setError(null)

    try {
      const input: CPPInput = {
        indication,
        phase,
        country_code: countryCode,
        procedures: visitProcedures,
        opal_input: opalInput,
        study_context: {
          calculation_date: new Date().toISOString()
        }
      }

      const response = await cppApi.calculateCPP(input)
      setResult(response.cpp)
      onCalculationComplete?.(response.cpp)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate CPP')
      console.error('Error calculating CPP:', err)
    } finally {
      setIsCalculating(false)
    }
  }

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Clinical Per-Patient (CPP) Calculator
          </CardTitle>
          <CardDescription>
            Calculate accurate Fair Market Value costs using OPAL overhead, FMV pricing, and rule-based adjustments
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Basic Information */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Indication</Label>
              <Input
                placeholder="e.g., NSCLC, Type 2 Diabetes"
                value={indication}
                onChange={(e) => setIndication(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Phase</Label>
              <Select value={phase} onValueChange={setPhase}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Phase I">Phase I</SelectItem>
                  <SelectItem value="Phase II">Phase II</SelectItem>
                  <SelectItem value="Phase III">Phase III</SelectItem>
                  <SelectItem value="Phase IV">Phase IV</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Country</Label>
              <Select value={countryCode} onValueChange={setCountryCode}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USA">United States</SelectItem>
                  <SelectItem value="GBR">United Kingdom</SelectItem>
                  <SelectItem value="DEU">Germany</SelectItem>
                  <SelectItem value="FRA">France</SelectItem>
                  <SelectItem value="JPN">Japan</SelectItem>
                  <SelectItem value="CHN">China</SelectItem>
                  <SelectItem value="IND">India</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Tabs */}
      <Tabs defaultValue="procedures" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="procedures">Procedure Mapping</TabsTrigger>
          <TabsTrigger value="opal">OPAL Overhead</TabsTrigger>
        </TabsList>

        <TabsContent value="procedures" className="space-y-4">
          <ProcedureMapper
            onMappingsComplete={(mappings) => {
              const procedures: VisitProcedure[] = mappings.map((m, idx) => ({
                visit_name: "Visit " + (idx + 1),
                visit_number: idx + 1,
                procedure_code: m.code,
                procedure_name: m.description,
                frequency: 1.0
              }))
              setVisitProcedures(procedures)
            }}
          />
        </TabsContent>

        <TabsContent value="opal" className="space-y-4">
          <OPALCalculatorWidget
            initialValues={{
              study_type: 'Interventional' as StudyType,
              phase: phase as Phase,
              num_arms: 2
            }}
            onCalculate={(opalResult) => {
              setOpalInput({
                study_type: 'Interventional' as StudyType,
                phase: phase as Phase,
                num_arms: 2,
                therapeutic_area: indication
              })
            }}
          />
        </TabsContent>
      </Tabs>

      {/* Calculate Button */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* Status */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm font-medium">Ready to Calculate</p>
                <p className="text-xs text-muted-foreground">
                  {visitProcedures.length} procedures mapped • OPAL {opalInput ? 'configured' : 'pending'}
                </p>
              </div>
              <Button 
                onClick={handleCalculate}
                disabled={isCalculating || !indication || !opalInput || visitProcedures.length === 0}
                size="lg"
              >
                {isCalculating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Calculating CPP...
                  </>
                ) : (
                  <>
                    <DollarSign className="mr-2 h-4 w-4" />
                    Calculate CPP
                  </>
                )}
              </Button>
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
                {error}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Total CPP */}
          <Card className="border-green-500 border-2">
            <CardHeader>
              <CardTitle className="text-2xl">Total Clinical Per-Patient Cost</CardTitle>
              <CardDescription>{result.country_code} • {result.currency}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-5xl font-bold text-green-600">
                {formatCurrency(result.total_cpp, result.currency)}
              </p>
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
                    <span className="text-sm">{formatCurrency(item.value, result.currency)}</span>
                  </div>
                ))}
                <div className="flex justify-between items-center py-2 font-semibold bg-gray-50 px-2 rounded">
                  <span>Subtotal</span>
                  <span>{formatCurrency(result.breakdown.total_before_overhead, result.currency)}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm font-medium">Overhead ({result.breakdown.overhead_percentage}%)</span>
                  <span className="text-sm">{formatCurrency(result.breakdown.overhead_amount, result.currency)}</span>
                </div>
                <div className="flex justify-between items-center py-3 text-lg font-bold bg-green-50 px-2 rounded border-2 border-green-500">
                  <span>TOTAL CPP</span>
                  <span>{formatCurrency(result.breakdown.total_cpp, result.currency)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Rules Applied */}
          {result.rules_applied && result.rules_applied.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Rules Applied ({result.rules_applied.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {result.rules_applied.map((rule, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-blue-50 rounded border border-blue-200">
                      <span className="text-sm font-medium">{rule.rule_name}</span>
                      <span className="text-sm font-semibold text-blue-900">
                        {rule.applied_value >= 0 ? '+' : ''}{formatCurrency(rule.applied_value, result.currency)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* OPAL Summary */}
          {result.opal_result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  OPAL Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-purple-50 rounded border border-purple-200">
                    <p className="text-sm text-muted-foreground">Adjusted OPAL Score</p>
                    <p className="text-2xl font-bold text-purple-900">{result.opal_result.adjusted_score.toFixed(1)}</p>
                  </div>
                  <div className="p-3 bg-purple-50 rounded border border-purple-200">
                    <p className="text-sm text-muted-foreground">Total Overhead Hours</p>
                    <p className="text-2xl font-bold text-purple-900">{result.opal_result.total_overhead_hours.toFixed(1)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}







