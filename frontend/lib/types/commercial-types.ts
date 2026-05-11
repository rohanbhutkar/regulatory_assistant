export interface RevenueSimulation {
  id: string
  assetName: string
  indication: string
  launchDate: Date
  pricing: PricingAssumptions
  coverage: CoverageAssumptions
  patientPopulation: PopulationAssumptions
  revenueCurve: RevenueDataPoint[]
  sensitivityAnalysis: SensitivityResult[]
}

export interface PricingAssumptions {
  listPrice: number
  netPrice: number
  discountRate: number
}

export interface CoverageAssumptions {
  commercialCoverage: number
  medicareCoverage: number
  medicaidCoverage: number
  timeToMedicareCoverage: number // months
}

export interface PopulationAssumptions {
  totalEligible: number
  marketPenetration: number
  adherenceRate: number
  treatmentDuration: number // months
}

export interface RevenueDataPoint {
  quarter: string
  revenue: number
  patients: number
  marketShare: number
}

export interface SensitivityResult {
  parameter: string
  baseCase: number
  lowCase: number
  highCase: number
  impact: number
}

export interface PatientFunnel {
  stage: string
  patients: number
  percentage: number
  color: string
}

export interface CommercialModel {
  id: string
  name: string
  assetName: string
  indication: string
  status: "draft" | "active" | "archived"
  lastModified: Date
  modifiedBy: string
  recentActivity: string
  simulation: RevenueSimulation
}
