/**
 * Asset Strategy Types - Extended types for Phase 1
 */

export type DevelopmentStage = 
  | 'discovery' 
  | 'preclinical' 
  | 'phase_i' 
  | 'phase_ii' 
  | 'phase_iii' 
  | 'pre_launch' 
  | 'launched'

export type AssetStatus = 'go' | 'no_go' | 'conditional_go' | 'revisit'

export type DecisionCutStatus = 'draft' | 'pending_approval' | 'approved' | 'superseded'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'delegated'

export type EvidenceArtifactType = 'tpp' | 'protocol' | 'publication' | 'submission'

export interface AssetStrategy {
  id: string
  asset_name: string
  therapeutic_area: string
  indication?: string
  indications?: string[]
  moa?: string // Mechanism of Action
  roa?: string // Route of Administration
  subpopulations?: string[]
  development_stage?: DevelopmentStage
  status?: AssetStatus
  launch_sequence?: Array<{ market: string; sequence: number }>
  
  // Existing fields
  trial_phase?: string
  cost_per_patient?: number
  total_estimated_cost?: number
  projected_revenue?: number
  current_trials?: Array<{
    id: string
    name: string
    nctId?: string
    phase?: string
    status?: string
    enrollmentTarget?: number
    enrollmentCurrent?: number
    sites?: number
    countries?: string[]
  }>
  last_updated: string
  created_by: string
  
  // Timeline fields
  expected_launch_dates?: Record<string, string>
  key_milestone_dates?: Record<string, string>
}

export interface DecisionCut {
  id: string
  asset_id: string
  cut_name: string
  cut_description?: string
  frozen_at: string
  frozen_by: string
  snapshot_data: Record<string, any>
  previous_cut_id?: string
  status: DecisionCutStatus
  created_at: string
}

export interface DecisionCutDiff {
  cut1_id: string
  cut2_id: string
  changes: Record<string, any>
  added_items: string[]
  removed_items: string[]
  modified_items: string[]
  impact_assessment?: {
    needs_recalculation?: string[]
    affected_modules?: string[]
  }
}

export interface Approval {
  id: string
  decision_cut_id: string
  approver_id: string
  status: ApprovalStatus
  comments?: string
  approved_at?: string
  created_at: string
}

export interface ApprovalRequest {
  decision_cut_id: string
  required_approvers: string[]
  optional_approvers?: string[]
  priority?: 'normal' | 'high' | 'urgent'
  notes?: string
}

export interface EvidenceArtifact {
  id: string
  asset_id: string
  artifact_type: EvidenceArtifactType
  file_name: string
  file_path: string
  file_size?: number
  uploaded_by: string
  uploaded_at: string
  extracted_entities?: Record<string, any>
  linked_fields?: Record<string, any>
  metadata?: Record<string, any>
  confidence_score?: number
}

export interface Comparator {
  drug: string
  indication: string
  market: string
  rationale?: string
  source?: string
}

export interface AssumptionSet {
  id: string
  asset_id: string
  name: string
  is_locked: boolean
  comparator_set: Comparator[]
  benefit_hypothesis?: string
  uptake_archetype?: 'fast' | 'moderate' | 'slow'
  uptake_parameters?: Record<string, any>
  created_at: string
  updated_at: string
  version: number
}

export interface CreateAssetRequest {
  asset_name: string
  therapeutic_area: string
  indication?: string
  moa?: string
  roa?: string
  development_stage?: DevelopmentStage
  status?: AssetStatus
}

export interface UpdateAssetRequest {
  asset_name?: string
  therapeutic_area?: string
  indication?: string
  indications?: string[]
  moa?: string
  roa?: string
  subpopulations?: string[]
  development_stage?: DevelopmentStage
  status?: AssetStatus
  launch_sequence?: Array<{ market: string; sequence: number }>
  expected_launch_dates?: Record<string, string>
  key_milestone_dates?: Record<string, string>
}

export interface CreateDecisionCutRequest {
  asset_id: string
  cut_name: string
  cut_description?: string
  required_approvers: string[]
  notes?: string
}


