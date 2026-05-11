import { Asset } from '@/lib/types/asset-types'
import { formatDate } from '@/lib/utils/time'

interface AssetDetailsDrawerProps {
  asset: Asset
  isOpen: boolean
  onClose: () => void
}

export function AssetDetailsDrawer({ asset, isOpen, onClose }: AssetDetailsDrawerProps) {
  if (!isOpen) return null

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl bg-white shadow-xl">
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-gray-900">{asset.asset_name}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="space-y-6">
              {/* Asset Overview */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Asset Overview</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">Therapeutic Area</label>
                    <p className="text-sm text-gray-900">{asset.therapeutic_area}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Trial Phase</label>
                    <p className="text-sm text-gray-900">{asset.trial_phase}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Status</label>
                    <p className="text-sm text-gray-900">{asset.status}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Last Updated</label>
                    <p className="text-sm text-gray-900">{formatDate(new Date(asset.last_updated))}</p>
                  </div>
                </div>
              </div>

              {/* Financial Summary */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Financial Summary</h3>
                <div className="grid grid-cols-1 gap-4">
                  <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-600">Cost per Patient</span>
                    <span className="text-lg font-semibold text-gray-900">{formatCurrency(asset.cost_per_patient)}</span>
                  </div>
                  <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-600">Total Estimated Cost</span>
                    <span className="text-lg font-semibold text-gray-900">{formatCurrency(asset.total_estimated_cost)}</span>
                  </div>
                  <div className="flex justify-between items-center p-4 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-600">Projected Revenue</span>
                    <span className="text-lg font-semibold text-green-600">{formatCurrency(asset.projected_revenue)}</span>
                  </div>
                </div>
              </div>

              {/* Current Trials */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Current Trials</h3>
                {asset.current_trials.length > 0 ? (
                  <div className="space-y-2">
                    {asset.current_trials.map((trial) => (
                      <div key={trial.id} className="p-3 border border-gray-200 rounded-lg">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium text-gray-900">{trial.name}</span>
                          <span className="text-xs text-gray-500">{trial.id}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No active trials</p>
                )}
              </div>

              {/* Cost Breakdown */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Cost Breakdown</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Screening</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(2000)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Treatment</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(15000)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Follow-up</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(5000)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Overhead</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(3000)}</span>
                  </div>
                </div>
              </div>

              {/* Revenue Projection */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Revenue Projection</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Year 1</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(25000000)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Year 2</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(45000000)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Year 3</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(65000000)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Year 4</span>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(15000000)}</span>
                  </div>
                </div>
              </div>

              {/* Risk Analysis */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Risk Analysis</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Regulatory Risk</span>
                    <span className="text-sm font-medium text-yellow-600">Medium</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Competitive Risk</span>
                    <span className="text-sm font-medium text-red-600">High</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Technical Risk</span>
                    <span className="text-sm font-medium text-green-600">Low</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="border-t border-gray-200 px-6 py-4">
            <div className="flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Close
              </button>
              <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700">
                Edit Asset
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}













