"use client"

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import type { AssetStrategy } from '@/lib/types/asset-strategy-types'
import { toast } from 'sonner'

interface AssetStrategyContextType {
  // Current asset
  currentAsset: AssetStrategy | null
  setCurrentAsset: (asset: AssetStrategy | null) => void
  
  // Tab state - store content for each tab
  tabContent: Record<string, any>
  setTabContent: (tabId: string, content: any) => void
  getTabContent: (tabId: string) => any
  
  // Active tab
  activeTab: string
  setActiveTab: (tab: string) => void
  
  // Save functionality
  saveAsset: () => Promise<void>
  isSaving: boolean
  
  // Auto-save enabled
  autoSaveEnabled: boolean
  setAutoSaveEnabled: (enabled: boolean) => void
}

const AssetStrategyContext = createContext<AssetStrategyContextType | undefined>(undefined)

export function AssetStrategyProvider({ 
  children, 
  assetId 
}: { 
  children: React.ReactNode
  assetId: string
}) {
  const [currentAsset, setCurrentAssetState] = useState<AssetStrategy | null>(null)
  const [tabContent, setTabContentState] = useState<Record<string, any>>({})
  const [activeTab, setActiveTab] = useState('overview')
  const [isSaving, setIsSaving] = useState(false)
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true)
  
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const lastSavedRef = useRef<string>('')
  
  // Load asset and tab content from localStorage on mount
  useEffect(() => {
    if (!assetId) return
    
    try {
      // Load asset data
      const savedAsset = localStorage.getItem(`asset-strategy-${assetId}`)
      if (savedAsset) {
        const parsed = JSON.parse(savedAsset)
        setCurrentAssetState(parsed.asset || null)
        setTabContentState(parsed.tabContent || {})
        console.log(`📂 Loaded asset ${assetId} from localStorage`)
      }
      
      // Load tab content separately (for backward compatibility)
      const savedTabContent = localStorage.getItem(`asset-strategy-tabs-${assetId}`)
      if (savedTabContent) {
        const parsed = JSON.parse(savedTabContent)
        setTabContentState(prev => ({ ...prev, ...parsed }))
      }
    } catch (error) {
      console.error('Error loading asset from localStorage:', error)
    }
  }, [assetId])
  
  // Set tab content
  const setTabContent = useCallback((tabId: string, content: any) => {
    setTabContentState(prev => {
      const updated = {
        ...prev,
        [tabId]: {
          ...prev[tabId],
          ...content,
          lastUpdated: new Date().toISOString()
        }
      }
      
      // Auto-save if enabled
      if (autoSaveEnabled) {
        // Debounce auto-save
        if (saveTimeoutRef.current) {
          clearTimeout(saveTimeoutRef.current)
        }
        
        saveTimeoutRef.current = setTimeout(() => {
          saveToLocalStorage(assetId, currentAsset, updated)
        }, 2000) // Save 2 seconds after last change
      }
      
      return updated
    })
  }, [assetId, currentAsset, autoSaveEnabled])
  
  // Get tab content
  const getTabContent = useCallback((tabId: string) => {
    return tabContent[tabId] || null
  }, [tabContent])
  
  // Helper to strip large fields from tab content
  const stripTabContent = useCallback((tabs: Record<string, any>): Record<string, any> => {
    return Object.entries(tabs).reduce((acc, [key, value]) => {
      if (!value) {
        acc[key] = value
        return acc
      }
      
      // Strip large fields based on tab type
      const stripped: any = { ...value }
      
      // Evidence tab - strip large search results but keep gap analysis
      if (key === 'evidence') {
        if (stripped.searchResults) {
          // Keep only essential search result metadata, not full objects
          stripped.searchResults = {
            hasResults: !!stripped.searchResults,
            trialCount: stripped.searchResults.trials?.length || 0,
            publicationCount: stripped.searchResults.publications?.length || 0,
            webResultCount: stripped.searchResults.web_results?.length || 0,
            // Don't save the actual results - they can be regenerated
          }
        }
        // Keep gap analysis but truncate if too long (>50KB)
        if (stripped.evidenceGapAnalysis && typeof stripped.evidenceGapAnalysis === 'string') {
          const maxLength = 50000 // ~50KB
          if (stripped.evidenceGapAnalysis.length > maxLength) {
            stripped.evidenceGapAnalysis = stripped.evidenceGapAnalysis.substring(0, maxLength) + '\n\n[... truncated for storage ...]'
          }
        }
        // Keep expanded/added IDs (small arrays)
        // Keep search query/type (small strings)
      }
      
      // Pricing tab - strip large price data objects
      if (key === 'pricing') {
        if (stripped.priceData) {
          // Keep only essential price data, not full waterfall objects
          stripped.priceData = {
            net_price: stripped.priceData.net_price,
            list_price: stripped.priceData.list_price,
            // Strip waterfall_components (can be large)
          }
        }
      }
      
      // Other tabs - strip any large objects
      Object.keys(stripped).forEach(k => {
        const val = stripped[k]
        if (val && typeof val === 'object' && !Array.isArray(val)) {
          const valStr = JSON.stringify(val)
          if (valStr.length > 10000) { // >10KB object
            // Replace with placeholder
            stripped[k] = { _stripped: true, _size: valStr.length }
          }
        } else if (Array.isArray(val) && val.length > 100) {
          // Large arrays - keep only first 100 items
          stripped[k] = val.slice(0, 100)
        } else if (typeof val === 'string' && val.length > 50000) {
          // Very long strings - truncate
          stripped[k] = val.substring(0, 50000) + '\n\n[... truncated ...]'
        }
      })
      
      acc[key] = stripped
      return acc
    }, {} as Record<string, any>)
  }, [])
  
  // Save to localStorage helper
  const saveToLocalStorage = useCallback((
    id: string, 
    asset: AssetStrategy | null, 
    tabs: Record<string, any>
  ) => {
    if (!id) return
    
    try {
      // Always strip large fields before saving
      const strippedAsset = asset ? {
        ...asset,
        // Keep only essential fields, remove large generated content
        evidence_artifacts: asset.evidence_artifacts?.slice(0, 10), // Keep only first 10
        // Remove any other large fields that might exist
      } : null
      
      const strippedTabs = stripTabContent(tabs)
      
      const dataToSave = {
        asset: strippedAsset,
        tabContent: strippedTabs,
        lastSaved: new Date().toISOString()
      }
      
      const dataString = JSON.stringify(dataToSave)
      const sizeInMB = new Blob([dataString]).size / 1024 / 1024
      
      // Check size before saving (localStorage limit is ~5MB)
      if (sizeInMB > 4.5) {
        console.warn(`⚠️ Asset data size is still large (${sizeInMB.toFixed(2)}MB) after stripping, attempting further compression`)
        
        // More aggressive stripping - remove tab content entirely if still too large
        const minimalTabs = Object.entries(strippedTabs).reduce((acc, [key, value]) => {
          // Keep only essential state flags, not content
          if (value && typeof value === 'object') {
            acc[key] = {
              lastUpdated: (value as any).lastUpdated,
              // Keep only small flags
              priceGenerated: (value as any).priceGenerated,
              refreshKey: (value as any).refreshKey,
            }
          }
          return acc
        }, {} as Record<string, any>)
        
        const minimalData = {
          asset: strippedAsset,
          tabContent: minimalTabs,
          lastSaved: new Date().toISOString()
        }
        
        const minimalString = JSON.stringify(minimalData)
        const minimalSizeMB = new Blob([minimalString]).size / 1024 / 1024
        
        if (minimalSizeMB > 4.5) {
          // Still too large - only save asset metadata
          const metadataOnly = {
            asset: strippedAsset ? {
              id: strippedAsset.id,
              asset_name: strippedAsset.asset_name,
              therapeutic_area: strippedAsset.therapeutic_area,
              indication: strippedAsset.indication,
              development_stage: strippedAsset.development_stage,
              status: strippedAsset.status,
            } : null,
            tabContent: {},
            lastSaved: new Date().toISOString(),
            _metadataOnly: true
          }
          localStorage.setItem(`asset-strategy-${id}`, JSON.stringify(metadataOnly))
          console.warn('⚠️ Saved only metadata due to size constraints')
        } else {
          localStorage.setItem(`asset-strategy-${id}`, minimalString)
        }
      } else {
        localStorage.setItem(`asset-strategy-${id}`, dataString)
      }
      
      lastSavedRef.current = new Date().toISOString()
      console.log(`💾 Saved asset ${id} to localStorage (${sizeInMB.toFixed(2)}MB)`)
    } catch (error: any) {
      console.error('Error saving to localStorage:', error)
      
      if (error.name === 'QuotaExceededError') {
        // Try to clear old data and save minimal version
        try {
          // Clear this asset's old data
          localStorage.removeItem(`asset-strategy-${id}`)
          localStorage.removeItem(`asset-strategy-tabs-${id}`)
          
          // Save only essential metadata
          const minimalData = {
            asset: asset ? {
              id: asset.id,
              asset_name: asset.asset_name,
              therapeutic_area: asset.therapeutic_area,
              indication: asset.indication,
              development_stage: asset.development_stage,
              status: asset.status,
            } : null,
            tabContent: {},
            lastSaved: new Date().toISOString(),
            _quotaExceeded: true
          }
          localStorage.setItem(`asset-strategy-${id}`, JSON.stringify(minimalData))
          toast.warning('Storage quota exceeded. Saved only essential data. Some tab content may need to be regenerated.')
        } catch (retryError) {
          toast.error('Storage quota exceeded. Please clear browser storage or use a different browser.')
        }
      }
    }
  }, [stripTabContent])
  
  // Manual save function
  const saveAsset = useCallback(async () => {
    if (!assetId || !currentAsset) {
      toast.error('No asset to save')
      return
    }
    
    setIsSaving(true)
    
    try {
      // Save to localStorage
      saveToLocalStorage(assetId, currentAsset, tabContent)
      
      // Also save to backend if onUpdate callback is available
      // This will be handled by the parent component
      
      toast.success('Asset saved successfully!')
    } catch (error: any) {
      console.error('Error saving asset:', error)
      toast.error('Failed to save asset')
    } finally {
      setIsSaving(false)
    }
  }, [assetId, currentAsset, tabContent, saveToLocalStorage])
  
  // Set current asset (with auto-save)
  const setCurrentAsset = useCallback((asset: AssetStrategy | null) => {
    setCurrentAssetState(asset)
    
    // Auto-save if enabled
    if (autoSaveEnabled && asset) {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      
      saveTimeoutRef.current = setTimeout(() => {
        saveToLocalStorage(assetId, asset, tabContent)
      }, 2000)
    }
  }, [assetId, tabContent, autoSaveEnabled, saveToLocalStorage])
  
  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])
  
  const value: AssetStrategyContextType = {
    currentAsset,
    setCurrentAsset,
    tabContent,
    setTabContent,
    getTabContent,
    activeTab,
    setActiveTab,
    saveAsset,
    isSaving,
    autoSaveEnabled,
    setAutoSaveEnabled
  }
  
  return (
    <AssetStrategyContext.Provider value={value}>
      {children}
    </AssetStrategyContext.Provider>
  )
}

export function useAssetStrategy() {
  const context = useContext(AssetStrategyContext)
  if (context === undefined) {
    throw new Error('useAssetStrategy must be used within an AssetStrategyProvider')
  }
  return context
}
