export const API_CONFIG = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001",
  wsURL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws",
  timeout: 30000,
  retryAttempts: 3,
}

export const ENDPOINTS = {
  // Assets
  assets: "/api/assets/",
  assetDetail: (id: string) => `/api/assets/${id}`,
  portfolioStats: "/api/assets/portfolio/stats",

  // Asset Strategy
  assetStrategy: {
    assets: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/assets/${id}`,
    assetAssumptions: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/assets/${id}/assumptions`,
    assetEvidence: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/assets/${id}/evidence`,
    assetDecisionCuts: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/assets/${id}/decision-cuts`,
    assetApprovals: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/assets/${id}/approvals`,
    assumptionSet: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/assumption-sets/${id}`,
    evidence: (id: string) => `${API_CONFIG.baseURL}/api/asset-strategy/evidence/${id}`,
    pricingComparators: (assetId: string, market: string) => `${API_CONFIG.baseURL}/api/asset-strategy/pricing/comparators?asset_id=${assetId}&market=${market}`,
    pricingPrediction: (assetId: string, market: string) => `${API_CONFIG.baseURL}/api/asset-strategy/pricing/${assetId}/${market}`,
    htaPathway: (assetId: string, market: string) => `${API_CONFIG.baseURL}/api/asset-strategy/hta/pathway/${assetId}/${market}`,
    htaAccessRisk: (assetId: string, market: string) => `${API_CONFIG.baseURL}/api/asset-strategy/hta/access-risk/${assetId}/${market}`,
  },

  // Studies
  studies: "/api/studies/",
  studyDetail: (id: string) => `/api/studies/${id}`,
  referenceTrials: "/api/trials/reference",

  // Commercial
  revenueSimulation: "/api/commercial/simulate",
  marketData: (indication: string) => `/api/commercial/market/${indication}`,

  // Chat
  chatMessage: "/api/chat/message",
  chatHistory: (sessionId: string) => `/api/chat/history/${sessionId}`,

  // Agents
  agents: "/api/agents/",
  agentQuery: "/api/agents/query",

  regulatoryDocuments: `${API_CONFIG.baseURL}/api/regulatory/documents`,
}
