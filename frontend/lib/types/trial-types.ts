export interface Trial {
  id: string
  title: string
  status: 'design' | 'active' | 'paused' | 'completed'
  therapeutic_area: string
  phase: string
  last_modified: string
  last_modified_by: string
  recent_activity: string
  assigned_to: string[]
}

export interface TrialFilters {
  status?: string[]
  therapeutic_area?: string[]
  phase?: string[]
  last_modified_range?: {
    start: string
    end: string
  }
  assigned_to?: string[]
}

export interface TrialsResponse {
  trials: Trial[]
  total_count: number
  filters_applied: TrialFilters
}




























