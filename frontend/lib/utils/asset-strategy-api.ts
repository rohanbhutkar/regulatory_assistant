/**
 * Helper functions for Asset Strategy API calls
 * All routes use the full backend URL since Next.js treats /api/* as Next.js API routes
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export const assetStrategyAPI = {
  // Asset endpoints
  getAsset: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}`,
  updateAsset: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}`,
  
  // Decision cuts
  getDecisionCuts: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/decision-cuts`,
  createDecisionCut: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/decision-cuts`,
  getDecisionCut: (cutId: string) => `${API_BASE_URL}/api/asset-strategy/decision-cuts/${cutId}`,
  getDecisionCutDiff: (cutId: string) => `${API_BASE_URL}/api/asset-strategy/decision-cuts/${cutId}/diff`,
  
  // Approvals
  getApprovals: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/approvals`,
  createApproval: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/approvals`,
  approveDecisionCut: (approvalId: string) => `${API_BASE_URL}/api/asset-strategy/approvals/${approvalId}/approve`,
  rejectDecisionCut: (approvalId: string) => `${API_BASE_URL}/api/asset-strategy/approvals/${approvalId}/reject`,
  
  // Evidence
  getEvidence: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/evidence`,
  createEvidence: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/evidence`,
  getEvidenceArtifact: (artifactId: string) => `${API_BASE_URL}/api/asset-strategy/evidence/${artifactId}`,
  deleteEvidence: (artifactId: string) => `${API_BASE_URL}/api/asset-strategy/evidence/${artifactId}`,
  
  // Assumptions
  getAssumptions: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/assumptions`,
  createAssumptionSet: (assetId: string) => `${API_BASE_URL}/api/asset-strategy/assets/${assetId}/assumptions`,
  updateAssumptionSet: (setId: string) => `${API_BASE_URL}/api/asset-strategy/assumption-sets/${setId}`,
  lockAssumptionSet: (setId: string) => `${API_BASE_URL}/api/asset-strategy/assumption-sets/${setId}/lock`,
  unlockAssumptionSet: (setId: string) => `${API_BASE_URL}/api/asset-strategy/assumption-sets/${setId}/unlock`,
  cloneAssumptionSet: (setId: string) => `${API_BASE_URL}/api/asset-strategy/assumption-sets/${setId}/clone`,
  
  // Pricing
  getPricePrediction: (assetId: string, market: string) => `${API_BASE_URL}/api/asset-strategy/pricing/${assetId}/${market}`,
  getComparators: (assetId: string, market: string) => `${API_BASE_URL}/api/asset-strategy/pricing/comparators?asset_id=${assetId}&market=${market}`,
  
  // HTA
  getHTAPathway: (assetId: string, market: string) => `${API_BASE_URL}/api/asset-strategy/hta/pathway/${assetId}/${market}`,
  getAccessRisk: (assetId: string, market: string) => `${API_BASE_URL}/api/asset-strategy/hta/access-risk/${assetId}/${market}`,
  
  // AI Generation
  generateAssetOverview: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/overview`,
  generateAssumptionSet: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/assumption-set`,
  generateComparators: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/comparators`,
  generateBenefitHypothesis: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/benefit-hypothesis`,
  analyzeEvidenceGaps: () => `${API_BASE_URL}/api/asset-strategy/ai/analyze/evidence-gaps`,
  generatePricePotential: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/price-potential`,
  suggestPricingParameters: () => `${API_BASE_URL}/api/asset-strategy/ai/suggest/pricing-parameters`,
  generateHTAAssessment: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/hta-assessment`,
  discoverEvidence: () => `${API_BASE_URL}/api/asset-strategy/ai/discover/evidence`,
  generateTimeline: () => `${API_BASE_URL}/api/asset-strategy/ai/generate/timeline`,
}

