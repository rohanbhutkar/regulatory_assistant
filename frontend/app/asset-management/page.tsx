"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/layout/header"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PortfolioStatsCards } from "@/components/asset-management/portfolio-stats"
import { AssetOverviewTable } from "@/components/asset-management/asset-overview-table"
import { ResearchAgentChat } from "@/components/chat/research-agent-chat"
import { MOCK_PORTFOLIO_STATS } from "@/lib/data/mock-assets"
import { ArrowLeft, Plus, Trash2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { assetStrategyAPI } from "@/lib/utils/asset-strategy-api"
import type { AssetStrategy } from "@/lib/types/asset-strategy-types"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export default function AssetManagementPage() {
  const router = useRouter()
  const [assets, setAssets] = useState<AssetStrategy[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [assetToDelete, setAssetToDelete] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newAsset, setNewAsset] = useState({
    asset_name: '',
    therapeutic_area: '',
    indication: '',
    development_stage: 'phase_ii' as const
  })

  useEffect(() => {
    loadAssets()
  }, [])

  const loadAssets = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/assets`)
      if (response.ok) {
        const data = await response.json()
        setAssets(data)
      }
    } catch (error) {
      console.error('Failed to load assets:', error)
      toast.error('Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  const handleAssetSelect = (asset: any) => {
    router.push(`/asset-strategy/${asset.id}`)
  }

  const handleBulkAction = (assetIds: string[], action: string) => {
    console.log('Bulk action:', action, 'on assets:', assetIds)
  }

  const handleCreateAsset = async () => {
    if (!newAsset.asset_name || !newAsset.therapeutic_area) {
      toast.error('Please provide asset name and therapeutic area')
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/assets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_name: newAsset.asset_name,
          therapeutic_area: newAsset.therapeutic_area,
          indication: newAsset.indication || undefined,
          development_stage: newAsset.development_stage
        })
      })

      if (response.ok) {
        const createdAsset = await response.json()
        setAssets([...assets, createdAsset])
        setCreateDialogOpen(false)
        setNewAsset({ asset_name: '', therapeutic_area: '', indication: '', development_stage: 'phase_ii' })
        toast.success('Asset created successfully')
      } else {
        toast.error('Failed to create asset')
      }
    } catch (error) {
      console.error('Failed to create asset:', error)
      toast.error('Failed to create asset')
    }
  }

  const handleDeleteClick = (assetId: string) => {
    setAssetToDelete(assetId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!assetToDelete) return

    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/assets/${assetToDelete}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setAssets(assets.filter(a => a.id !== assetToDelete))
        setDeleteDialogOpen(false)
        setAssetToDelete(null)
        toast.success('Asset deleted successfully')
      } else {
        toast.error('Failed to delete asset')
      }
    } catch (error) {
      console.error('Failed to delete asset:', error)
      toast.error('Failed to delete asset')
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div className="px-4 sm:px-6 lg:px-8 py-4 sm:py-6 border-b border-border/40 shrink-0">
          <Button
            variant="ghost"
            onClick={() => router.push("/")}
            className="mb-4 sm:mb-6 -ml-2 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Personas
          </Button>

          <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight text-foreground mb-2">
                Asset Management
              </h1>
              <p className="text-base sm:text-lg text-muted-foreground">Portfolio oversight and investment tracking</p>
            </div>
            <div className="flex items-center gap-3">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setCreateDialogOpen(true)}
                className="gap-2"
              >
                <Plus className="h-4 w-4" />
                New Asset
              </Button>
              <Button variant="outline" size="sm">
                Export Report
              </Button>
            </div>
          </div>
        </div>
                  
        {/* Main Content */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <Tabs defaultValue="dashboard" className="h-full flex flex-col min-h-0">
            <div className="px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 border-b border-border/40 overflow-x-auto">
              <TabsList className="bg-transparent border-b-0 p-0 h-auto inline-flex min-w-full sm:min-w-0">
                <TabsTrigger
                  value="dashboard"
                  className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 whitespace-nowrap"
                >
                  Dashboard
                </TabsTrigger>
                <TabsTrigger
                  value="research"
                  className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-foreground rounded-none px-3 sm:px-4 pb-3 whitespace-nowrap"
                >
                  Research Agent
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent
              value="dashboard"
              className="flex-1 overflow-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 space-y-6 sm:space-y-8 mt-0"
            >
              <PortfolioStatsCards stats={MOCK_PORTFOLIO_STATS} />
              {loading ? (
                <div className="text-center py-12">Loading assets...</div>
              ) : (
                <AssetOverviewTable 
                  assets={assets} 
                  onAssetSelect={handleAssetSelect}
                  onBulkAction={handleBulkAction}
                  onDeleteAsset={handleDeleteClick}
                />
              )}
            </TabsContent>

            <TabsContent value="research" className="flex-1 min-h-0 overflow-hidden mt-0">
              <ResearchAgentChat />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Create Asset Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Asset</DialogTitle>
            <DialogDescription>
              Add a new asset to your portfolio
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="asset_name">Asset Name *</Label>
              <Input
                id="asset_name"
                value={newAsset.asset_name}
                onChange={(e) => setNewAsset({ ...newAsset, asset_name: e.target.value })}
                placeholder="e.g., BIO-2847 (Pembrolizumab NSCLC Program)"
              />
            </div>
            <div>
              <Label htmlFor="therapeutic_area">Therapeutic Area *</Label>
              <Input
                id="therapeutic_area"
                value={newAsset.therapeutic_area}
                onChange={(e) => setNewAsset({ ...newAsset, therapeutic_area: e.target.value })}
                placeholder="e.g., Oncology"
              />
            </div>
            <div>
              <Label htmlFor="indication">Indication</Label>
              <Input
                id="indication"
                value={newAsset.indication}
                onChange={(e) => setNewAsset({ ...newAsset, indication: e.target.value })}
                placeholder="e.g., Non-Small Cell Lung Cancer"
              />
            </div>
            <div>
              <Label htmlFor="development_stage">Development Stage</Label>
              <select
                id="development_stage"
                value={newAsset.development_stage}
                onChange={(e) => setNewAsset({ ...newAsset, development_stage: e.target.value as any })}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="discovery">Discovery</option>
                <option value="preclinical">Preclinical</option>
                <option value="phase_i">Phase I</option>
                <option value="phase_ii">Phase II</option>
                <option value="phase_iii">Phase III</option>
                <option value="pre_launch">Pre-Launch</option>
                <option value="launched">Launched</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateAsset}>
              Create Asset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Asset?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this asset? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}











