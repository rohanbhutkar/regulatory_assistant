"use client"

import { Card } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DollarSign, TrendingUp, TrendingDown, RefreshCw } from "lucide-react"
import { useAnalysisAPI } from "@/lib/hooks/use-analysis-api"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { toast } from "sonner"
import { useState, useEffect } from "react"

interface BudgetTabProps {
  studyId?: string
  studyDesign?: any
  sites?: any[]
}

export function BudgetTab({ studyId: propsStudyId, studyDesign: propsStudyDesign, sites: propsSites }: BudgetTabProps = {}) {
  // Use context data with props as fallback
  const {
    budgetData: contextBudgetData,
    setBudgetData: setContextBudgetData,
    selectedSites: contextSites,
    studyDesign: contextStudyDesign,
    indication,
    phase,
    isLoading: contextLoading
  } = useStudyDesigner()

  // Use context data if available, otherwise use props
  const studyDesign = propsStudyDesign !== undefined ? propsStudyDesign : contextStudyDesign
  const sites = propsSites !== undefined ? propsSites : contextSites
  const studyId = propsStudyId || "context-study"

  const { analyzeBudget, isLoading, error } = useAnalysisAPI()
  const [localBudgetData, setLocalBudgetData] = useState<any>(null)

  // Use context or local budget data
  const budgetData = contextBudgetData || localBudgetData
  const setBudgetData = propsStudyDesign === undefined ? setContextBudgetData : setLocalBudgetData

  console.log("🔍 Budget Tab:", {
    contextBudgetData: !!contextBudgetData,
    localBudgetData: !!localBudgetData,
    usingContext: propsStudyDesign === undefined,
    indication,
    phase,
    sitesCount: sites.length
  })

  const loadBudgetAnalysis = async () => {
    try {
      const request = {
        studyDesign: studyDesign,
        sites: sites,
        patientCount: studyDesign?.patient_count || 300,
        durationMonths: studyDesign?.duration_months || 24,
        therapeuticArea: studyDesign?.therapeutic_area || therapeuticArea || 'Oncology'
      }

      const response = await analyzeBudget(request)

      if (response && response.success) {
        setBudgetData(response)
        toast.success('Budget analysis completed successfully!')
      } else {
        toast.error('Budget analysis failed. Please try again.')
      }
    } catch (err) {
      console.error('Error analyzing budget:', err)
      toast.error('Error analyzing budget. Please try again.')
    }
  }

  useEffect(() => {
    loadBudgetAnalysis()
  }, [studyDesign, sites])

  if (!budgetData) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Trial Budget & Burden Calculations</h2>
            <p className="text-muted-foreground">Detailed cost breakdown and per-patient analysis</p>
          </div>
          <Button onClick={loadBudgetAnalysis} disabled={isLoading} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Analyzing...' : 'Refresh Analysis'}
          </Button>
        </div>
        <Card className="p-12">
          <div className="text-center space-y-4">
            <DollarSign className="h-16 w-16 text-muted-foreground mx-auto" />
            <h3 className="text-xl font-semibold text-foreground">Loading Budget Analysis</h3>
            <p className="text-muted-foreground">Analyzing study costs and budget requirements...</p>
          </div>
        </Card>
      </div>
    )
  }

  const totalCost = budgetData.total_cost
  const costPerPatient = budgetData.cost_per_patient

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Trial Budget & Burden Calculations</h2>
          <p className="text-muted-foreground">Detailed cost breakdown and per-patient analysis</p>
        </div>
        <Button onClick={loadBudgetAnalysis} disabled={isLoading} className="gap-2">
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Analyzing...' : 'Refresh Analysis'}
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-2">
            <DollarSign className="h-5 w-5 text-primary" />
            <div className="text-sm text-muted-foreground">Total Study Cost</div>
          </div>
          <div className="text-3xl font-bold text-foreground">${(totalCost / 1000000).toFixed(2)}M</div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-2">
            <DollarSign className="h-5 w-5 text-accent" />
            <div className="text-sm text-muted-foreground">Cost Per Patient</div>
          </div>
          <div className="text-3xl font-bold text-foreground">${costPerPatient.toLocaleString()}</div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="h-5 w-5 text-success" />
            <div className="text-sm text-muted-foreground">Budget Status</div>
          </div>
          <Badge variant="default" className="text-lg px-3 py-1">
            {budgetData.budget_status}
          </Badge>
        </Card>
      </div>

      {/* Budget Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Category</TableHead>
              <TableHead>Subcategory</TableHead>
              <TableHead className="text-right">Total Cost</TableHead>
              <TableHead className="text-right">Cost Per Patient</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Object.entries(budgetData.cost_breakdown).map(([category, subcategories]: [string, any]) =>
              Object.entries(subcategories).map(([subcategory, cost]: [string, any]) => (
                <TableRow key={`${category}-${subcategory}`}>
                  <TableCell className="font-medium">{category}</TableCell>
                  <TableCell>{subcategory}</TableCell>
                  <TableCell className="text-right font-semibold">${cost.toLocaleString()}</TableCell>
                  <TableCell className="text-right">${Math.round(cost / (studyDesign.patient_count || 300)).toLocaleString()}</TableCell>
                </TableRow>
              ))
            )}
            <TableRow className="bg-muted/50 font-semibold">
              <TableCell colSpan={2}>Total</TableCell>
              <TableCell className="text-right">${totalCost.toLocaleString()}</TableCell>
              <TableCell className="text-right">${costPerPatient.toLocaleString()}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>

      {/* Recommendations */}
      {budgetData.recommendations && budgetData.recommendations.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-foreground">Budget Optimization Recommendations</h3>
          <ul className="space-y-2">
            {budgetData.recommendations.map((recommendation: string, index: number) => (
              <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className="text-primary font-bold">{index + 1}.</span>
                <span>{recommendation}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
