"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Sparkles, Loader2, Play, Plus, Trash2, TrendingUp, TrendingDown, Download, FileSpreadsheet, FileText } from 'lucide-react'
import { toast } from 'sonner'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { InlineActivityIndicator } from '@/components/activity/inline-activity-indicator'
import { ReportGenerator } from './report-generator'
import { ScenarioComparisonDialog } from './scenario-comparison-dialog'

interface ScenarioTabProps {
  assetId: string
  market: string
  asset?: {
    asset_name?: string
    indication?: string
    therapeutic_area?: string
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface Scenario {
  scenario_id?: string
  name: string
  description?: string
  parameters: {
    list_price?: number
    discount_pct?: number
    uptake_archetype?: string
    hta_outcome?: string
    units?: number
    launch_date?: string
  }
  results?: any
}

export function ScenarioTab({ assetId, market, asset }: ScenarioTabProps) {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [comparisonResults, setComparisonResults] = useState<any>(null)
  const [monteCarloResults, setMonteCarloResults] = useState<any>(null)
  const [sensitivityResults, setSensitivityResults] = useState<any>(null)
  const [selectedScenarios, setSelectedScenarios] = useState<Set<string>>(new Set())

  // Load scenarios on mount
  useEffect(() => {
    loadScenarios()
  }, [assetId])

  const loadScenarios = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/?asset_id=${assetId}`)
      if (response.ok) {
        const data = await response.json()
        setScenarios(data.scenarios || [])
      }
    } catch (error) {
      console.error('Failed to load scenarios:', error)
    }
  }

  const createNewScenario = () => {
    const newScenario: Scenario = {
      name: `Scenario ${scenarios.length + 1}`,
      description: '',
      parameters: {
        list_price: 100000,
        discount_pct: 0,
        uptake_archetype: 'moderate',
        hta_outcome: 'approval',
        units: 1000
      }
    }
    setSelectedScenario(newScenario)
    setIsCreating(true)
  }

  const saveScenario = async (scenario: Scenario) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...scenario,
          asset_id: assetId,
          market: market
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        toast.success('Scenario saved successfully')
        setIsCreating(false)
        setSelectedScenario(null)
        loadScenarios()
      } else {
        toast.error('Failed to save scenario')
      }
    } catch (error) {
      console.error('Failed to save scenario:', error)
      toast.error('Failed to save scenario')
    }
  }

  const runScenario = async (scenarioId: string) => {
    setIsRunning(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/${scenarioId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset_id: assetId })
      })
      
      if (response.ok) {
        const data = await response.json()
        toast.success('Scenario run completed')
        // Update scenario with results
        setScenarios(prev => prev.map(s => 
          s.scenario_id === scenarioId ? { ...s, results: data } : s
        ))
        setSelectedScenario(prev => prev?.scenario_id === scenarioId ? { ...prev, results: data } : prev)
      } else {
        toast.error('Failed to run scenario')
      }
    } catch (error) {
      console.error('Failed to run scenario:', error)
      toast.error('Failed to run scenario')
    } finally {
      setIsRunning(false)
    }
  }

  const runMonteCarlo = async () => {
    setIsRunning(true)
    try {
      // Get suggested parameters first
      const suggestResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/suggest-parameters/${assetId}?market=${market}`)
      let suggestedParams = null
      if (suggestResponse.ok) {
        const suggestData = await suggestResponse.json()
        suggestedParams = suggestData.suggested_parameters
      }

      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/monte-carlo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          base_scenario: {
            list_price: 100000,
            discount_pct: 0,
            uptake_archetype: 'moderate',
            hta_outcome: 'approval',
            units: 1000
          },
          uncertain_parameters: suggestedParams,
          iterations: 5000,
          use_data_driven: true
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setMonteCarloResults(data)
        toast.success('Monte Carlo simulation completed')
      } else {
        toast.error('Failed to run Monte Carlo simulation')
      }
    } catch (error) {
      console.error('Failed to run Monte Carlo:', error)
      toast.error('Failed to run Monte Carlo simulation')
    } finally {
      setIsRunning(false)
    }
  }

  const runSensitivityAnalysis = async () => {
    setIsRunning(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/sensitivity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          base_scenario: {
            list_price: 100000,
            discount_pct: 0,
            uptake_archetype: 'moderate',
            hta_outcome: 'approval',
            units: 1000
          },
          parameters: ['list_price', 'discount_pct', 'units'],
          target_metric: 'npv'
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setSensitivityResults(data)
        toast.success('Sensitivity analysis completed')
      } else {
        toast.error('Failed to run sensitivity analysis')
      }
    } catch (error) {
      console.error('Failed to run sensitivity analysis:', error)
      toast.error('Failed to run sensitivity analysis')
    } finally {
      setIsRunning(false)
    }
  }

  const compareScenarios = async (scenario1Id: string, scenario2Id: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_scenario_id: scenario1Id,
          comparison_scenario_id: scenario2Id
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setComparisonResults(data)
        toast.success('Scenarios compared')
      } else {
        toast.error('Failed to compare scenarios')
      }
    } catch (error) {
      console.error('Failed to compare scenarios:', error)
      toast.error('Failed to compare scenarios')
    }
  }

  const deleteScenario = async (scenarioId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/${scenarioId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        toast.success('Scenario deleted')
        loadScenarios()
        setSelectedScenarios(prev => {
          const next = new Set(prev)
          next.delete(scenarioId)
          return next
        })
      } else {
        toast.error('Failed to delete scenario')
      }
    } catch (error) {
      console.error('Failed to delete scenario:', error)
      toast.error('Failed to delete scenario')
    }
  }

  const bulkDeleteScenarios = async () => {
    if (selectedScenarios.size === 0) {
      toast.error('No scenarios selected')
      return
    }
    
    try {
      const deletePromises = Array.from(selectedScenarios).map(id => 
        fetch(`${API_BASE_URL}/api/asset-strategy/scenarios/${id}`, { method: 'DELETE' })
      )
      
      await Promise.all(deletePromises)
      toast.success(`Deleted ${selectedScenarios.size} scenario(s)`)
      setSelectedScenarios(new Set())
      loadScenarios()
    } catch (error) {
      console.error('Failed to delete scenarios:', error)
      toast.error('Failed to delete scenarios')
    }
  }

  const exportScenarios = async (format: 'json' | 'csv' = 'json') => {
    try {
      const scenariosToExport = scenarios.filter(s => 
        selectedScenarios.size === 0 || selectedScenarios.has(s.scenario_id!)
      )
      
      if (scenariosToExport.length === 0) {
        toast.error('No scenarios to export')
        return
      }
      
      if (format === 'json') {
        const dataStr = JSON.stringify(scenariosToExport, null, 2)
        const dataBlob = new Blob([dataStr], { type: 'application/json' })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `scenarios-${assetId}-${new Date().toISOString().split('T')[0]}.json`
        link.click()
        URL.revokeObjectURL(url)
        toast.success(`Exported ${scenariosToExport.length} scenario(s) as JSON`)
      } else if (format === 'csv') {
        // Convert to CSV
        const headers = ['Name', 'Description', 'List Price', 'Discount %', 'Uptake', 'HTA Outcome', 'NPV', 'Peak Sales']
        const rows = scenariosToExport.map(s => [
          s.name,
          s.description || '',
          s.parameters.list_price || 0,
          s.parameters.discount_pct || 0,
          s.parameters.uptake_archetype || '',
          s.parameters.hta_outcome || '',
          s.results?.results?.npv || 0,
          s.results?.results?.peak_sales || 0
        ])
        
        const csvContent = [
          headers.join(','),
          ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n')
        
        const dataBlob = new Blob([csvContent], { type: 'text/csv' })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `scenarios-${assetId}-${new Date().toISOString().split('T')[0]}.csv`
        link.click()
        URL.revokeObjectURL(url)
        toast.success(`Exported ${scenariosToExport.length} scenario(s) as CSV`)
      }
    } catch (error) {
      console.error('Failed to export scenarios:', error)
      toast.error('Failed to export scenarios')
    }
  }

  const toggleScenarioSelection = (scenarioId: string) => {
    setSelectedScenarios(prev => {
      const next = new Set(prev)
      if (next.has(scenarioId)) {
        next.delete(scenarioId)
      } else {
        next.add(scenarioId)
      }
      return next
    })
  }

  const selectAllScenarios = () => {
    setSelectedScenarios(new Set(scenarios.map(s => s.scenario_id!).filter(Boolean)))
  }

  const clearSelection = () => {
    setSelectedScenarios(new Set())
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">Scenario Planning & Simulation</h3>
          <p className="text-sm text-muted-foreground">What-if analysis, sensitivity, and Monte Carlo simulations</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button onClick={createNewScenario} className="gap-2">
            <Plus className="h-4 w-4" />
            New Scenario
          </Button>
          <Button onClick={runMonteCarlo} disabled={isRunning} variant="outline" className="gap-2">
            {isRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Monte Carlo
          </Button>
          <Button onClick={runSensitivityAnalysis} disabled={isRunning} variant="outline" className="gap-2">
            {isRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <TrendingUp className="h-4 w-4" />
            )}
            Sensitivity
          </Button>
          {scenarios.length > 0 && (
            <>
              <Button 
                onClick={() => exportScenarios('json')} 
                variant="outline" 
                className="gap-2"
                disabled={isRunning}
              >
                <Download className="h-4 w-4" />
                Export JSON
              </Button>
              <Button 
                onClick={() => exportScenarios('csv')} 
                variant="outline" 
                className="gap-2"
                disabled={isRunning}
              >
                <FileSpreadsheet className="h-4 w-4" />
                Export CSV
              </Button>
              {selectedScenarios.size > 0 && (
                <Button 
                  onClick={bulkDeleteScenarios} 
                  variant="destructive" 
                  className="gap-2"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete ({selectedScenarios.size})
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      <InlineActivityIndicator
        operationType="scenario_calc"
        context={{ assetId, tab: 'scenarios' }}
      />

      {/* Create/Edit Scenario Form */}
      {isCreating && selectedScenario && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Scenario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Scenario Name</Label>
              <Input
                value={selectedScenario.name}
                onChange={(e) => setSelectedScenario({ ...selectedScenario, name: e.target.value })}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Input
                value={selectedScenario.description || ''}
                onChange={(e) => setSelectedScenario({ ...selectedScenario, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>List Price</Label>
                <Input
                  type="number"
                  value={selectedScenario.parameters.list_price}
                  onChange={(e) => setSelectedScenario({
                    ...selectedScenario,
                    parameters: { ...selectedScenario.parameters, list_price: parseFloat(e.target.value) }
                  })}
                />
              </div>
              <div>
                <Label>Discount %</Label>
                <Input
                  type="number"
                  value={selectedScenario.parameters.discount_pct}
                  onChange={(e) => setSelectedScenario({
                    ...selectedScenario,
                    parameters: { ...selectedScenario.parameters, discount_pct: parseFloat(e.target.value) }
                  })}
                />
              </div>
              <div>
                <Label>Uptake Archetype</Label>
                <Select
                  value={selectedScenario.parameters.uptake_archetype}
                  onValueChange={(value) => setSelectedScenario({
                    ...selectedScenario,
                    parameters: { ...selectedScenario.parameters, uptake_archetype: value }
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="slow">Slow</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="fast">Fast</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>HTA Outcome</Label>
                <Select
                  value={selectedScenario.parameters.hta_outcome}
                  onValueChange={(value) => setSelectedScenario({
                    ...selectedScenario,
                    parameters: { ...selectedScenario.parameters, hta_outcome: value }
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="approval">Approval</SelectItem>
                    <SelectItem value="restriction">Restriction</SelectItem>
                    <SelectItem value="rejection">Rejection</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => saveScenario(selectedScenario)}>Save Scenario</Button>
              <Button variant="outline" onClick={() => { setIsCreating(false); setSelectedScenario(null) }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bulk Selection Controls */}
      {scenarios.length > 0 && (
        <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={selectAllScenarios}
            >
              Select All
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={clearSelection}
            >
              Clear Selection
            </Button>
            {selectedScenarios.size > 0 && (
              <span className="text-sm text-muted-foreground">
                {selectedScenarios.size} selected
              </span>
            )}
          </div>
        </div>
      )}

      {/* Scenarios List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {scenarios.map((scenario) => {
          const scenarioId = scenario.scenario_id || `scenario-${scenarios.indexOf(scenario)}`
          return (
          <Card 
            key={scenarioId}
            className={selectedScenarios.has(scenarioId) ? 'ring-2 ring-primary' : ''}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedScenarios.has(scenarioId)}
                    onChange={() => toggleScenarioSelection(scenarioId)}
                    className="h-4 w-4"
                  />
                  <CardTitle className="text-lg">{scenario.name}</CardTitle>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => runScenario(scenarioId)}
                    disabled={isRunning}
                  >
                    <Play className="h-3 w-3" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => deleteScenario(scenarioId)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              {scenario.description && (
                <CardDescription>{scenario.description}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">List Price:</span>
                  <span>${scenario.parameters.list_price?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Discount:</span>
                  <span>{scenario.parameters.discount_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Uptake:</span>
                  <Badge variant="outline">{scenario.parameters.uptake_archetype}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">HTA Outcome:</span>
                  <Badge variant="outline">{scenario.parameters.hta_outcome}</Badge>
                </div>
                {scenario.results && (
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">NPV:</span>
                      <span className="font-bold">${scenario.results.results?.npv?.toLocaleString() || '0'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Peak Sales:</span>
                      <span className="font-bold">${scenario.results.results?.peak_sales?.toLocaleString() || '0'}</span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
          )
        })}
      </div>

      {scenarios.length === 0 && !isCreating && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>No scenarios created yet</p>
            <p className="text-sm mt-2">Click "New Scenario" to create your first scenario</p>
          </CardContent>
        </Card>
      )}

      {/* Monte Carlo Results */}
      {monteCarloResults && (
        <Card>
          <CardHeader>
            <CardTitle>Monte Carlo Simulation Results</CardTitle>
            <CardDescription>
              {monteCarloResults.iterations || 5000} iterations with data-driven parameter distributions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div>
                <p className="text-sm text-muted-foreground">P10 NPV</p>
                <p className="text-2xl font-bold">${(monteCarloResults.npv_p10 || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">P50 NPV</p>
                <p className="text-2xl font-bold">${(monteCarloResults.npv_p50 || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">P90 NPV</p>
                <p className="text-2xl font-bold">${(monteCarloResults.npv_p90 || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Success Probability</p>
                <p className="text-2xl font-bold">
                  {((monteCarloResults.success_probability || 0) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
            {monteCarloResults.data_sources_used && monteCarloResults.data_sources_used.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground mb-2">Data Sources Used:</p>
                <div className="flex flex-wrap gap-2">
                  {monteCarloResults.data_sources_used.map((source: string) => (
                    <Badge key={source} variant="secondary">{source}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Sensitivity Analysis Results */}
      {sensitivityResults && (
        <Card>
          <CardHeader>
            <CardTitle>Sensitivity Analysis Results</CardTitle>
            <CardDescription>Impact of parameter changes on NPV</CardDescription>
          </CardHeader>
          <CardContent>
            {sensitivityResults.sensitivity && (
              <div className="space-y-4">
                {Object.entries(sensitivityResults.sensitivity).map(([param, impact]: [string, any]) => (
                  <div key={param}>
                    <div className="flex justify-between mb-2">
                      <span className="font-medium">{param}</span>
                      <span className={impact > 0 ? 'text-green-600' : 'text-red-600'}>
                        {impact > 0 ? <TrendingUp className="h-4 w-4 inline" /> : <TrendingDown className="h-4 w-4 inline" />}
                        {Math.abs(impact).toFixed(2)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${impact > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(Math.abs(impact) * 10, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Report Generator */}
      <ReportGenerator assetId={assetId} />
    </div>
  )
}
