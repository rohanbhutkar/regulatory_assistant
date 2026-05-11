export function MarketAnalysis() {
  return (
    <div className="space-y-6">
      {/* Market Overview */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Market Overview</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-900">$2.5B</div>
            <div className="text-sm text-gray-600">Market Size</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-600">85%</div>
            <div className="text-sm text-gray-600">Payer Coverage</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">12%</div>
            <div className="text-sm text-gray-600">Market Penetration</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-600">3</div>
            <div className="text-sm text-gray-600">Key Competitors</div>
          </div>
        </div>
      </div>

      {/* Competitive Landscape */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Competitive Landscape</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Competitor A</div>
              <div className="text-sm text-gray-600">Market Leader</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-gray-900">35%</div>
              <div className="text-sm text-gray-600">Market Share</div>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Competitor B</div>
              <div className="text-sm text-gray-600">Established Player</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-gray-900">28%</div>
              <div className="text-sm text-gray-600">Market Share</div>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Competitor C</div>
              <div className="text-sm text-gray-600">Emerging Player</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-gray-900">22%</div>
              <div className="text-sm text-gray-600">Market Share</div>
            </div>
          </div>
        </div>
      </div>

      {/* Payer Analysis */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Payer Analysis</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">Commercial</h4>
            <div className="text-2xl font-bold text-blue-600">40%</div>
            <div className="text-sm text-blue-700">Payer Split</div>
            <div className="text-sm text-blue-700 mt-1">80% Coverage</div>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4">
            <h4 className="font-medium text-green-900 mb-2">Medicare</h4>
            <div className="text-2xl font-bold text-green-600">35%</div>
            <div className="text-sm text-green-700">Payer Split</div>
            <div className="text-sm text-green-700 mt-1">90% Coverage</div>
          </div>
          
          <div className="bg-purple-50 rounded-lg p-4">
            <h4 className="font-medium text-purple-900 mb-2">Medicaid</h4>
            <div className="text-2xl font-bold text-purple-600">25%</div>
            <div className="text-sm text-purple-700">Payer Split</div>
            <div className="text-sm text-purple-700 mt-1">70% Coverage</div>
          </div>
        </div>
      </div>

      {/* Market Trends */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Market Trends</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Market Growth Rate</div>
              <div className="text-sm text-gray-600">Annual growth projection</div>
            </div>
            <div className="text-lg font-bold text-green-600">+8.5%</div>
          </div>
          
          <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Price Pressure</div>
              <div className="text-sm text-gray-600">Expected pricing trends</div>
            </div>
            <div className="text-lg font-bold text-yellow-600">-3.2%</div>
          </div>
          
          <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Regulatory Changes</div>
              <div className="text-sm text-gray-600">Impact on market access</div>
            </div>
            <div className="text-lg font-bold text-blue-600">Neutral</div>
          </div>
        </div>
      </div>
    </div>
  )
}






















