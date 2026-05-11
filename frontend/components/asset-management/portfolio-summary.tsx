import { Asset } from '@/lib/types/asset-types'

interface PortfolioSummaryProps {
  assets: Asset[]
}

export function PortfolioSummary({ assets }: PortfolioSummaryProps) {
  const totalInvestment = assets.reduce((sum, asset) => sum + asset.total_estimated_cost, 0)
  const projectedRevenue = assets.reduce((sum, asset) => sum + asset.projected_revenue, 0)
  const activeAssets = assets.filter(asset => asset.status === 'active').length
  const roiPercentage = totalInvestment > 0 ? ((projectedRevenue - totalInvestment) / totalInvestment) * 100 : 0

  const therapeuticAreas = assets.reduce((acc, asset) => {
    acc[asset.therapeutic_area] = (acc[asset.therapeutic_area] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const phaseDistribution = assets.reduce((acc, asset) => {
    acc[asset.trial_phase] = (acc[asset.trial_phase] || 0) + 1
    return acc
  }, {} as Record<string, number>)

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
      {/* Portfolio Overview */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Overview</h3>
        
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Total Investment</span>
            <span className="text-lg font-semibold text-gray-900">{formatCurrency(totalInvestment)}</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Projected Revenue</span>
            <span className="text-lg font-semibold text-green-600">{formatCurrency(projectedRevenue)}</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">ROI</span>
            <span className={`text-lg font-semibold ${roiPercentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {roiPercentage.toFixed(1)}%
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Active Assets</span>
            <span className="text-lg font-semibold text-blue-600">{activeAssets}</span>
          </div>
        </div>
      </div>

      {/* Therapeutic Area Distribution */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Therapeutic Areas</h3>
        
        <div className="space-y-3">
          {Object.entries(therapeuticAreas).map(([area, count]) => (
            <div key={area} className="flex justify-between items-center">
              <span className="text-sm text-gray-600">{area}</span>
              <span className="text-sm font-medium text-gray-900">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Phase Distribution */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Phase Distribution</h3>
        
        <div className="space-y-3">
          {Object.entries(phaseDistribution).map(([phase, count]) => (
            <div key={phase} className="flex justify-between items-center">
              <span className="text-sm text-gray-600">{phase}</span>
              <span className="text-sm font-medium text-gray-900">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        
        <div className="space-y-2">
          <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
            📊 Run Cost Analysis
          </button>
          <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
            💰 Generate Revenue Projection
          </button>
          <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
            ⚠️ Risk Assessment
          </button>
          <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
            📈 Portfolio Analytics
          </button>
        </div>
      </div>
    </div>
  )
}






















