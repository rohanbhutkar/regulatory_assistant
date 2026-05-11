import type { Change } from "./collaboration-types"

export interface StudyDesign {
  id: string
  title: string
  status: "design" | "active" | "paused" | "completed"
  therapeuticArea: string
  indication: string
  phase: string
  lastModified: Date
  modifiedBy: string
  recentActivity: string
  referenceTrials: ReferenceTrial[]
  protocolSections: ProtocolSection[]
  sites: SelectedSite[]
  ieCriteria: IECriterion[]
  simulation: SimulationResult | null
}

export interface ReferenceTrial {
  id: string
  nctId: string
  title: string
  indication: string
  phase: string
  primaryEndpoint: string
  ieKeyPoints: string[]
  locations: string[]
  sponsor: string
  selected: boolean
  // Preserve all original trial data for protocol generation
  [key: string]: any  // Allow any TrialTrove fields to be preserved
}

export interface ProtocolSection {
  id: string
  type: string
  title: string
  content: string
  status: "draft" | "review" | "approved"
  lastModified: Date
  changes?: Change[]
  comments: any[] // Renamed Comment to any[] to avoid redeclaration
}

export interface IECriterion {
  id: string
  type: "inclusion" | "exclusion"
  criterion: string
  icdCodes: string[]
  populationImpact: number
  order: number
}

export interface SelectedSite {
  id: string
  name: string
  location: string
  coordinates: { lat: number; lng: number }
  score: number
  historicalPerformance: number
  estimatedEnrollment: number
}

export interface SimulationResult {
  id: string
  enrollmentCurve: EnrollmentDataPoint[]
  milestones: Milestone[]
  riskAssessment: string
  budgetProjection: number
  successProbability: number
}

export interface EnrollmentDataPoint {
  month: number
  enrolled: number
  projected: number
}

export interface Milestone {
  name: string
  date: Date
  status: "pending" | "completed"
}

export interface Comment {
  id: string
  author: string
  content: string
  timestamp: Date
  resolved: boolean
}
