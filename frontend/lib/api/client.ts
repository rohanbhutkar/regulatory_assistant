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

  // Chat persistence (cookie + credentials)
  private async requestWithCredentials<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseURL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`
    const response = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`)
    }
    return await response.json()
  }

  async chatBootstrap() {
    return this.requestWithCredentials("/api/chat/visitors/bootstrap", { method: "POST" })
  }

  async chatListSessions(variant?: string) {
    const q = variant ? `?variant=${encodeURIComponent(variant)}` : ""
    return this.requestWithCredentials(`/api/chat/sessions${q}`, { method: "GET" })
  }

  async chatCreateSession(body: { title?: string; variant?: string }) {
    return this.requestWithCredentials("/api/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: body.title ?? "New chat", variant: body.variant ?? "regulatory" }),
    })
  }

  async chatPatchSession(
    sessionId: string,
    body: { title?: string; starred?: boolean; titlePinned?: boolean },
  ) {
    const payload: Record<string, unknown> = {}
    if (body.title !== undefined) payload.title = body.title
    if (body.starred !== undefined) payload.starred = body.starred
    if (body.titlePinned !== undefined) payload.title_pinned = body.titlePinned
    return this.requestWithCredentials(`/api/chat/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    })
  }

  async chatDeleteSession(sessionId: string) {
    return this.requestWithCredentials(`/api/chat/sessions/${sessionId}`, { method: "DELETE" })
  }

  async chatListMessages(sessionId: string) {
    return this.requestWithCredentials(`/api/chat/sessions/${sessionId}/messages`, { method: "GET" })
  }

  async chatAppendMessage(
    sessionId: string,
    body: { content: string; metadata?: Record<string, unknown>; client_message_id?: string },
  ) {
    return this.requestWithCredentials(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(body),
    })
  }

  async chatCompleteTurn(
    sessionId: string,
    body: { content: string; metadata?: Record<string, unknown>; idempotency_key: string },
  ) {
    return this.requestWithCredentials(`/api/chat/sessions/${sessionId}/complete-turn`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": body.idempotency_key },
    })
  }
}

export const apiClient = new APIClient()
