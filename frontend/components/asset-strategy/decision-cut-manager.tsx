"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Scissors, Eye, FileDiff, Download, Trash2 } from 'lucide-react'
import type { DecisionCut, CreateDecisionCutRequest } from '@/lib/types/asset-strategy-types'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'

interface DecisionCutManagerProps {
  assetId: string
  readOnly?: boolean
}

export function DecisionCutManager({ assetId, readOnly = false }: DecisionCutManagerProps) {
  const [decisionCuts, setDecisionCuts] = useState<DecisionCut[]>([])
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [cutName, setCutName] = useState('')
  const [cutDescription, setCutDescription] = useState('')
  const [requiredApprovers, setRequiredApprovers] = useState<string[]>([])
  const [notes, setNotes] = useState('')

  useEffect(() => {
    loadDecisionCuts()
  }, [assetId])

  const loadDecisionCuts = async () => {
    try {
      const response = await fetch(assetStrategyAPI.getDecisionCuts(assetId))
      if (response.ok) {
        const data = await response.json()
        setDecisionCuts(data)
      }
    } catch (error) {
      console.error('Failed to load decision cuts:', error)
    }
  }

  const handleCreateCut = async () => {
    if (!cutName.trim()) {
      alert('Please enter a cut name')
      return
    }

    try {
      const request: CreateDecisionCutRequest = {
        asset_id: assetId,
        cut_name: cutName,
        cut_description: cutDescription || undefined,
        required_approvers: requiredApprovers,
        notes: notes || undefined
      }

      const response = await fetch(`/api/asset-strategy/assets/${assetId}/decision-cuts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      })

      if (response.ok) {
        setIsDialogOpen(false)
        setCutName('')
        setCutDescription('')
        setRequiredApprovers([])
        setNotes('')
        await loadDecisionCuts()
      }
    } catch (error) {
      console.error('Failed to create decision cut:', error)
    }
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-800',
      pending_approval: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      superseded: 'bg-blue-100 text-blue-800'
    }
    return (
      <Badge className={styles[status as keyof typeof styles] || ''}>
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Decision Cuts</CardTitle>
            <CardDescription>Immutable snapshots of asset state at key decision gates</CardDescription>
          </div>
          {!readOnly && (
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Scissors className="h-4 w-4 mr-2" />
                  Freeze New Cut
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Decision Cut</DialogTitle>
                  <DialogDescription>
                    Create an immutable snapshot of the current asset state
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label htmlFor="cut_name">Cut Name *</Label>
                    <Input
                      id="cut_name"
                      value={cutName}
                      onChange={(e) => setCutName(e.target.value)}
                      placeholder="e.g., Early BD Screen, Pre-PhIII, Pre-Launch"
                    />
                  </div>
                  <div>
                    <Label htmlFor="cut_description">Description</Label>
                    <Textarea
                      id="cut_description"
                      value={cutDescription}
                      onChange={(e) => setCutDescription(e.target.value)}
                      placeholder="Optional description of this decision cut"
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label htmlFor="required_approvers">Required Approvers</Label>
                    <Input
                      id="required_approvers"
                      value={requiredApprovers.join(', ')}
                      onChange={(e) => setRequiredApprovers(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                      placeholder="Comma-separated user IDs"
                    />
                  </div>
                  <div>
                    <Label htmlFor="notes">Notes/Justification</Label>
                    <Textarea
                      id="notes"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Optional notes or justification"
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateCut}>
                    Create Cut
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {decisionCuts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No decision cuts created yet
            </div>
          ) : (
            decisionCuts.map((cut) => (
              <div key={cut.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <div className="font-medium">{cut.cut_name}</div>
                    {getStatusBadge(cut.status)}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {new Date(cut.frozen_at).toLocaleDateString()} by {cut.frozen_by}
                  </div>
                  {cut.cut_description && (
                    <div className="text-sm text-gray-600 mt-1">{cut.cut_description}</div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline">
                    <Eye className="h-4 w-4 mr-2" />
                    View
                  </Button>
                  {decisionCuts.length > 1 && (
                    <Button size="sm" variant="outline">
                      <FileDiff className="h-4 w-4 mr-2" />
                      Compare
                    </Button>
                  )}
                  <Button size="sm" variant="outline">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                  {cut.status === 'draft' && !readOnly && (
                    <Button size="sm" variant="outline" className="text-red-600">
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}

