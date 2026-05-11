"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Timeline, CheckCircle, Clock, XCircle } from 'lucide-react'
import type { DecisionCut, Approval } from '@/lib/types/asset-strategy-types'
import { DecisionCutManager } from './decision-cut-manager'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'
import { ReportGenerator } from './report-generator'

interface GovernanceTabProps {
  assetId: string
  assetName?: string
  readOnly?: boolean
}

export function GovernanceTab({ assetId, assetName, readOnly = false }: GovernanceTabProps) {
  const [decisionCuts, setDecisionCuts] = useState<DecisionCut[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])

  useEffect(() => {
    loadDecisionCuts()
    loadApprovals()
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

  const loadApprovals = async () => {
    try {
      const response = await fetch(assetStrategyAPI.getApprovals(assetId))
      if (response.ok) {
        const data = await response.json()
        setApprovals(data)
      }
    } catch (error) {
      console.error('Failed to load approvals:', error)
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
    <div className="space-y-6">
      {assetName && (
        <ReportGenerator assetId={assetId} assetName={assetName} />
      )}
      <DecisionCutManager assetId={assetId} readOnly={readOnly} />

      {/* Decision Cut History */}
      <Card>
        <CardHeader>
          <CardTitle>Decision Cut History</CardTitle>
          <CardDescription>Chronological timeline of all decision cuts</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {decisionCuts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No decision cuts created yet
              </div>
            ) : (
              decisionCuts.map((cut) => (
                <div key={cut.id} className="flex items-start gap-4 border-l-2 border-gray-200 pl-4">
                  <Timeline className="h-5 w-5 text-gray-400 mt-1" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{cut.cut_name}</div>
                        <div className="text-sm text-gray-500">
                          {new Date(cut.frozen_at).toLocaleDateString()} by {cut.frozen_by}
                        </div>
                        {cut.cut_description && (
                          <div className="text-sm text-gray-600 mt-1">{cut.cut_description}</div>
                        )}
                      </div>
                      {getStatusBadge(cut.status)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Approval Status */}
      <Card>
        <CardHeader>
          <CardTitle>Approval Status</CardTitle>
          <CardDescription>Current and pending approvals</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {approvals.length === 0 ? (
              <div className="text-center py-4 text-gray-500">No approvals</div>
            ) : (
              approvals.map((approval) => (
                <div key={approval.id} className="flex items-center justify-between p-3 border rounded">
                  <div className="flex items-center gap-3">
                    {approval.status === 'approved' && <CheckCircle className="h-5 w-5 text-green-500" />}
                    {approval.status === 'pending' && <Clock className="h-5 w-5 text-yellow-500" />}
                    {approval.status === 'rejected' && <XCircle className="h-5 w-5 text-red-500" />}
                    <div>
                      <div className="font-medium">Approver: {approval.approver_id}</div>
                      {approval.comments && (
                        <div className="text-sm text-gray-600">{approval.comments}</div>
                      )}
                    </div>
                  </div>
                  <Badge>{approval.status.toUpperCase()}</Badge>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

