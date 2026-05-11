"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Sparkles, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { PriceWaterfall } from './price-waterfall'
import { ComparatorBenchmark } from './comparator-benchmark'
import { PriceConfidenceWidget } from './price-confidence-widget'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'
import { InlineActivityIndicator } from '@/components/activity/inline-activity-indicator'
import { useAssetStrategy } from '@/lib/contexts/asset-strategy-context'

interface PricingTabProps {
  assetId: string
  market: string
  asset?: {
    asset_name?: string
    indication?: string
    therapeutic_area?: string
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export function PricingTab({ assetId, market, asset }: PricingTabProps) {
  const { generatePricePotential, isGenerating } = useAssetStrategyGeneration()
  const { setTabContent, getTabContent } = useAssetStrategy()
  
  // Load saved state from context
  const savedState = getTabContent('pricing') || {}
  const [priceGenerated, setPriceGenerated] = useState(savedState.priceGenerated || false)
  const [priceData, setPriceData] = useState<any>(savedState.priceData || null)
  const [refreshKey, setRefreshKey] = useState(savedState.refreshKey || 0)
  
  // Save state to context whenever it changes
  useEffect(() => {
    setTabContent('pricing', {
      priceGenerated,
      priceData,
      refreshKey
    })
  }, [priceGenerated, priceData, refreshKey, setTabContent])

  const handleAIGeneratePricePotential = async () => {
    try {
      const response = await generatePricePotential({
        asset_id: assetId,
        context: { market }
      })
      
      if (response?.structured_data) {
        const structured = response.structured_data
        const recommendedPrice = structured.recommended_price_range
        const avgPrice = recommendedPrice ? (recommendedPrice.min + recommendedPrice.max) / 2 : 100000
        
        // Calculate price prediction using the recommended price
        // The backend will now use real GTN calculations from formulary tier, payer plan, and comparator data
        try {
          const predictResponse = await fetch(`${API_BASE_URL}/api/asset-strategy/pricing/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              asset_id: assetId,
              market: market,
              list_price: avgPrice,
              // These will be overridden by real GTN calculations if asset data is available
              mandatory_discount_pct: 0.0,
              expected_rebates: 0.0,
              clawbacks: 0.0,
              program_adjustments: 0.0,
              include_uncertainty: true
            })
          })
          
          if (predictResponse.ok) {
            const predictionData = await predictResponse.json()
            setPriceData(predictionData)
            setRefreshKey(prev => prev + 1) // Force widgets to refresh
            toast.success('Price potential analysis generated and calculated. Review the pricing widgets below.')
          } else {
            toast.success('Price potential analysis generated. Review the pricing widgets below.')
          }
        } catch (error) {
          console.error('Failed to calculate price prediction:', error)
          toast.success('Price potential analysis generated. Review the pricing widgets below.')
        }
        
        setPriceGenerated(true)
      } else if (response?.content) {
        toast.success('Price potential analysis generated. Review the pricing widgets below.')
        setPriceGenerated(true)
      } else {
        toast.error('Failed to generate price potential')
      }
    } catch (error) {
      console.error('Failed to generate price potential:', error)
      toast.error('Failed to generate price potential')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">US Market Price Potential & Net Price Prediction</h3>
          <p className="text-sm text-muted-foreground">Analyze pricing strategy and market positioning</p>
        </div>
        <Button
          onClick={handleAIGeneratePricePotential}
          disabled={isGenerating}
          className="gap-2 bg-primary hover:bg-primary/90"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate with AI
            </>
          )}
        </Button>
      </div>
      <InlineActivityIndicator
        operationType="pricing_calc"
        context={{ assetId, tab: 'pricing' }}
      />

      <PriceWaterfall 
        key={`price-waterfall-${refreshKey}`} 
        assetId={assetId} 
        market={market}
        priceData={priceData}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ComparatorBenchmark 
          key={`comparator-benchmark-${refreshKey}`} 
          assetId={assetId} 
          market={market} 
          predictedPrice={priceData?.net_price || 50000} 
        />
        <PriceConfidenceWidget key={`price-confidence-${refreshKey}`} assetId={assetId} market={market} />
      </div>
    </div>
  )
}

