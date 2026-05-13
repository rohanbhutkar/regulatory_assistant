"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, FileText, BarChart3, ClipboardCheck, ArrowRight, Scale } from "lucide-react"
import type { Persona } from "@/lib/types/persona-types"
import { useRouter } from "next/navigation"

interface PersonaCardProps {
  persona: Persona
  index: number
}

const iconMap = {
  TrendingUp: TrendingUp,
  FileText: FileText,
  BarChart3: BarChart3,
  ClipboardCheck: ClipboardCheck,
  Scale: Scale,
}

export function PersonaCard({ persona, index }: PersonaCardProps) {
  const router = useRouter()
  const IconComponent = iconMap[persona.icon as keyof typeof iconMap] || FileText

  const handleSelect = () => {
    router.push(persona.dashboardRoute)
  }

  return (
    <Card
      className="group relative overflow-hidden border-border/60 bg-card hover:border-primary/50 transition-all duration-300 cursor-pointer hover:shadow-lg"
      onClick={handleSelect}
    >
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between mb-4">
          <div className="p-3 rounded-xl bg-muted/80 group-hover:bg-primary/10 transition-colors duration-300">
            <IconComponent className="h-6 w-6 text-foreground group-hover:text-primary transition-colors duration-300" />
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-1 transition-all duration-300" />
        </div>

        <div className="space-y-2">
          <CardTitle className="text-xl font-bold text-foreground">{persona.name}</CardTitle>
          <CardDescription className="text-muted-foreground leading-relaxed text-sm">
            {persona.description}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {persona.features.slice(0, 3).map((feature) => (
            <Badge
              key={feature}
              variant="secondary"
              className="text-xs bg-muted/60 hover:bg-muted transition-colors border-0"
            >
              {feature}
            </Badge>
          ))}
          {persona.features.length > 3 && (
            <Badge variant="outline" className="text-xs text-muted-foreground">
              +{persona.features.length - 3}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
