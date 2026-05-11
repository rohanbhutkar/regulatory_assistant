"use client"

import React from 'react'
import { OperationType, OperationStatus } from '@/lib/contexts/activity-context'
import { Loader2, Sparkles, Search, Database, Calculator, MapPin, Users, DollarSign, FileText, CheckCircle2, XCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ActivityIconProps {
  type: OperationType
  status: OperationStatus
  className?: string
}

const iconMap: Record<OperationType, React.ComponentType<{ className?: string }>> = {
  ai_generation: Sparkles,
  data_search: Search,
  simulation: Calculator,
  evidence_discovery: Database,
  budget_calc: Calculator,
  site_filtering: MapPin,
  population_analysis: Users,
  pricing_calc: DollarSign,
  hta_assessment: FileText
}

export function ActivityIcon({ type, status, className }: ActivityIconProps) {
  const Icon = iconMap[type] || Sparkles
  
  if (status === 'in_progress' || status === 'pending') {
    return <Loader2 className={cn("animate-spin", className)} />
  }
  
  if (status === 'completed') {
    return <CheckCircle2 className={cn("text-green-500", className)} />
  }
  
  if (status === 'error') {
    return <XCircle className={cn("text-red-500", className)} />
  }
  
  if (status === 'cancelled') {
    return <X className={cn("text-gray-500", className)} />
  }
  
  return <Icon className={className} />
}
