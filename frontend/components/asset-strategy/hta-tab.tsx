"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Sparkles, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { HTAPathwayTimeline } from './hta-pathway-timeline'
import { HTAOutcomeLikelihood } from './hta-outcome-likelihood'
import { AccessRiskScore } from './access-risk-score'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'

interface HTATabProps {
  assetId: string
  market: string
  asset?: {
    asset_name?: string
    indication?: string
    therapeutic_area?: string
  }
}

export function HTATab({ assetId, market, asset }: HTATabProps) {
  const { generateHTAAssessment, isGenerating } = useAssetStrategyGeneration()
  const [assessmentGenerated, setAssessmentGenerated] = useState(false)

  const handleAIGenerateHTAAssessment = async () => {
    const response = await generateHTAAssessment({
      asset_id: assetId,
      context: { market }
    })
    
    if (response?.content) {
      toast.success('HTA assessment generated. Review the widgets below for detailed analysis.')
      setAssessmentGenerated(true)
      // The widgets will automatically refresh when data is available
    } else {
      toast.error('Failed to generate HTA assessment')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">HTA & Market Access Intelligence</h3>
          <p className="text-sm text-muted-foreground">Assess HTA requirements and access risk</p>
        </div>
        <Button
          onClick={handleAIGenerateHTAAssessment}
          disabled={isGenerating}
          className="gap-2 bg-primary hover:bg-primary/90"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate with AI
            </>
          )}
        </Button>
      </div>

      <HTAPathwayTimeline assetId={assetId} market={market} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <HTAOutcomeLikelihood assetId={assetId} market={market} />
        <AccessRiskScore assetId={assetId} market={market} />
      </div>
    </div>
  )
}

