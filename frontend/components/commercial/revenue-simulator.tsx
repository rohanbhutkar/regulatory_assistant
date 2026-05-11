"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import type { RevenueSimulation } from "@/lib/types/commercial-types"
import { Play, Download } from "lucide-react"

interface RevenueSimulatorProps {
  simulation: RevenueSimulation
  onSimulationChange: (simulation: RevenueSimulation) => void
  onRunSimulation: () => void
}

export function RevenueSimulator({ simulation, onSimulationChange, onRunSimulation }: RevenueSimulatorProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)
  }

  const updatePricing = (field: keyof typeof simulation.pricing, value: number) => {
    onSimulationChange({
      ...simulation,
      pricing: { ...simulation.pricing, [field]: value },
    })
  }

  const updateCoverage = (field: keyof typeof simulation.coverage, value: number) => {
    onSimulationChange({
      ...simulation,
      coverage: { ...simulation.coverage, [field]: value },
    })
  }

  const updatePopulation = (field: keyof typeof simulation.patientPopulation, value: number) => {
    onSimulationChange({
      ...simulation,
      patientPopulation: { ...simulation.patientPopulation, [field]: value },
    })
  }

  const handleExport = () => {
    const exportData = {
      assetName: simulation.assetName,
      indication: simulation.indication,
      pricing: simulation.pricing,
      coverage: simulation.coverage,
      patientPopulation: simulation.patientPopulation,
      revenueCurve: simulation.revenueCurve,
      sensitivityAnalysis: simulation.sensitivityAnalysis,
      exportDate: new Date().toISOString(),
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `revenue-simulation-${simulation.assetName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-foreground">{simulation.assetName}</h2>
          <p className="text-sm sm:text-base text-muted-foreground">{simulation.indication}</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={onRunSimulation} className="gap-2 bg-gradient-to-r from-emerald-500 to-teal-500">
            <Play className="h-4 w-4" />
            <span className="hidden sm:inline">Run Simulation</span>
            <span className="sm:hidden">Run</span>
          </Button>
          <Button variant="outline" className="gap-2 bg-transparent" onClick={handleExport}>
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Export</span>
          </Button>
        </div>
      </div>

      {/* Input Parameters */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Pricing Assumptions */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Pricing Assumptions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="listPrice">List Price</Label>
              <Input
                id="listPrice"
                type="number"
                value={simulation.pricing.listPrice}
                onChange={(e) => updatePricing("listPrice", Number(e.target.value))}
                className="bg-card border-border/50"
              />
              <p className="text-xs text-muted-foreground">{formatCurrency(simulation.pricing.listPrice)}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="discountRate">Discount Rate (%)</Label>
              <Slider
                id="discountRate"
                value={[simulation.pricing.discountRate]}
                onValueChange={([value]) => updatePricing("discountRate", value)}
                min={0}
                max={50}
                step={1}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">{simulation.pricing.discountRate}%</p>
            </div>

            <div className="space-y-2">
              <Label>Net Price (Calculated)</Label>
              <div className="text-2xl font-bold text-foreground">
                {formatCurrency(simulation.pricing.listPrice * (1 - simulation.pricing.discountRate / 100))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Coverage Assumptions */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Coverage Assumptions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="commercialCoverage">Commercial Coverage (%)</Label>
              <Slider
                id="commercialCoverage"
                value={[simulation.coverage.commercialCoverage]}
                onValueChange={([value]) => updateCoverage("commercialCoverage", value)}
                min={0}
                max={100}
                step={5}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">{simulation.coverage.commercialCoverage}%</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="medicareCoverage">Medicare Coverage (%)</Label>
              <Slider
                id="medicareCoverage"
                value={[simulation.coverage.medicareCoverage]}
                onValueChange={([value]) => updateCoverage("medicareCoverage", value)}
                min={0}
                max={100}
                step={5}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">{simulation.coverage.medicareCoverage}%</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="medicaidCoverage">Medicaid Coverage (%)</Label>
              <Slider
                id="medicaidCoverage"
                value={[simulation.coverage.medicaidCoverage]}
                onValueChange={([value]) => updateCoverage("medicaidCoverage", value)}
                min={0}
                max={100}
                step={5}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">{simulation.coverage.medicaidCoverage}%</p>
            </div>
          </CardContent>
        </Card>

        {/* Population Assumptions */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Population Assumptions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="totalEligible">Total Eligible Population</Label>
              <Input
                id="totalEligible"
                type="number"
                value={simulation.patientPopulation.totalEligible}
                onChange={(e) => updatePopulation("totalEligible", Number(e.target.value))}
                className="bg-card border-border/50"
              />
              <p className="text-xs text-muted-foreground">
                {simulation.patientPopulation.totalEligible.toLocaleString()} patients
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="marketPenetration">Market Penetration (%)</Label>
              <Slider
                id="marketPenetration"
                value={[simulation.patientPopulation.marketPenetration]}
                onValueChange={([value]) => updatePopulation("marketPenetration", value)}
                min={0}
                max={50}
                step={1}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">{simulation.patientPopulation.marketPenetration}%</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="adherenceRate">Adherence Rate (%)</Label>
              <Slider
                id="adherenceRate"
                value={[simulation.patientPopulation.adherenceRate]}
                onValueChange={([value]) => updatePopulation("adherenceRate", value)}
                min={0}
                max={100}
                step={5}
                className="py-4"
              />
              <p className="text-xs text-muted-foreground">{simulation.patientPopulation.adherenceRate}%</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
