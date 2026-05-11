"use client"

import { useState, useEffect, useRef, useCallback } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { AssetStrategy, DevelopmentStage, AssetStatus } from '@/lib/types/asset-strategy-types'
import { OverviewTab } from './overview-tab'
import { EvidenceTab } from './evidence-tab'
import { AssumptionsTab } from './assumptions-tab'
import { GovernanceTab } from './governance-tab'
import { PricingTab } from './pricing-tab'
import { HTATab } from './hta-tab'
import { FinancialValueTab } from './financial-value-tab'
import { ScenarioTab } from './scenario-tab'
import { AssetStrategyProvider, useAssetStrategy } from '@/lib/contexts/asset-strategy-context'
import { Save, Loader2 } from 'lucide-react'

interface AssetCardProps {
  asset: AssetStrategy
  onUpdate?: (asset: AssetStrategy) => void
  readOnly?: boolean
}

function AssetCardContent({ asset, onUpdate, readOnly = false }: AssetCardProps) {
  const {
    currentAsset,
    setCurrentAsset,
    activeTab,
    setActiveTab,
    saveAsset,
    isSaving,
    autoSaveEnabled,
    setAutoSaveEnabled
  } = useAssetStrategy()
  
  const prevAssetIdRef = useRef(asset.id)

  // Initialize context with asset on mount or when asset ID changes
  useEffect(() => {
    if (asset.id !== prevAssetIdRef.current) {
      prevAssetIdRef.current = asset.id
      setCurrentAsset(asset)
    } else if (!currentAsset) {
      setCurrentAsset(asset)
    }
  }, [asset.id, asset, currentAsset, setCurrentAsset])

  // Sync context asset with parent updates (but preserve tab content)
  useEffect(() => {
    if (currentAsset && asset.id === currentAsset.id) {
      // Only update if there are meaningful changes (not just tab content)
      const hasSignificantChanges = 
        currentAsset.asset_name !== asset.asset_name ||
        currentAsset.therapeutic_area !== asset.therapeutic_area ||
        currentAsset.development_stage !== asset.development_stage ||
        currentAsset.status !== asset.status
      
      if (hasSignificantChanges) {
        setCurrentAsset(asset)
      }
    }
  }, [asset, currentAsset, setCurrentAsset])
  
  const handleUpdate = useCallback((updates: Partial<AssetStrategy>) => {
    if (!currentAsset) return
    
    // Update context asset
    const updated = { ...currentAsset, ...updates }
    setCurrentAsset(updated)
    
    // Also notify parent (debounced)
    onUpdate?.(updated)
  }, [currentAsset, setCurrentAsset, onUpdate])

  const getStatusBadge = (status?: AssetStatus) => {
    if (!status) return null
    
    const styles = {
      go: 'bg-green-100 text-green-800',
      no_go: 'bg-red-100 text-red-800',
      conditional_go: 'bg-yellow-100 text-yellow-800',
      revisit: 'bg-blue-100 text-blue-800'
    }
    
    return (
      <Badge className={styles[status]}>
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    )
  }

  if (!currentAsset) {
    return <div>Loading...</div>
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-2xl">{currentAsset.asset_name}</CardTitle>
            <CardDescription className="mt-1">
              {currentAsset.therapeutic_area} • {currentAsset.development_stage || 'Not specified'}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge(currentAsset.status)}
            <Button
              variant="outline"
              size="sm"
              onClick={saveAsset}
              disabled={isSaving}
              className="ml-2"
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-8 lg:grid-cols-8">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="evidence">Evidence</TabsTrigger>
            <TabsTrigger value="assumptions">Assumptions</TabsTrigger>
            <TabsTrigger value="pricing">Pricing</TabsTrigger>
            <TabsTrigger value="hta">HTA Timeline</TabsTrigger>
            <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
            <TabsTrigger value="value">Value</TabsTrigger>
            <TabsTrigger value="governance">Governance</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-4">
            <OverviewTab 
              asset={currentAsset} 
              onUpdate={handleUpdate}
              readOnly={readOnly}
            />
          </TabsContent>

          <TabsContent value="evidence" className="mt-4">
            <EvidenceTab 
              assetId={currentAsset.id}
              asset={{
                asset_name: currentAsset.asset_name,
                therapeutic_area: currentAsset.therapeutic_area,
                indication: currentAsset.indication || currentAsset.indications?.[0]
              }}
              readOnly={readOnly}
            />
          </TabsContent>

          <TabsContent value="assumptions" className="mt-4">
            <AssumptionsTab 
              assetId={currentAsset.id}
              asset={{
                asset_name: currentAsset.asset_name,
                therapeutic_area: currentAsset.therapeutic_area,
                indication: currentAsset.indication || currentAsset.indications?.[0],
                moa: currentAsset.moa
              }}
              readOnly={readOnly}
            />
          </TabsContent>

          <TabsContent value="pricing" className="mt-4">
            <PricingTab
              assetId={currentAsset.id}
              market="US"
              asset={{
                asset_name: currentAsset.asset_name,
                indication: currentAsset.indication || currentAsset.indications?.[0],
                therapeutic_area: currentAsset.therapeutic_area
              }}
            />
          </TabsContent>

          <TabsContent value="hta" className="mt-4">
            <HTATab
              assetId={currentAsset.id}
              market="US"
              asset={{
                asset_name: currentAsset.asset_name,
                indication: currentAsset.indication || currentAsset.indications?.[0],
                therapeutic_area: currentAsset.therapeutic_area
              }}
            />
          </TabsContent>

          <TabsContent value="scenarios" className="mt-4">
            <ScenarioTab
              assetId={currentAsset.id}
              market="US"
              asset={{
                asset_name: currentAsset.asset_name,
                indication: currentAsset.indication || currentAsset.indications?.[0],
                therapeutic_area: currentAsset.therapeutic_area
              }}
            />
          </TabsContent>

          <TabsContent value="value" className="mt-4">
            <FinancialValueTab
              assetId={currentAsset.id}
              market="US"
              asset={{
                asset_name: currentAsset.asset_name,
                indication: currentAsset.indication || currentAsset.indications?.[0],
                therapeutic_area: currentAsset.therapeutic_area
              }}
            />
          </TabsContent>

          <TabsContent value="governance" className="mt-4">
            <GovernanceTab
              assetId={currentAsset.id}
              assetName={currentAsset.asset_name}
              readOnly={readOnly}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export function AssetCard({ asset, onUpdate, readOnly = false }: AssetCardProps) {
  return (
    <AssetStrategyProvider assetId={asset.id}>
      <AssetCardContent asset={asset} onUpdate={onUpdate} readOnly={readOnly} />
    </AssetStrategyProvider>
  )
}

