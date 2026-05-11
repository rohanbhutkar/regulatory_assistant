export interface PortfolioStats {
  totalAssets: number
  activeTrials: number
  totalInvestment: number
  projectedRevenue: number
  highRiskAssets: number
}

export interface Asset {
  id: string
  asset_name: string
  therapeutic_area: string
  trial_phase: string
  molecule?: string
  indication?: string
  cost_per_patient: number
  total_estimated_cost: number
  projected_revenue: number
  status: 'active' | 'paused' | 'completed'
  current_trials: Array<{
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
}

export interface AssetFilters {
  therapeutic_area?: string[]
  trial_phase?: string[]
  status?: string[]
  cost_range?: {
    min: number
    max: number
  }
  revenue_range?: {
    min: number
    max: number
  }
}

export interface PortfolioSummary {
  total_investment: number
  projected_revenue: number
  roi_percentage?: number
  active_assets: number
  high_risk_assets: number
  therapeutic_area_distribution: Record<string, number>
  phase_distribution: Record<string, number>
  cost_trends: Array<{
    month: string
    cost: number
  }>
}

export interface AssetsResponse {
  assets: Asset[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  filters_applied: AssetFilters
}
