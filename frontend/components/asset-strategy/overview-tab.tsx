"use client"

import { useState, useEffect, useRef } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sparkles, Loader2, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import type { AssetStrategy, DevelopmentStage, AssetStatus } from '@/lib/types/asset-strategy-types'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'
import { InlineActivityIndicator } from '@/components/activity/inline-activity-indicator'
import ReactMarkdown from 'react-markdown'

interface OverviewTabProps {
  asset: AssetStrategy
  onUpdate: (updates: Partial<AssetStrategy>) => void
  readOnly?: boolean
}

const DEVELOPMENT_STAGES: { value: DevelopmentStage; label: string }[] = [
  { value: 'discovery', label: 'Discovery' },
  { value: 'preclinical', label: 'Preclinical' },
  { value: 'phase_i', label: 'Phase I' },
  { value: 'phase_ii', label: 'Phase II' },
  { value: 'phase_iii', label: 'Phase III' },
  { value: 'pre_launch', label: 'Pre-Launch' },
  { value: 'launched', label: 'Launched' }
]

const ASSET_STATUSES: { value: AssetStatus; label: string }[] = [
  { value: 'go', label: 'Go' },
  { value: 'no_go', label: 'No-Go' },
  { value: 'conditional_go', label: 'Conditional Go' },
  { value: 'revisit', label: 'Revisit' }
]

export function OverviewTab({ asset, onUpdate, readOnly = false }: OverviewTabProps) {
  const [localAsset, setLocalAsset] = useState({
    ...asset,
    expected_launch_dates: asset.expected_launch_dates || {},
    key_milestone_dates: asset.key_milestone_dates || {}
  })
  const [timelineConsiderations, setTimelineConsiderations] = useState<string | null>(null)
  const [comparators, setComparators] = useState<any[]>([])
  const { generateAssetOverview, generateTimeline, generateComparators, isGenerating } = useAssetStrategyGeneration()
  const prevAssetIdRef = useRef(asset.id)
  const isUpdatingRef = useRef(false)

  // Only update local state when asset ID changes (different asset loaded)
  // Don't sync on every prop change to prevent input resets while typing
  useEffect(() => {
    if (asset.id !== prevAssetIdRef.current) {
      prevAssetIdRef.current = asset.id
      setLocalAsset({
        ...asset,
        expected_launch_dates: asset.expected_launch_dates || {},
        key_milestone_dates: asset.key_milestone_dates || {}
      })
    }
    // Note: We intentionally don't sync other field changes from props
    // to prevent input fields from resetting while the user is typing
  }, [asset.id])

  const handleFieldChange = (field: keyof AssetStrategy, value: any) => {
    const updated = { ...localAsset, [field]: value }
    setLocalAsset(updated)
    // Mark that we're updating to prevent sync loops
    isUpdatingRef.current = true
    onUpdate({ [field]: value })
    // Reset flag after a short delay
    setTimeout(() => {
      isUpdatingRef.current = false
    }, 100)
  }

  const handleAIGenerateMoA = async () => {
    if (!asset.therapeutic_area && !asset.indication) {
      toast.error('Please provide therapeutic area or indication first')
      return
    }
    
    const response = await generateAssetOverview({
      asset_id: asset.id,
      query: `Generate a detailed mechanism of action for this asset. Focus specifically on the MoA section.`,
      context: {
        therapeutic_area: asset.therapeutic_area,
        indication: asset.indication || undefined,
        moa: asset.moa || undefined
      }
    })

    if (response?.moa) {
      // Use structured response directly
      handleFieldChange('moa', response.moa)
      toast.success('MoA generated successfully')
    } else if (response?.content) {
      // Fallback: Extract from content
      const moa = response.content.replace(/\*\*/g, '').replace(/^.*?[Mm]echanism[^:]*:\s*/i, '').trim().split('\n')[0]
      handleFieldChange('moa', moa)
      toast.success('MoA generated successfully')
    } else {
      toast.error('Failed to generate MoA')
    }
  }

  const handleAIGenerateIndications = async () => {
    if (!asset.therapeutic_area) {
      toast.error('Please provide therapeutic area first')
      return
    }

    const response = await generateAssetOverview({
      asset_id: asset.id,
      query: `Generate relevant indications for this asset. Provide a list of 3-5 potential indications, one per line.`,
      context: {
        therapeutic_area: asset.therapeutic_area,
        moa: asset.moa || undefined
      }
    })

    if (response?.content) {
      // Extract indications from response
      const content = response.content
      // Look for "indications" section or numbered/bulleted list
      const indicationsMatch = content.match(/indications?[:\s]+([^\n]+(?:\n[-•\d.]+\s*[^\n]+)*)/i)
      const indicationsText = indicationsMatch ? indicationsMatch[1] : content
      
      const lines = indicationsText.split('\n').filter(l => l.trim())
      const indications = lines
        .map(line => line.replace(/^[-•\d.]+\s*/, '').replace(/\*\*/g, '').trim())
        .filter(ind => ind.length > 0 && ind.length < 100) // Filter out very long lines
        .slice(0, 5)
      
      if (indications.length > 0) {
        handleFieldChange('indications', [...(localAsset.indications || []), ...indications])
        toast.success(`Generated ${indications.length} indications`)
      } else {
        toast.error('Could not extract indications from response')
      }
    } else {
      toast.error('Failed to generate indications')
    }
  }

  const handleIndicationAdd = () => {
    const newIndication = prompt('Enter indication:')
    if (newIndication) {
      const indications = [...(localAsset.indications || []), newIndication]
      handleFieldChange('indications', indications)
    }
  }

  const handleAIGenerateSubpopulations = async () => {
    if (!asset.indication && !asset.therapeutic_area) {
      toast.error('Please provide indication or therapeutic area first')
      return
    }

    const response = await generateAssetOverview({
      asset_id: asset.id,
      query: `Generate relevant patient subpopulations for this asset. Provide a list of 3-5 subpopulations, one per line.`,
      context: {
        indication: asset.indication || undefined,
        therapeutic_area: asset.therapeutic_area
      }
    })

    if (response?.subpopulations && Array.isArray(response.subpopulations)) {
      // Use structured response directly
      handleFieldChange('subpopulations', [...(localAsset.subpopulations || []), ...response.subpopulations])
      toast.success(`Generated ${response.subpopulations.length} subpopulations`)
    } else if (response?.content) {
      // Fallback: Extract from content
      const content = response.content
      let subpopText = content
      
      const subpopMatch1 = content.match(/subpopulations?[:\s]+([^\n]+(?:\n[-•\d.]+\s*[^\n]+)*)/i)
      if (subpopMatch1) {
        subpopText = subpopMatch1[1]
      }
      
      const lines = subpopText.split('\n').filter(l => l.trim())
      const subpopulations = lines
        .map(line => {
          let cleaned = line
            .replace(/^[-•\d.]+\s*/, '')
            .replace(/\*\*/g, '')
            .replace(/^#+\s*/, '')
            .replace(/^\s*-\s*/, '')
            .trim()
          
          if (cleaned.length > 100 || cleaned.length === 0) {
            return null
          }
          
          if (cleaned.toLowerCase().includes('subpopulation') && cleaned.length < 30) {
            return null
          }
          
          return cleaned
        })
        .filter((sub): sub is string => sub !== null && sub.length > 0)
        .slice(0, 5)
      
      if (subpopulations.length > 0) {
        handleFieldChange('subpopulations', [...(localAsset.subpopulations || []), ...subpopulations])
        toast.success(`Generated ${subpopulations.length} subpopulations`)
      } else {
        toast.error('Could not extract subpopulations from response.')
        console.log('Generated content:', content)
      }
    } else {
      toast.error('Failed to generate subpopulations')
    }
  }

  const handleSubpopulationAdd = () => {
    const newSubpop = prompt('Enter subpopulation:')
    if (newSubpop) {
      const subpopulations = [...(localAsset.subpopulations || []), newSubpop]
      handleFieldChange('subpopulations', subpopulations)
    }
  }

  const handleAIGenerateTimeline = async () => {
    if (!asset.therapeutic_area && !asset.indication) {
      toast.error('Please provide therapeutic area or indication first')
      return
    }

    const response = await generateTimeline({
      asset_id: asset.id,
      context: {
        therapeutic_area: asset.therapeutic_area,
        indication: asset.indication || undefined,
        development_stage: asset.development_stage || undefined,
        moa: asset.moa || undefined
      }
    })

    if (response?.expected_launch_dates || response?.key_milestone_dates) {
      // Merge AI-generated timelines with existing ones (don't overwrite, just add new ones)
      const updatedLaunchDates = {
        ...(localAsset.expected_launch_dates || {}),
        ...(response.expected_launch_dates || {})
      }
      const updatedMilestoneDates = {
        ...(localAsset.key_milestone_dates || {}),
        ...(response.key_milestone_dates || {})
      }
      
      handleFieldChange('expected_launch_dates', updatedLaunchDates)
      handleFieldChange('key_milestone_dates', updatedMilestoneDates)
      
      // Store considerations for display
      if (response.considerations) {
        setTimelineConsiderations(response.considerations)
      }
      
      const launchCount = Object.keys(response.expected_launch_dates || {}).length
      const milestoneCount = Object.keys(response.key_milestone_dates || {}).length
      toast.success(
        `Generated ${launchCount} launch date${launchCount !== 1 ? 's' : ''} and ${milestoneCount} milestone${milestoneCount !== 1 ? 's' : ''}. ${response.rationale ? `(${response.rationale.substring(0, 80)}...)` : ''}`
      )
    } else {
      toast.error('Failed to generate timeline recommendations')
    }
  }

  const [showSummary, setShowSummary] = useState(false)

  return (
    <div className="space-y-6">
      {/* Summary Dashboard Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">Asset Overview</h3>
          <p className="text-sm text-muted-foreground">Core asset information and key metrics</p>
        </div>
        <Button
          variant="outline"
          onClick={() => setShowSummary(!showSummary)}
          className="gap-2"
        >
          {showSummary ? 'Hide' : 'Show'} Summary Dashboard
        </Button>
      </div>

      {/* Summary Dashboard */}
      {showSummary && (
        <div className="mb-6">
          <AssetSummaryDashboard assetId={asset.id} />
        </div>
      )}
      {/* Asset Master Data */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="asset_name">Asset Name</Label>
          <Input
            id="asset_name"
            value={localAsset.asset_name}
            onChange={(e) => handleFieldChange('asset_name', e.target.value)}
            disabled={readOnly}
          />
        </div>

        <div>
          <Label htmlFor="therapeutic_area">Therapeutic Area</Label>
          <Input
            id="therapeutic_area"
            value={localAsset.therapeutic_area}
            onChange={(e) => handleFieldChange('therapeutic_area', e.target.value)}
            disabled={readOnly}
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <Label htmlFor="moa">Mechanism of Action (MoA)</Label>
            {!readOnly && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handleAIGenerateMoA}
                disabled={isGenerating}
                className="h-7 text-xs"
              >
                {isGenerating ? (
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                ) : (
                  <Sparkles className="h-3 w-3 mr-1" />
                )}
                AI Generate
              </Button>
            )}
          </div>
          <Input
            id="moa"
            value={localAsset.moa || ''}
            onChange={(e) => handleFieldChange('moa', e.target.value)}
            disabled={readOnly}
            placeholder="e.g., PD-1 inhibitor"
          />
        </div>

        <div>
          <Label htmlFor="roa">Route of Administration (RoA)</Label>
          <Input
            id="roa"
            value={localAsset.roa || ''}
            onChange={(e) => handleFieldChange('roa', e.target.value)}
            disabled={readOnly}
            placeholder="e.g., IV, Oral"
          />
        </div>

        <div>
          <Label htmlFor="development_stage">Development Stage</Label>
          <Select
            value={localAsset.development_stage || ''}
            onValueChange={(value) => handleFieldChange('development_stage', value as DevelopmentStage)}
            disabled={readOnly}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select stage" />
            </SelectTrigger>
            <SelectContent>
              {DEVELOPMENT_STAGES.map((stage) => (
                <SelectItem key={stage.value} value={stage.value}>
                  {stage.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="status">Status</Label>
          <Select
            value={localAsset.status || ''}
            onValueChange={(value) => handleFieldChange('status', value as AssetStatus)}
            disabled={readOnly}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              {ASSET_STATUSES.map((status) => (
                <SelectItem key={status.value} value={status.value}>
                  {status.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Indications */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <Label>Indications</Label>
          {!readOnly && (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleAIGenerateIndications}
                disabled={isGenerating}
                className="gap-1"
              >
                {isGenerating ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Sparkles className="h-3 w-3" />
                )}
                Generate with AI
              </Button>
              <Button size="sm" variant="outline" onClick={handleIndicationAdd}>
                Add Manually
              </Button>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {localAsset.indications?.map((ind, idx) => (
            <Badge key={idx} variant="secondary">
              {ind}
              {!readOnly && (
                <button
                  className="ml-2 hover:text-red-600"
                  onClick={() => {
                    const indications = localAsset.indications?.filter((_, i) => i !== idx)
                    handleFieldChange('indications', indications)
                  }}
                >
                  ×
                </button>
              )}
            </Badge>
          ))}
          {(!localAsset.indications || localAsset.indications.length === 0) && (
            <span className="text-sm text-gray-500">No indications added</span>
          )}
        </div>
      </div>

      {/* Subpopulations */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <Label>Subpopulations</Label>
          {!readOnly && (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleAIGenerateSubpopulations}
                disabled={isGenerating}
                className="gap-1"
              >
                {isGenerating ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Sparkles className="h-3 w-3" />
                )}
                Generate with AI
              </Button>
              <Button size="sm" variant="outline" onClick={handleSubpopulationAdd}>
                Add Manually
              </Button>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {localAsset.subpopulations?.map((subpop, idx) => (
            <Badge key={idx} variant="secondary">
              {subpop}
              {!readOnly && (
                <button
                  className="ml-2 hover:text-red-600"
                  onClick={() => {
                    const subpopulations = localAsset.subpopulations?.filter((_, i) => i !== idx)
                    handleFieldChange('subpopulations', subpopulations)
                  }}
                >
                  ×
                </button>
              )}
            </Badge>
          ))}
          {(!localAsset.subpopulations || localAsset.subpopulations.length === 0) && (
            <span className="text-sm text-gray-500">No subpopulations added</span>
          )}
        </div>
      </div>

      {/* Comparators */}
      <div className="border-t pt-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">Comparators</h3>
            <p className="text-sm text-muted-foreground">Competitive landscape and benchmark drugs</p>
          </div>
          {!readOnly && (
            <Button
              onClick={async () => {
                if (!asset.indication && !asset.therapeutic_area) {
                  toast.error('Please provide indication or therapeutic area first')
                  return
                }
                
                const response = await generateComparators({
                  asset_id: asset.id,
                  context: {
                    indication: asset.indication || undefined,
                    therapeutic_area: asset.therapeutic_area,
                    market: 'US'
                  }
                })
                
                if (response?.comparators && Array.isArray(response.comparators)) {
                  setComparators(response.comparators)
                  toast.success(`Generated ${response.comparators.length} comparators`)
                } else if (response?.content) {
                  toast.success('Comparators generated. Check the pricing tab for benchmark analysis.')
                } else {
                  toast.error('Failed to generate comparators')
                }
              }}
              disabled={isGenerating}
              size="sm"
              variant="outline"
              className="gap-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate Comparators
                </>
              )}
            </Button>
          )}
        </div>
        <InlineActivityIndicator
          operationType="ai_generation"
          context={{ assetId: asset.id, tab: 'overview', operation: 'comparators' }}
        />
        {comparators.length > 0 ? (
          <div className="space-y-3">
            {comparators.map((comp, idx) => (
              <Card key={idx} className="p-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-sm">{comp.drug || comp.name || 'Unknown Drug'}</div>
                    {comp.indication && (
                      <div className="text-xs text-gray-600 mt-1">Indication: {comp.indication}</div>
                    )}
                    {comp.rationale && (
                      <div className="text-xs text-gray-500 mt-1">{comp.rationale}</div>
                    )}
                    {comp.market && (
                      <Badge variant="outline" className="mt-2 text-xs">
                        {comp.market}
                      </Badge>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 border-2 border-dashed rounded-lg">
            <p className="text-sm">No comparators generated yet</p>
            <p className="text-xs mt-1">Click "Generate Comparators" to identify competitive drugs</p>
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="border-t pt-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium">Timeline</h3>
          {!readOnly && (
            <Button
              onClick={handleAIGenerateTimeline}
              disabled={isGenerating}
              size="sm"
              variant="outline"
              className="gap-2"
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
          )}
        </div>
        <InlineActivityIndicator
          operationType="ai_generation"
          context={{ assetId: asset.id, tab: 'overview' }}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Expected Launch Dates</Label>
            <div className="space-y-2 mt-2">
              {Object.entries(localAsset.expected_launch_dates || {}).map(([market, date], index) => {
                // Use index as stable key - never changes, prevents remounting
                return (
                <div key={`launch_${index}`} className="flex items-center gap-2">
                  <Input
                    value={market}
                    placeholder="Market (e.g., US, EU, JP)"
                    disabled={readOnly}
                    className="flex-1"
                    onChange={(e) => {
                      const newMarket = e.target.value // Don't trim while typing!
                      const dates = { ...(localAsset.expected_launch_dates || {}) }
                      const oldDate = dates[market] || ''
                      
                      // Delete old key and add new key with same date
                      delete dates[market]
                      dates[newMarket] = oldDate
                      
                      handleFieldChange('expected_launch_dates', dates)
                    }}
                    onBlur={(e) => {
                      // Trim on blur to clean up whitespace
                      const trimmed = e.target.value.trim()
                      if (trimmed !== market && trimmed) {
                        const dates = { ...(localAsset.expected_launch_dates || {}) }
                        const oldDate = dates[market] || ''
                        delete dates[market]
                        dates[trimmed] = oldDate
                        handleFieldChange('expected_launch_dates', dates)
                      }
                    }}
                  />
                  <Input
                    type="date"
                    value={date || ''}
                    disabled={readOnly}
                    className="w-40"
                    onChange={(e) => {
                      const dates = { ...(localAsset.expected_launch_dates || {}) }
                      dates[market] = e.target.value
                      handleFieldChange('expected_launch_dates', dates)
                    }}
                  />
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        const dates = { ...(localAsset.expected_launch_dates || {}) }
                        delete dates[market]
                        handleFieldChange('expected_launch_dates', dates)
                      }}
                      className="text-red-600 hover:text-red-700"
                    >
                      ×
                    </Button>
                  )}
                </div>
                )
              })}
              {(!localAsset.expected_launch_dates || Object.keys(localAsset.expected_launch_dates).length === 0) && (
                <p className="text-sm text-muted-foreground">No launch dates added</p>
              )}
              {!readOnly && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    const dates = { ...(localAsset.expected_launch_dates || {}) }
                    // Add a new entry with a temporary key
                    const tempKey = `market_${Date.now()}`
                    dates[tempKey] = ''
                    handleFieldChange('expected_launch_dates', dates)
                  }}
                  className="w-full"
                >
                  + Add Launch Date
                </Button>
              )}
            </div>
          </div>

          <div>
            <Label>Key Milestone Dates</Label>
            <div className="space-y-2 mt-2">
              {Object.entries(localAsset.key_milestone_dates || {}).map(([milestone, date], index) => {
                // Use index as stable key - never changes, prevents remounting
                return (
                <div key={`milestone_${index}`} className="flex items-center gap-2">
                  <Input
                    value={milestone}
                    placeholder="Milestone (e.g., Phase III Start, NDA Submission)"
                    disabled={readOnly}
                    className="flex-1"
                    onChange={(e) => {
                      const newMilestone = e.target.value // Don't trim while typing!
                      const dates = { ...(localAsset.key_milestone_dates || {}) }
                      const oldDate = dates[milestone] || ''
                      
                      // Delete old key and add new key with same date
                      delete dates[milestone]
                      dates[newMilestone] = oldDate
                      
                      handleFieldChange('key_milestone_dates', dates)
                    }}
                    onBlur={(e) => {
                      // Trim on blur to clean up whitespace
                      const trimmed = e.target.value.trim()
                      if (trimmed !== milestone && trimmed) {
                        const dates = { ...(localAsset.key_milestone_dates || {}) }
                        const oldDate = dates[milestone] || ''
                        delete dates[milestone]
                        dates[trimmed] = oldDate
                        handleFieldChange('key_milestone_dates', dates)
                      }
                    }}
                  />
                  <Input
                    type="date"
                    value={date || ''}
                    disabled={readOnly}
                    className="w-40"
                    onChange={(e) => {
                      const dates = { ...(localAsset.key_milestone_dates || {}) }
                      dates[milestone] = e.target.value
                      handleFieldChange('key_milestone_dates', dates)
                    }}
                  />
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        const dates = { ...(localAsset.key_milestone_dates || {}) }
                        delete dates[milestone]
                        handleFieldChange('key_milestone_dates', dates)
                      }}
                      className="text-red-600 hover:text-red-700"
                    >
                      ×
                    </Button>
                  )}
                </div>
                )
              })}
              {(!localAsset.key_milestone_dates || Object.keys(localAsset.key_milestone_dates).length === 0) && (
                <p className="text-sm text-muted-foreground">No milestone dates added</p>
              )}
              {!readOnly && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    const dates = { ...(localAsset.key_milestone_dates || {}) }
                    // Add a new entry with a temporary key
                    const tempKey = `milestone_${Date.now()}`
                    dates[tempKey] = ''
                    handleFieldChange('key_milestone_dates', dates)
                  }}
                  className="w-full"
                >
                  + Add Milestone
                </Button>
              )}
            </div>
          </div>
        </div>
        
        {/* Timeline Considerations */}
        {timelineConsiderations && (
          <div className="mt-4">
            <Card className="bg-blue-50 border-blue-200">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-blue-600" />
                  <CardTitle className="text-base">Timeline Considerations</CardTitle>
                </div>
                <CardDescription>
                  Key factors, assumptions, and regulatory considerations impacting the timeline
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none text-gray-700">
                  <ReactMarkdown>{timelineConsiderations}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="border-t pt-4">
        <h3 className="text-lg font-medium mb-4">Quick Stats</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Last Updated</div>
            <div className="font-medium">
              {new Date(localAsset.last_updated).toLocaleDateString()}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Created By</div>
            <div className="font-medium">{localAsset.created_by}</div>
          </div>
          <div>
            <div className="text-gray-500">Current Decision Cut</div>
            <div className="font-medium text-gray-400">-</div>
          </div>
        </div>
      </div>
    </div>
  )
}

