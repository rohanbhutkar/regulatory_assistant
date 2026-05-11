/**
 * CPP (Clinical Per-Patient) TypeScript Types
 * Generated from backend models
 */

// Enums
export enum StudyType {
  INTERVENTIONAL = "Interventional",
  OBSERVATIONAL = "Observational",
  EARLY_TERMINATION = "Early Termination"
}

export enum Phase {
  PHASE_I = "Phase I",
  PHASE_II = "Phase II",
  PHASE_III = "Phase III",
  PHASE_IV = "Phase IV"
}

export enum RuleType {
  GOLDEN = "Golden",
  COUNTRY = "Country",
  INDICATION = "Indication"
}

export enum RuleAction {
  ADD_COST = "add_cost",
  MULTIPLY = "multiply",
  ADD_PERCENTAGE = "add_percentage",
  SET_VALUE = "set_value"
}

// OPAL Models
export interface OPALInput {
  study_type: StudyType
  phase: Phase
  num_arms: number
  therapeutic_area?: string
  has_tissue_biopsy?: boolean
  has_pk_draws?: boolean
  has_specialized_procedures?: boolean
  has_complex_assessments?: boolean
  num_special_procedures?: number
  num_complex_procedures?: number
}

export interface StaffDistribution {
  [visitType: string]: {
    PI: number
    Nurse: number
    CRC: number
    CRA: number
  }
}

export interface OPALResult {
  raw_score: number
  modifier_score: number
  adjusted_score: number
  total_overhead_hours: number
  staff_distribution: StaffDistribution
  calculation_details: Record<string, any>
}

// Procedure Models
export interface ProcedureMatch {
  raw_text: string
  normalized_text: string
  matched_code?: string
  matched_description?: string
  confidence_score: number
  match_type: string
  alternatives: Array<{
    code: string
    description: string
    score: number
  }>
  requires_review: boolean
}

export interface VisitProcedure {
  visit_name: string
  visit_number: number
  procedure_code: string
  procedure_name: string
  frequency: number
  is_optional?: boolean
  probability?: number
}

// Pricing Models
export interface SPUPrice {
  procedure_code: string
  country_code: string
  local_price: number
  currency: string
  effective_date?: string
  source: string
}

// Matrix Models
export interface CostMatrix {
  procedures: string[]
  visits: string[]
  frequency_matrix: number[][]
  cost_vector: number[]
  cost_matrix: number[][]
  per_visit_totals: number[]
  per_procedure_totals: number[]
  grand_total: number
}

// Rules Models
export interface Rule {
  id: string
  name: string
  rule_type: RuleType
  description: string
  conditions: Record<string, any>
  action: RuleAction
  value: number
  priority: number
  active: boolean
}

export interface RuleApplication {
  rule_id: string
  rule_name: string
  applied_value: number
  context: Record<string, any>
}

// CPP Models
export interface CPPBreakdown {
  direct_procedures: number
  staff_overhead: number
  administration: number
  travel_stipend: number
  other_direct_costs: number
  country_adjustments: number
  total_before_overhead: number
  overhead_percentage: number
  overhead_amount: number
  total_cpp: number
}

export interface CPPResult {
  total_cpp: number
  currency: string
  country_code: string
  breakdown: CPPBreakdown
  opal_result?: OPALResult
  procedure_costs: Array<{
    code: string
    total_cost: number
  }>
  rules_applied: RuleApplication[]
  matrix_data?: CostMatrix
  calculation_metadata: Record<string, any>
}

export interface CPPInput {
  indication: string
  phase: string
  country_code: string
  procedures: VisitProcedure[]
  opal_input: OPALInput
  study_context?: Record<string, any>
}

// API Response Types
export interface CPPApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface ProcedureMappingResponse {
  success: boolean
  match: ProcedureMatch
}

export interface ProcedureMappingBatchResponse {
  success: boolean
  matches: ProcedureMatch[]
  count: number
}

export interface OPALCalculationResponse {
  success: boolean
  opal: OPALResult
}

export interface PricingResponse {
  success: boolean
  country_code: string
  prices: Record<string, SPUPrice | null>
  count_found: number
  count_missing: number
}

export interface MatrixCalculationResponse {
  success: boolean
  matrix: CostMatrix
  grand_total: number
  currency: string
}

export interface CPPCalculationResponse {
  success: boolean
  cpp: CPPResult
}

export interface RulesPreviewResponse {
  success: boolean
  rules: Array<{
    id: string
    name: string
    type: string
    description: string
    action: string
    value: number
    priority: number
  }>
  count: number
}







