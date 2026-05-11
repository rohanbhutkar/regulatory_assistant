"use client"

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Header } from '@/components/layout/header'
import { Button } from '@/components/ui/button'
import { AssetCard } from '@/components/asset-strategy/asset-card'
import { ArrowLeft, Loader2 } from 'lucide-react'
import type { AssetStrategy } from '@/lib/types/asset-strategy-types'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'

export default function AssetStrategyPage() {
  const params = useParams()
  const router = useRouter()
  const assetId = params.assetId as string
  
  const [asset, setAsset] = useState<AssetStrategy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAsset()
  }, [assetId])

  const loadAsset = async () => {
    try {
      setLoading(true)
      const response = await fetch(assetStrategyAPI.getAsset(assetId))
      
      if (!response.ok) {
        throw new Error('Failed to load asset')
      }
      
      const data = await response.json()
      setAsset(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load asset')
    } finally {
      setLoading(false)
    }
  }

  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  const handleUpdate = useCallback(async (updatedAsset: AssetStrategy) => {
    // Optimistically update local state first (but don't cause re-render of child)
    // The child component manages its own state, so we don't need to update here
    // setAsset(updatedAsset) // Commented out to prevent re-renders
    
    // Debounce backend saves
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await fetch(assetStrategyAPI.updateAsset(assetId), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedAsset)
        })

        if (!response.ok) {
          // If save fails, reload from server to get correct state
          console.error('Failed to update asset, reloading...')
          await loadAsset()
        } else {
          // Only update local state after successful save
          setAsset(updatedAsset)
        }
      } catch (err) {
        console.error('Failed to update asset:', err)
        // On error, reload from server
        await loadAsset()
      }
    }, 1000) // Wait 1 second after user stops typing before saving
  }, [assetId])
  
  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  if (loading) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  if (error || !asset) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-600 mb-4">{error || 'Asset not found'}</p>
            <Button onClick={() => router.push('/asset-management')}>
              Back to Asset Management
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-4 sm:px-6 lg:px-8 py-4 sm:py-6 border-b border-border/40">
          <Button
            variant="ghost"
            onClick={() => router.push('/asset-management')}
            className="mb-4 sm:mb-6 -ml-2 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Asset Management
          </Button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight text-foreground mb-2">
                {asset.asset_name}
              </h1>
              <p className="text-base sm:text-lg text-muted-foreground">
                Asset Strategy & Management
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
          <AssetCard asset={asset} onUpdate={handleUpdate} />
        </div>
      </div>
    </div>
  )
}

