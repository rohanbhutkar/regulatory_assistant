"use client"

import { PersonaCard } from "./persona-card"
import type { Persona } from "@/lib/types/persona-types"

interface PersonaGridProps {
  personas: Persona[]
}

export function PersonaGrid({ personas }: PersonaGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-4 sm:gap-6 max-w-5xl">
      {personas.map((persona, index) => (
        <PersonaCard key={persona.id} persona={persona} index={index} />
      ))}
    </div>
  )
}
