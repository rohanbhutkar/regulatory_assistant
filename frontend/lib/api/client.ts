const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

export class APIClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`[v0] API request failed for ${endpoint}:`, error)
      throw error
    }
  }

  // Persona endpoints
  async getPersonas() {
    return this.request("/api/personas/")
  }

  // Asset Management endpoints
  async getAssets() {
    return this.request("/api/assets/")
  }

  async getAsset(id: string) {
    return this.request(`/api/assets/${id}`)
  }

  async getPortfolioStats() {
    return this.request("/api/assets/portfolio/stats")
  }

  // Study Designer endpoints
  async getStudies() {
    return this.request("/api/studies/")
  }

  async getStudy(id: string) {
    return this.request(`/api/studies/${id}`)
  }

  async createStudy(data: any) {
    return this.request("/api/studies/", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async updateStudy(id: string, data: any) {
    return this.request(`/api/studies/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async getReferenceTrials(params?: any) {
    const queryString = params ? `?${new URLSearchParams(params).toString()}` : ""
    return this.request(`/api/trials/reference${queryString}`)
  }

  // Commercial endpoints
  async runRevenueSimulation(data: any) {
    return this.request("/api/commercial/simulate", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getMarketData(indication: string) {
    return this.request(`/api/commercial/market/${indication}`)
  }

  // Chat endpoints
  async sendChatMessage(message: string, personaId: string, sessionId?: string) {
    return this.request("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ message, personaId, sessionId }),
    })
  }

  async getChatHistory(sessionId: string) {
    return this.request(`/api/chat/history/${sessionId}`)
  }
}

export const apiClient = new APIClient()
