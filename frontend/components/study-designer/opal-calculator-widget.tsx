/**
 * OPAL Calculator Widget
 * Calculates overhead staffing hours based on study complexity
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Loader2, Calculator } from 'lucide-react'
import { cppApi } from '@/lib/api/cpp-api'
import type { OPALInput, OPALResult, StudyType, Phase } from '@/lib/types/cpp'

interface OPALCalculatorWidgetProps {
  onCalculate?: (result: OPALResult) => void
  initialValues?: Partial<OPALInput>
}

export function OPALCalculatorWidget({ onCalculate, initialValues }: OPALCalculatorWidgetProps) {
  const [input, setInput] = useState<OPALInput>({
    study_type: initialValues?.study_type || 'Interventional' as StudyType,
    phase: initialValues?.phase || 'Phase III' as Phase,
    num_arms: initialValues?.num_arms || 2,
    therapeutic_area: initialValues?.therapeutic_area || '',
    has_tissue_biopsy: initialValues?.has_tissue_biopsy || false,
    has_pk_draws: initialValues?.has_pk_draws || false,
    has_specialized_procedures: initialValues?.has_specialized_procedures || false,
    has_complex_assessments: initialValues?.has_complex_assessments || false,
    num_special_procedures: initialValues?.num_special_procedures || 0,
    num_complex_procedures: initialValues?.num_complex_procedures || 0
  })

  const [result, setResult] = useState<OPALResult | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCalculate = async () => {
    setIsCalculating(true)
    setError(null)

    try {
      const response = await cppApi.calculateOPAL(input)
      setResult(response.opal)
      onCalculate?.(response.opal)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate OPAL')
      console.error('Error calculating OPAL:', err)
    } finally {
      setIsCalculating(false)
    }
  }

  const updateInput = (updates: Partial<OPALInput>) => {
    setInput(prev => ({ ...prev, ...updates }))
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>OPAL Calculator</CardTitle>
          <CardDescription>
            Calculate overhead staffing hours based on study complexity
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Study Type */}
          <div className="space-y-2">
            <Label>Study Type</Label>
            <Select
              value={input.study_type}
              onValueChange={(value) => updateInput({ study_type: value as StudyType })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Interventional">Interventional</SelectItem>
                <SelectItem value="Observational">Observational</SelectItem>
                <SelectItem value="Early Termination">Early Termination</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Phase */}
          <div className="space-y-2">
            <Label>Phase</Label>
            <Select
              value={input.phase}
              onValueChange={(value) => updateInput({ phase: value as Phase })}
            >
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

          {/* Number of Arms */}
          <div className="space-y-2">
            <Label>Number of Arms</Label>
            <Input
              type="number"
              min="1"
              value={input.num_arms}
              onChange={(e) => updateInput({ num_arms: parseInt(e.target.value) || 1 })}
            />
          </div>

          {/* Therapeutic Area */}
          <div className="space-y-2">
            <Label>Therapeutic Area (Optional)</Label>
            <Input
              placeholder="e.g., Oncology, Cardiovascular"
              value={input.therapeutic_area}
              onChange={(e) => updateInput({ therapeutic_area: e.target.value })}
            />
          </div>

          {/* Special Procedures */}
          <div className="space-y-2">
            <Label className="text-base font-semibold">Special Procedures</Label>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="tissue_biopsy"
                  checked={input.has_tissue_biopsy}
                  onCheckedChange={(checked) => 
                    updateInput({ has_tissue_biopsy: checked as boolean })
                  }
                />
                <label
                  htmlFor="tissue_biopsy"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Tissue Biopsy
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="pk_draws"
                  checked={input.has_pk_draws}
                  onCheckedChange={(checked) => 
                    updateInput({ has_pk_draws: checked as boolean })
                  }
                />
                <label
                  htmlFor="pk_draws"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  PK Draws
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="specialized_procedures"
                  checked={input.has_specialized_procedures}
                  onCheckedChange={(checked) => 
                    updateInput({ has_specialized_procedures: checked as boolean })
                  }
                />
                <label
                  htmlFor="specialized_procedures"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Specialized Procedures
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="complex_assessments"
                  checked={input.has_complex_assessments}
                  onCheckedChange={(checked) => 
                    updateInput({ has_complex_assessments: checked as boolean })
                  }
                />
                <label
                  htmlFor="complex_assessments"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Complex Assessments
                </label>
              </div>
            </div>
          </div>

          {/* Procedure Counts */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Special Procedures Count</Label>
              <Input
                type="number"
                min="0"
                value={input.num_special_procedures}
                onChange={(e) => updateInput({ num_special_procedures: parseInt(e.target.value) || 0 })}
              />
            </div>
            <div className="space-y-2">
              <Label>Complex Procedures Count</Label>
              <Input
                type="number"
                min="0"
                value={input.num_complex_procedures}
                onChange={(e) => updateInput({ num_complex_procedures: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>

          {/* Calculate Button */}
          <Button 
            onClick={handleCalculate} 
            disabled={isCalculating}
            className="w-full"
          >
            {isCalculating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Calculating...
              </>
            ) : (
              <>
                <Calculator className="mr-2 h-4 w-4" />
                Calculate OPAL
              </>
            )}
          </Button>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>OPAL Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Scores */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-3 bg-blue-50 rounded-md border border-blue-200">
                <p className="text-sm text-muted-foreground">Raw Score</p>
                <p className="text-2xl font-bold text-blue-900">{result.raw_score.toFixed(1)}</p>
              </div>
              <div className="p-3 bg-purple-50 rounded-md border border-purple-200">
                <p className="text-sm text-muted-foreground">Modifiers</p>
                <p className="text-2xl font-bold text-purple-900">+{result.modifier_score.toFixed(1)}</p>
              </div>
              <div className="p-3 bg-green-50 rounded-md border border-green-200">
                <p className="text-sm text-muted-foreground">Adjusted Score</p>
                <p className="text-2xl font-bold text-green-900">{result.adjusted_score.toFixed(1)}</p>
              </div>
            </div>

            {/* Total Hours */}
            <div className="p-4 bg-gray-50 rounded-md border border-gray-200">
              <p className="text-sm text-muted-foreground mb-1">Total Overhead Hours</p>
              <p className="text-3xl font-bold">{result.total_overhead_hours.toFixed(1)} hours</p>
            </div>

            {/* Staff Distribution */}
            <div className="space-y-2">
              <p className="font-semibold">Staff Distribution by Visit Type</p>
              <div className="space-y-3">
                {Object.entries(result.staff_distribution).slice(0, 3).map(([visitType, roles]) => (
                  <div key={visitType} className="p-3 border rounded-md">
                    <p className="text-sm font-medium mb-2">{visitType}</p>
                    <div className="grid grid-cols-4 gap-2 text-sm">
                      <div>
                        <p className="text-muted-foreground">PI</p>
                        <p className="font-semibold">{roles.PI.toFixed(1)}h</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Nurse</p>
                        <p className="font-semibold">{roles.Nurse.toFixed(1)}h</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">CRC</p>
                        <p className="font-semibold">{roles.CRC.toFixed(1)}h</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">CRA</p>
                        <p className="font-semibold">{roles.CRA.toFixed(1)}h</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}







