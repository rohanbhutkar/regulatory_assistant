"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Lock, Unlock, Copy, Plus, X, Sparkles, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import type { AssumptionSet, Comparator } from '@/lib/types/asset-strategy-types'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'

interface AssumptionsTabProps {
  assetId: string
  asset?: {
    asset_name?: string
    therapeutic_area?: string
    indication?: string
    moa?: string
  }
  readOnly?: boolean
}

export function AssumptionsTab({ assetId, asset, readOnly = false }: AssumptionsTabProps) {
  const [assumptionSets, setAssumptionSets] = useState<AssumptionSet[]>([])
  const [selectedSet, setSelectedSet] = useState<AssumptionSet | null>(null)
  const { generateBenefitHypothesis, generateComparators, generateAssumptionSet, isGenerating } = useAssetStrategyGeneration()

  useEffect(() => {
    loadAssumptionSets()
  }, [assetId])

  const loadAssumptionSets = async () => {
    try {
      const response = await fetch(assetStrategyAPI.getAssumptions(assetId))
      if (response.ok) {
        const data = await response.json()
        setAssumptionSets(data)
        if (data.length > 0 && !selectedSet) {
          setSelectedSet(data[0])
        }
      }
    } catch (error) {
      console.error('Failed to load assumption sets:', error)
    }
  }

  const handleCreateSet = async () => {
    const name = prompt('Enter assumption set name:')
    if (!name) return

    try {
      const response = await fetch(assetStrategyAPI.createAssumptionSet(assetId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, asset_id: assetId })
      })

      if (response.ok) {
        await loadAssumptionSets()
      }
    } catch (error) {
      console.error('Failed to create assumption set:', error)
    }
  }

  const handleAIGenerateComparators = async () => {
    if (!selectedSet) {
      toast.error('Please select or create an assumption set first')
      return
    }

    if (!asset?.indication) {
      toast.error('Please provide indication in asset overview first')
      return
    }

    const market = prompt('Enter market (e.g., US, EU):', 'US') || 'US'
    
    const response = await generateComparators({
      asset_id: assetId,
      context: {
        indication: asset.indication,
        market: market
      }
    })

    if (response?.comparators && Array.isArray(response.comparators)) {
      // Use structured response directly
      const comparators = response.comparators.map(c => ({
        drug: c.drug || '',
        indication: c.indication || asset.indication || '',
        market: c.market || market,
        rationale: c.rationale || ''
      }))

      if (comparators.length > 0) {
        try {
          const updateResponse = await fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              comparator_set: [
                ...selectedSet.comparator_set,
                ...comparators
              ]
            })
          })

          if (updateResponse.ok) {
            await loadAssumptionSets()
            toast.success(`Added ${comparators.length} AI-generated comparators`)
          }
        } catch (error) {
          console.error('Failed to add comparators:', error)
          toast.error('Failed to save comparators')
        }
      } else {
        toast.error('No comparators in response')
      }
    } else if (response?.content) {
      // Fallback: Parse from content
      const lines = response.content.split('\n').filter(l => l.trim())
      const comparators = lines
        .map(line => {
          const cleaned = line.replace(/^[-•\d.]+\s*/, '').replace(/\*\*/g, '').trim()
          const drug = cleaned.split(/[:–-]/)[0].trim()
          return {
            drug: drug || cleaned,
            indication: asset.indication || '',
            market: market
          }
        })
        .filter(c => c.drug.length > 0)
        .slice(0, 5)

      if (comparators.length > 0) {
        try {
          const updateResponse = await fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              comparator_set: [
                ...selectedSet.comparator_set,
                ...comparators
              ]
            })
          })

          if (updateResponse.ok) {
            await loadAssumptionSets()
            toast.success(`Added ${comparators.length} AI-generated comparators`)
          }
        } catch (error) {
          console.error('Failed to add comparators:', error)
          toast.error('Failed to save comparators')
        }
      } else {
        toast.error('Could not extract comparators from response')
      }
    } else {
      toast.error('Failed to generate comparators')
    }
  }

  const handleAIGenerateBenefitHypothesis = async () => {
    if (!selectedSet) {
      toast.error('Please select or create an assumption set first')
      return
    }

    const response = await generateBenefitHypothesis({
      asset_id: assetId,
      context: {
        indication: asset?.indication,
        therapeutic_area: asset?.therapeutic_area,
        moa: asset?.moa
      }
    })

    if (response?.content) {
      try {
        const updateResponse = await fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ benefit_hypothesis: response.content })
        })

        if (updateResponse.ok) {
          await loadAssumptionSets()
          toast.success('Benefit hypothesis generated successfully')
        }
      } catch (error) {
        console.error('Failed to update hypothesis:', error)
        toast.error('Failed to save benefit hypothesis')
      }
    } else {
      toast.error('Failed to generate benefit hypothesis')
    }
  }

  const handleAIGenerateFullSet = async () => {
    const name = prompt('Enter assumption set name:', `AI Generated Set ${new Date().toLocaleDateString()}`)
    if (!name) return

    // Create set first
    try {
      const createResponse = await fetch(assetStrategyAPI.createAssumptionSet(assetId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, asset_id: assetId })
      })

      if (!createResponse.ok) {
        toast.error('Failed to create assumption set')
        return
      }

      const newSet = await createResponse.json()
      setSelectedSet(newSet)

      // Generate full set with AI
      const response = await generateAssumptionSet({
        asset_id: assetId,
        context: {
          indication: asset?.indication,
          therapeutic_area: asset?.therapeutic_area,
          moa: asset?.moa
        }
      })

      if (response?.content) {
        // Parse and update the set
        const updateResponse = await fetch(assetStrategyAPI.updateAssumptionSet(newSet.id), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            benefit_hypothesis: response.content,
            // Could parse more from response if structured
          })
        })

        if (updateResponse.ok) {
          await loadAssumptionSets()
          toast.success('Assumption set generated successfully')
        }
      }
    } catch (error) {
      console.error('Failed to generate assumption set:', error)
      toast.error('Failed to generate assumption set')
    }
  }

  const handleAddComparator = async () => {
    if (!selectedSet) return

    const drug = prompt('Enter comparator drug:')
    const indication = prompt('Enter indication:', asset?.indication || '')
    const market = prompt('Enter market:', 'US')

    if (!drug || !indication || !market) return

    try {
      const response = await fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          comparator_set: [
            ...selectedSet.comparator_set,
            { drug, indication, market }
          ]
        })
      })

      if (response.ok) {
        await loadAssumptionSets()
      }
    } catch (error) {
      console.error('Failed to add comparator:', error)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Assumption Sets</h3>
        {!readOnly && (
          <div className="flex gap-2">
            <Button
              onClick={handleAIGenerateFullSet}
              disabled={isGenerating}
              size="sm"
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
            <Button onClick={handleCreateSet} size="sm" variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Create Manually
            </Button>
          </div>
        )}
      </div>

      {assumptionSets.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            No assumption sets created yet
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Assumption Set List */}
          <div className="space-y-2">
            {assumptionSets.map((set) => (
              <Card
                key={set.id}
                className={`cursor-pointer ${selectedSet?.id === set.id ? 'ring-2 ring-blue-500' : ''}`}
                onClick={() => setSelectedSet(set)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{set.name}</CardTitle>
                    {set.is_locked && <Lock className="h-4 w-4 text-yellow-500" />}
                  </div>
                  <CardDescription className="text-xs">
                    v{set.version} • {new Date(set.updated_at).toLocaleDateString()}
                  </CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>

          {/* Selected Set Details */}
          {selectedSet && (
            <div className="md:col-span-2 space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{selectedSet.name}</CardTitle>
                    {!readOnly && (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            const newName = prompt('Enter new name:')
                            if (newName) {
                              try {
                                await fetch(assetStrategyAPI.cloneAssumptionSet(selectedSet.id), {
                                  method: 'POST',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ new_name: newName })
                                })
                                await loadAssumptionSets()
                              } catch (error) {
                                console.error('Failed to clone set:', error)
                              }
                            }
                          }}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Clone
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            try {
                              const endpoint = selectedSet.is_locked ? 'unlock' : 'lock'
                              const url = endpoint === 'lock' 
                                ? assetStrategyAPI.lockAssumptionSet(selectedSet.id)
                                : assetStrategyAPI.unlockAssumptionSet(selectedSet.id)
                              await fetch(url, {
                                method: 'POST'
                              })
                              await loadAssumptionSets()
                            } catch (error) {
                              console.error('Failed to toggle lock:', error)
                            }
                          }}
                        >
                          {selectedSet.is_locked ? (
                            <>
                              <Unlock className="h-4 w-4 mr-2" />
                              Unlock
                            </>
                          ) : (
                            <>
                              <Lock className="h-4 w-4 mr-2" />
                              Lock
                            </>
                          )}
                        </Button>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Comparators */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Label>Comparators</Label>
                      {!readOnly && !selectedSet.is_locked && (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleAIGenerateComparators}
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
                          <Button size="sm" variant="outline" onClick={handleAddComparator}>
                            <Plus className="h-4 w-4 mr-2" />
                            Add Manually
                          </Button>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      {selectedSet.comparator_set.map((comp, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium">{comp.drug}</div>
                            <div className="text-sm text-gray-500">
                              {comp.indication} • {comp.market}
                            </div>
                          </div>
                          {!readOnly && !selectedSet.is_locked && (
                            <Button
                              size="sm"
                              variant="ghost"
                      onClick={async () => {
                        try {
                          const updatedComparators = selectedSet.comparator_set.filter((_, i) => i !== idx)
                          await fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              comparator_set: updatedComparators
                            })
                          })
                          await loadAssumptionSets()
                        } catch (error) {
                          console.error('Failed to remove comparator:', error)
                        }
                      }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Benefit Hypothesis */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Label>Benefit Hypothesis</Label>
                      {!readOnly && !selectedSet.is_locked && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={handleAIGenerateBenefitHypothesis}
                          disabled={isGenerating}
                          className="h-7 text-xs gap-1"
                        >
                          {isGenerating ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Sparkles className="h-3 w-3" />
                          )}
                          Generate with AI
                        </Button>
                      )}
                    </div>
                    {selectedSet.benefit_hypothesis ? (
                      <div className="border rounded-lg p-4 bg-gray-50">
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>{selectedSet.benefit_hypothesis}</ReactMarkdown>
                        </div>
                        {!readOnly && !selectedSet.is_locked && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="mt-2"
                            onClick={() => {
                              const newValue = prompt('Edit benefit hypothesis:', selectedSet.benefit_hypothesis)
                              if (newValue !== null) {
                                fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
                                  method: 'PUT',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ benefit_hypothesis: newValue })
                                }).then(() => loadAssumptionSets())
                              }
                            }}
                          >
                            Edit
                          </Button>
                        )}
                      </div>
                    ) : (
                      <Textarea
                        value={selectedSet.benefit_hypothesis || ''}
                        disabled={readOnly || selectedSet.is_locked}
                        placeholder="Describe the benefit hypothesis... Use AI to generate or type manually."
                        rows={4}
                        onBlur={async (e) => {
                          try {
                            await fetch(assetStrategyAPI.updateAssumptionSet(selectedSet.id), {
                              method: 'PUT',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ benefit_hypothesis: e.target.value })
                            })
                            await loadAssumptionSets()
                          } catch (error) {
                            console.error('Failed to update hypothesis:', error)
                          }
                        }}
                      />
                    )}
                  </div>

                  {/* Uptake Archetype */}
                  <div>
                    <Label>Uptake Archetype</Label>
                    <Select
                      value={selectedSet.uptake_archetype || ''}
                      disabled={readOnly || selectedSet.is_locked}
                      onValueChange={async (value) => {
                        if (!selectedSet || selectedSet.is_locked) return
                        try {
                          await fetch(`/api/asset-strategy/assumption-sets/${selectedSet.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ uptake_archetype: value })
                          })
                          await loadAssumptionSets()
                        } catch (error) {
                          console.error('Failed to update uptake:', error)
                        }
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select archetype" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fast">Fast</SelectItem>
                        <SelectItem value="moderate">Moderate</SelectItem>
                        <SelectItem value="slow">Slow</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

