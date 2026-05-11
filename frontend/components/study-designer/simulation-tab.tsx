"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { SimulationResult } from "@/lib/types/study-types"
import { PlayCircle, Calendar, CheckCircle2, Clock } from "lucide-react"
import { EnrollmentCurveChart } from "./enrollment-curve-chart"
import { useAnalysisAPI } from "@/lib/hooks/use-analysis-api"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { toast } from "sonner"

interface SimulationTabProps {
  simulation?: SimulationResult | null
  onSimulationChange?: (simulation: SimulationResult) => void
  studyDesign?: any
  sites?: any[]
}

export function SimulationTab({ simulation: propsSimulation, onSimulationChange: propsOnChange, studyDesign: propsStudyDesign, sites: propsSites }: SimulationTabProps = {}) {
  // Use context data with props as fallback
  const {
    simulation: contextSimulation,
    setSimulation: setContextSimulation,
    selectedSites: contextSites,
    studyDesign: contextStudyDesign,
    indication,
    phase,
    isLoading: contextLoading
  } = useStudyDesigner()
  
  // Use context data if available, otherwise use props
  const simulation = propsSimulation !== undefined ? propsSimulation : contextSimulation
  const studyDesign = propsStudyDesign !== undefined ? propsStudyDesign : contextStudyDesign
  const sites = propsSites !== undefined ? propsSites : contextSites
  
  const { runSimulation, isLoading, error } = useAnalysisAPI()
  
  console.log("🔍 Simulation Tab:", {
    contextSimulation: !!contextSimulation,
    propsSimulation: !!propsSimulation,
    usingContext: propsSimulation === undefined,
    indication,
    phase,
    sitesCount: sites.length
  })

  const handleRunSimulation = async () => {
    try {
      const request = {
        study_design: studyDesign,
        sites: sites,
        enrollment_target: studyDesign.enrollment_target || 300,
        timeline_months: studyDesign.timeline_months || 24,
        budget_constraints: studyDesign.budget_constraints
      }

      const response = await runSimulation(request)

      if (response && response.success) {
        const newSimulation: SimulationResult = {
          id: `sim-${Date.now()}`,
          enrollmentCurve: response.enrollment_curve.map((point: any) => ({
            month: point.month,
            enrolled: point.enrolled,
            projected: point.projected,
          })),
          milestones: response.milestones.map((milestone: any) => ({
            name: milestone.name,
            date: new Date(milestone.date),
            status: milestone.status as "pending" | "completed",
          })),
          riskAssessment: response.risk_assessment,
        budgetProjection: response.budget_projection,
        successProbability: response.success_probability,
      }
      
      // Use context or props method
      if (propsOnChange) {
        propsOnChange(newSimulation)
      } else {
        setContextSimulation(newSimulation)
      }
      toast.success('Simulation completed successfully!')
    } else {
      toast.error('Simulation failed. Please try again.')
    }
    } catch (err) {
      console.error('Error running simulation:', err)
      toast.error('Error running simulation. Please try again.')
    }
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Study Startup Simulation</h2>
          <p className="text-muted-foreground">Model enrollment timelines and identify potential risks</p>
        </div>
        <Button onClick={handleRunSimulation} disabled={isLoading} className="gap-2">
          <PlayCircle className="h-4 w-4" />
          {isLoading ? 'Running Simulation...' : 'Run Simulation'}
        </Button>
      </div>

      {simulation ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="p-6">
              <div className="text-sm text-muted-foreground mb-2">Success Probability</div>
              <div className="text-3xl font-bold text-success">{simulation.successProbability}%</div>
            </Card>
            <Card className="p-6">
              <div className="text-sm text-muted-foreground mb-2">Budget Projection</div>
              <div className="text-3xl font-bold text-foreground">
                ${(simulation.budgetProjection / 1000000).toFixed(1)}M
              </div>
            </Card>
            <Card className="p-6">
              <div className="text-sm text-muted-foreground mb-2">Risk Assessment</div>
              <Badge
                variant={simulation.riskAssessment === "Low" ? "default" : "secondary"}
                className="text-lg px-3 py-1"
              >
                {simulation.riskAssessment}
              </Badge>
            </Card>
          </div>

          {/* Timeline */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-6 text-foreground">Study Timeline & Milestones</h3>
            <div className="space-y-4">
              {simulation.milestones && simulation.milestones.length > 0 ? (
                simulation.milestones.map((milestone, index) => (
                  <div key={index} className="flex items-center gap-4 p-4 rounded-lg bg-muted/30 border border-border/50">
                    <div className="flex-shrink-0">
                      {milestone.status === "completed" ? (
                        <CheckCircle2 className="h-6 w-6 text-success" />
                      ) : (
                        <Clock className="h-6 w-6 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-foreground">{milestone.name}</div>
                      <div className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
                        <Calendar className="h-3 w-3" />
                        {milestone.date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
                      </div>
                    </div>
                    <Badge variant={milestone.status === "completed" ? "default" : "secondary"}>{milestone.status}</Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No milestones available</p>
              )}
            </div>
          </Card>

          {/* Enrollment Curve Chart */}
          <EnrollmentCurveChart simulation={simulation} />
        </>
      ) : (
        <Card className="p-12">
          <div className="text-center space-y-4">
            <PlayCircle className="h-16 w-16 text-muted-foreground mx-auto" />
            <h3 className="text-xl font-semibold text-foreground">No Simulation Run Yet</h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              Run a simulation to model enrollment timelines, identify risks, and optimize your study startup strategy.
            </p>
            <Button onClick={handleRunSimulation} size="lg" className="gap-2" disabled={isLoading}>
              <PlayCircle className="h-5 w-5" />
              {isLoading ? 'Running Simulation...' : 'Run Your First Simulation'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
