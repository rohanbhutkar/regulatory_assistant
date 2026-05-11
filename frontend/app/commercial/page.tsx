"use client"

import { useState } from "react"
import { Header } from "@/components/layout/header"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ModelList } from "@/components/commercial/model-list"
import { RevenueSimulator } from "@/components/commercial/revenue-simulator"
import { RevenueChart } from "@/components/commercial/revenue-chart"
import { PatientFunnelVisualization } from "@/components/commercial/patient-funnel"
import { SensitivityAnalysis } from "@/components/commercial/sensitivity-analysis"
import { ResearchAgentChat } from "@/components/chat/research-agent-chat"
import { MOCK_COMMERCIAL_MODELS, MOCK_PATIENT_FUNNEL } from "@/lib/data/mock-commercial"
import type { RevenueSimulation, CommercialModel } from "@/lib/types/commercial-types"
import { ArrowLeft, BarChart3 } from "lucide-react"
import { useRouter } from "next/navigation"

export default function CommercialPage() {
  const router = useRouter()
  const [selectedModel, setSelectedModel] = useState<CommercialModel | null>(null)
  const [simulation, setSimulation] = useState<RevenueSimulation | null>(null)

  const handleCreateNew = () => {
    const newModel: CommercialModel = {
      id: `model-${Date.now()}`,
      name: "New Commercial Model",
      assetName: "New Asset",
      indication: "",
      status: "draft",
      lastModified: new Date(),
      modifiedBy: "Current User",
      recentActivity: "Created",
      simulation: {
        id: `sim-${Date.now()}`,
        assetName: "New Asset",
        indication: "",
        launchDate: new Date(),
        pricing: {
          listPrice: 100000,
          netPrice: 70000,
          discountRate: 30,
        },
        coverage: {
          commercialCoverage: 70,
          medicareCoverage: 60,
          medicaidCoverage: 50,
          timeToMedicareCoverage: 12,
        },
        patientPopulation: {
          totalEligible: 30000,
          marketPenetration: 15,
          adherenceRate: 80,
          treatmentDuration: 12,
        },
        revenueCurve: [],
        sensitivityAnalysis: [],
      },
    }
    setSelectedModel(newModel)
    setSimulation(newModel.simulation)
  }

  const handleSelectModel = (model: CommercialModel) => {
    setSelectedModel(model)
    setSimulation(model.simulation)
  }

  const handleRunSimulation = () => {
    if (!simulation) return

    const netPrice = simulation.pricing.listPrice * (1 - simulation.pricing.discountRate / 100)
    const treatedPatients =
      simulation.patientPopulation.totalEligible *
      (simulation.patientPopulation.marketPenetration / 100) *
      (simulation.patientPopulation.adherenceRate / 100)

    // Recalculate revenue curve based on new parameters
    const newRevenueCurve = simulation.revenueCurve.map((quarter) => {
      const quarterMultiplier = Number(quarter.quarter) / 12 // Ramp up over time
      const revenue = netPrice * treatedPatients * quarterMultiplier
      return {
        ...quarter,
        revenue,
      }
    })

    setSimulation({
      ...simulation,
      revenueCurve: newRevenueCurve,
    })
  }

  if (selectedModel && simulation) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <Header />

        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="px-4 sm:px-6 lg:px-8 py-4 sm:py-6 border-b border-border/40 shrink-0">
            <Button
              variant="ghost"
              onClick={() => setSelectedModel(null)}
              className="mb-4 sm:mb-6 -ml-2 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Models
            </Button>

            <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight text-foreground mb-2">
                  {selectedModel.name}
                </h1>
                <p className="text-base sm:text-lg text-muted-foreground">
                  {selectedModel.assetName} • {selectedModel.indication}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Button variant="outline" size="sm">
                  Save Model
                </Button>
                <Button variant="outline" size="sm">
                  Export Analysis
                </Button>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <Tabs defaultValue="simulator" className="h-full flex flex-col min-h-0">
              <div className="px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 border-b border-border/40 overflow-x-auto">
                <TabsList className="bg-transparent border-b-0 p-0 h-auto inline-flex min-w-max">
                  <TabsTrigger
                    value="simulator"
                    className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                  >
                    Revenue Simulator
                  </TabsTrigger>
                  <TabsTrigger
                    value="analysis"
                    className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                  >
                    Analysis
                  </TabsTrigger>
                  <TabsTrigger
                    value="research"
                    className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 text-xs sm:text-sm whitespace-nowrap"
                  >
                    Research Agent
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="simulator" className="flex-1 overflow-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8 mt-0">
                <RevenueSimulator
                  simulation={simulation}
                  onSimulationChange={setSimulation}
                  onRunSimulation={handleRunSimulation}
                />
                <RevenueChart data={simulation.revenueCurve} />
              </TabsContent>

              <TabsContent value="analysis" className="flex-1 overflow-auto p-4 sm:p-6 space-y-6 mt-0">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <PatientFunnelVisualization funnel={MOCK_PATIENT_FUNNEL} />
                  <SensitivityAnalysis results={simulation.sensitivityAnalysis} />
                </div>
              </TabsContent>

              <TabsContent value="research" className="flex-1 min-h-0 overflow-hidden mt-0">
                <ResearchAgentChat />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Page Header */}
        <div className="p-6 border-b border-border/50 bg-card/30">
          <div className="flex items-center justify-between mb-4">
            <Button variant="ghost" onClick={() => router.push("/")} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Personas
            </Button>
          </div>

          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-muted/80 flex items-center justify-center">
              <BarChart3 className="h-6 w-6 text-foreground" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Commercial Simulation</h1>
              <p className="text-muted-foreground">Market analysis and revenue modeling workspace</p>
            </div>
          </div>
        </div>

        {/* Model List */}
        <div className="flex-1 overflow-auto p-6">
          <ModelList models={MOCK_COMMERCIAL_MODELS} onSelectModel={handleSelectModel} onCreateNew={handleCreateNew} />
        </div>
      </div>
    </div>
  )
}










