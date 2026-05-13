export interface Persona {
  id: string
  name: string
  description: string
  icon: string
  features: string[]
  permissions: string[]
  dashboardRoute: string
  color: string
}

export interface User {
  id: string
  name: string
  email: string
  roles: string[]
  currentPersona?: string
}

export interface PersonaStats {
  personaId: string
  activeUsers: number
  recentActivity: string
  keyMetrics: Record<string, number>
}
