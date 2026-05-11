import { useState } from 'react'
import { Trial } from '@/lib/types/trial-types'

interface TrialDesignWorkspaceProps {
  trial: Trial
  onClose: () => void
  onSave: (trial: Trial) => void
}

export function TrialDesignWorkspace({ trial, onClose, onSave }: TrialDesignWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<string>("reference_trials")
  const [trialData, setTrialData] = useState<Trial>(trial)
  const [isDirty, setIsDirty] = useState(false)
  
  const tabs = [
    { id: "reference_trials", label: "Reference Trials", icon: "📄" },
    { id: "protocol_synopsis", label: "Protocol Synopsis", icon: "📋" },
    { id: "ie_criteria", label: "IE Criteria", icon: "🔍" },
    { id: "site_selection", label: "Site Selection", icon: "📍" },
    { id: "startup_simulation", label: "Startup Simulation", icon: "▶️" },
    { id: "budget_calculation", label: "Budget Calculation", icon: "💰" },
  ]
  
  const handleSave = () => {
    onSave(trialData)
    setIsDirty(false)
  }

  const handleExport = (format: 'pdf' | 'docx') => {
    console.log(`Exporting trial ${trialData.id} as ${format}`)
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case "reference_trials":
        return (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Reference Trials</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-600">Search and select reference trials to inform your protocol design.</p>
              <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                Search Trials
              </button>
            </div>
          </div>
        )
      case "protocol_synopsis":
        return (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Protocol Synopsis</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Protocol Title</label>
                <input
                  type="text"
                  value={trialData.title}
                  onChange={(e) => {
                    setTrialData({...trialData, title: e.target.value})
                    setIsDirty(true)
                  }}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Rationale</label>
                <textarea
                  rows={4}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  placeholder="Enter protocol rationale..."
                />
              </div>
            </div>
          </div>
        )
      case "ie_criteria":
        return (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Inclusion/Exclusion Criteria</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">Inclusion Criteria</h4>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm text-gray-700">Age ≥ 18 years</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm text-gray-700">Histologically confirmed diagnosis</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm text-gray-700">ECOG performance status 0-1</span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">Exclusion Criteria</h4>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm text-gray-700">Prior treatment with similar drugs</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm text-gray-700">Active infection</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm text-gray-700">Pregnancy or lactation</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      case "site_selection":
        return (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Site Selection</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-600">Select sites based on geographic distribution, patient population, and site capabilities.</p>
              <div className="mt-4 grid grid-cols-3 gap-4">
                <div className="bg-white rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-600">15</div>
                  <div className="text-sm text-gray-600">Selected Sites</div>
                </div>
                <div className="bg-white rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green-600">500</div>
                  <div className="text-sm text-gray-600">Target Patients</div>
                </div>
                <div className="bg-white rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-purple-600">3</div>
                  <div className="text-sm text-gray-600">Countries</div>
                </div>
              </div>
            </div>
          </div>
        )
      case "startup_simulation":
        return (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Study Startup Simulation</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-600">Run MCMC simulation to predict enrollment curves and key milestones.</p>
              <div className="mt-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Estimated Enrollment Time</span>
                  <span className="text-sm font-medium text-gray-900">18 months</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Success Probability</span>
                  <span className="text-sm font-medium text-green-600">78%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Key Risk Factors</span>
                  <span className="text-sm font-medium text-yellow-600">Regulatory delays</span>
                </div>
              </div>
            </div>
          </div>
        )
      case "budget_calculation":
        return (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Budget Calculation</h3>
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-600">Cost per Patient</span>
                  <span className="text-lg font-semibold text-gray-900">$25,000</span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-600">Total Cost</span>
                  <span className="text-lg font-semibold text-gray-900">$5,000,000</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Cost Breakdown</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Screening</span>
                      <span className="text-gray-900">$2,000</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Treatment</span>
                      <span className="text-gray-900">$15,000</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Follow-up</span>
                      <span className="text-gray-900">$5,000</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Overhead</span>
                      <span className="text-gray-900">$3,000</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Burden Analysis</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Patient Burden</span>
                      <span className="text-gray-900">7.5/10</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Caregiver Burden</span>
                      <span className="text-gray-900">6.2/10</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      default:
        return <div>Select a tab to get started</div>
    }
  }
  
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{trialData.title}</h1>
            <p className="text-muted-foreground">
              {trialData.phase} • {trialData.therapeutic_area}
            </p>
          </div>
          <div className="flex space-x-2">
            <button 
              onClick={() => handleExport('pdf')}
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              📄 Export PDF
            </button>
            <button 
              onClick={() => handleExport('docx')}
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              📄 Export DOCX
            </button>
            <button 
              onClick={handleSave} 
              disabled={!isDirty}
              className="inline-flex items-center px-3 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              💾 Save Changes
            </button>
            <button
              onClick={onClose}
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              ← Back
            </button>
          </div>
        </div>
      </div>
      
      {/* Tab Navigation */}
      <div className="border-b bg-white">
        <div className="px-6">
          <nav className="flex space-x-8">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="h-full">
          {renderTabContent()}
        </div>
      </div>
    </div>
  )
}






















