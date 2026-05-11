import { useState } from 'react'
import { useAnalysisAPI } from '@/lib/hooks/use-analysis-api'
import { toast } from 'sonner'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface SimulationProgress {
  step: string
  progress: number
}

interface QuarterlyRevenue {
  quarter: number
  quarter_in_year: number
  year: number
  revenue: number
}

interface PatientFunnel {
  total_population: number
  indication_prevalence: number
  diagnosis_rate: number
  treatment_rate: number
  final_patient_count: number
}

interface SimulationResults {
  quarterly_revenue: QuarterlyRevenue[]
  peak_revenue: number
  total_revenue: number
  patient_funnel?: PatientFunnel
  [key: string]: unknown
}

export function RevenueSimulationEngine() {
  const { runSimulation } = useAnalysisAPI()
  const [simulationParams, setSimulationParams] = useState({
    tppParameters: {
      indication: 'Oncology',
      targetPopulation: 1000,
      launchTiming: '2024-06-01',
      pricing: 1500,
      competitiveLandscape: ['Competitor A', 'Competitor B']
    },
    payerSplit: {
      commercial: 0.4,
      medicare: 0.35,
      medicaid: 0.25,
    },
    coverageAssumptions: {
      commercialCoverage: 0.8,
      medicareCoverage: 0.9,
      medicaidCoverage: 0.7,
      timeToCoverage: 12
    },
    patientFunnel: {
      totalPopulation: 100000,
      indicationPrevalence: 0.05,
      diagnosisRate: 0.8,
      treatmentRate: 0.6,
      adherenceRate: 0.85
    }
  })
  
  const [simulationResults, setSimulationResults] = useState<SimulationResults | null>(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const [simulationProgress, setSimulationProgress] = useState<SimulationProgress | null>(null)
  
  const runRevenueSimulation = async () => {
    setIsSimulating(true)
    setSimulationProgress({ step: 'Initializing', progress: 0 })
    
    try {
      // Update progress
      setSimulationProgress({ step: 'Running simulation', progress: 50 })
      
      const response = await fetch(`${API_BASE_URL}/api/commercial/revenue-simulation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(simulationParams)
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data && data.quarterly_revenue) {
        // Transform the response data to match our expected format
        const results: SimulationResults = {
          quarterly_revenue: data.quarterly_revenue,
          total_revenue: data.total_revenue,
          peak_revenue: data.peak_revenue,
          ...data
        }
        
        setSimulationResults(results)
        toast.success('Revenue simulation completed successfully')
      } else {
        toast.error('Revenue simulation failed. Please try again.')
      }
    } catch (error) {
      console.error('Revenue simulation failed:', error)
      toast.error('Revenue simulation failed')
    } finally {
      setIsSimulating(false)
      setSimulationProgress(null)
    }
  }
  
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* TPP Parameters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Target Product Profile</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Indication</label>
            <input
              type="text"
              value={simulationParams.tppParameters.indication}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                tppParameters: { ...prev.tppParameters, indication: e.target.value }
              }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target Population</label>
            <input
              type="number"
              value={simulationParams.tppParameters.targetPopulation}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                tppParameters: { ...prev.tppParameters, targetPopulation: Number(e.target.value) }
              }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Launch Price ($)</label>
            <input
              type="number"
              value={simulationParams.tppParameters.pricing}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                tppParameters: { ...prev.tppParameters, pricing: Number(e.target.value) }
              }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Launch Timing</label>
            <input
              type="date"
              value={simulationParams.tppParameters.launchTiming}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                tppParameters: { ...prev.tppParameters, launchTiming: e.target.value }
              }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
            />
          </div>
        </div>
      </div>
      
      {/* Payer Split */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Payer Split</h3>
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <label className="w-24 text-sm font-medium text-gray-700">Commercial</label>
            <input
              type="range"
              min="0"
              max="100"
              value={simulationParams.payerSplit.commercial * 100}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                payerSplit: { ...prev.payerSplit, commercial: Number(e.target.value) / 100 }
              }))}
              className="flex-1"
            />
            <span className="w-12 text-sm text-gray-900">{Math.round(simulationParams.payerSplit.commercial * 100)}%</span>
          </div>
          <div className="flex items-center space-x-4">
            <label className="w-24 text-sm font-medium text-gray-700">Medicare</label>
            <input
              type="range"
              min="0"
              max="100"
              value={simulationParams.payerSplit.medicare * 100}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                payerSplit: { ...prev.payerSplit, medicare: Number(e.target.value) / 100 }
              }))}
              className="flex-1"
            />
            <span className="w-12 text-sm text-gray-900">{Math.round(simulationParams.payerSplit.medicare * 100)}%</span>
          </div>
          <div className="flex items-center space-x-4">
            <label className="w-24 text-sm font-medium text-gray-700">Medicaid</label>
            <input
              type="range"
              min="0"
              max="100"
              value={simulationParams.payerSplit.medicaid * 100}
              onChange={(e) => setSimulationParams(prev => ({
                ...prev,
                payerSplit: { ...prev.payerSplit, medicaid: Number(e.target.value) / 100 }
              }))}
              className="flex-1"
            />
            <span className="w-12 text-sm text-gray-900">{Math.round(simulationParams.payerSplit.medicaid * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Simulation Progress */}
      {simulationProgress && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Simulation Progress</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">{simulationProgress.step}</span>
              <span className="text-gray-900">{simulationProgress.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${simulationProgress.progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600">{simulationProgress.step}</p>
          </div>
        </div>
      )}
      
      {/* Revenue Results */}
      {simulationResults && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Revenue Projection</h3>
          
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-gray-900">{formatCurrency(simulationResults.total_revenue)}</div>
              <div className="text-sm text-gray-600">Total Revenue</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-600">{formatCurrency(simulationResults.peak_revenue)}</div>
              <div className="text-sm text-gray-600">Peak Revenue</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">{simulationResults.quarterly_revenue.length}</div>
              <div className="text-sm text-gray-600">Quarters to Peak</div>
            </div>
          </div>

          {/* Quarterly Revenue Chart */}
          <div className="mb-6">
            <h4 className="text-md font-medium text-gray-900 mb-3">Quarterly Revenue Projection</h4>
            <div className="space-y-2">
              {simulationResults.quarterly_revenue.map((quarter: QuarterlyRevenue) => (
                <div key={quarter.quarter} className="flex items-center space-x-4">
                  <div className="w-16 text-sm text-gray-600">Q{quarter.quarter_in_year} Y{quarter.year}</div>
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div 
                      className="bg-blue-600 h-4 rounded-full"
                      style={{ width: `${(quarter.revenue / simulationResults.peak_revenue) * 100}%` }}
                    />
                  </div>
                  <div className="w-24 text-sm font-medium text-gray-900">{formatCurrency(quarter.revenue)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Patient Funnel */}
          {simulationResults.patient_funnel && (
            <div className="mb-6">
              <h4 className="text-md font-medium text-gray-900 mb-3">Patient Funnel</h4>
              <div className="grid grid-cols-5 gap-2">
                <div className="text-center">
                  <div className="text-lg font-bold text-gray-900">{simulationResults.patient_funnel.total_population.toLocaleString()}</div>
                  <div className="text-xs text-gray-600">Total Population</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-gray-900">{(simulationResults.patient_funnel.total_population * simulationResults.patient_funnel.indication_prevalence).toLocaleString()}</div>
                  <div className="text-xs text-gray-600">Indication</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-gray-900">{(simulationResults.patient_funnel.total_population * simulationResults.patient_funnel.indication_prevalence * simulationResults.patient_funnel.diagnosis_rate).toLocaleString()}</div>
                  <div className="text-xs text-gray-600">Diagnosed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-gray-900">{(simulationResults.patient_funnel.total_population * simulationResults.patient_funnel.indication_prevalence * simulationResults.patient_funnel.diagnosis_rate * simulationResults.patient_funnel.treatment_rate).toLocaleString()}</div>
                  <div className="text-xs text-gray-600">Treated</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-green-600">{simulationResults.patient_funnel.final_patient_count.toLocaleString()}</div>
                  <div className="text-xs text-gray-600">Adherent</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      <button 
        onClick={runRevenueSimulation}
        disabled={isSimulating}
        className="w-full py-3 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
      >
        {isSimulating ? 'Running Simulation...' : 'Generate Revenue Curve'}
      </button>
    </div>
  )
}















