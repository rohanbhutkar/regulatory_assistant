"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { SelectedSite } from "@/lib/types/study-types"
import { MapPin, Users } from "lucide-react"
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ZAxis } from "recharts"

interface InteractiveSiteMapProps {
  sites: SelectedSite[]
  onSiteClick?: (site: SelectedSite) => void
  showPopulationOverlay?: boolean
}

export function InteractiveSiteMap({ sites, onSiteClick, showPopulationOverlay = true }: InteractiveSiteMapProps) {
  const [hoveredSite, setHoveredSite] = useState<string | null>(null)

  const scatterData = sites
    .filter((site) => site.coordinates?.lng != null && site.coordinates?.lat != null)
    .map((site) => ({
      x: site.coordinates.lng, // Longitude as X
      y: site.coordinates.lat, // Latitude as Y
      z: site.estimatedEnrollment || 0, // Size based on enrollment
      score: site.score || 0,
      name: site.name || 'Unknown Site',
      location: site.location || 'Unknown Location',
      id: site.id,
    }))

  // Population density centers for overlay
  const populationCenters = showPopulationOverlay
    ? [
        { x: -74, y: 40.7, z: 8000, name: "Northeast" }, // NYC area
        { x: -118, y: 34, z: 7000, name: "West Coast" }, // LA area
        { x: -87.6, y: 41.8, z: 6000, name: "Midwest" }, // Chicago area
        { x: -95.3, y: 29.7, z: 5500, name: "South" }, // Houston area
        { x: -122.4, y: 37.7, z: 6500, name: "Bay Area" }, // SF area
      ]
    : []

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-popover border border-border rounded-lg p-3 shadow-lg">
          <div className="flex items-start gap-2 mb-2">
            <MapPin className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-semibold text-sm text-foreground">{data.name}</div>
              <div className="text-xs text-muted-foreground">{data.location}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
            <div>
              <div className="text-muted-foreground">Score</div>
              <div className="font-semibold text-foreground">{data.score}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Est. Enrollment</div>
              <div className="font-semibold text-foreground">{data.z}</div>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <Card className="p-6 bg-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-foreground">Site Distribution Map</h3>
          <Badge variant="secondary">{sites.length} Sites</Badge>
        </div>
      </div>

      <div className="relative rounded-lg border border-border overflow-hidden bg-gradient-to-br from-primary/5 via-accent/5 to-primary/5">
        <ResponsiveContainer width="100%" height={500}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              type="number"
              dataKey="x"
              name="Longitude"
              domain={[-125, -65]}
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: "hsl(var(--muted-foreground))" }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Latitude"
              domain={[25, 50]}
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: "hsl(var(--muted-foreground))" }}
            />
            <ZAxis type="number" dataKey="z" range={[100, 1000]} />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />

            {/* Population density overlay */}
            {showPopulationOverlay && (
              <Scatter name="Population Centers" data={populationCenters} fill="hsl(var(--primary))" fillOpacity={0.15}>
                {populationCenters.map((entry, index) => (
                  <Cell key={`cell-${index}`} />
                ))}
              </Scatter>
            )}

            {/* Site markers */}
            <Scatter
              name="Trial Sites"
              data={scatterData}
              fill="hsl(var(--primary))"
              onClick={(data: any) => {
                const site = sites.find((s) => s.id === data.id)
                if (site) onSiteClick?.(site)
              }}
            >
              {scatterData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.score >= 85 ? "hsl(var(--success))" : "hsl(var(--primary))"}
                  stroke="hsl(var(--background))"
                  strokeWidth={2}
                  style={{ cursor: "pointer" }}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>

        {/* Map overlay labels */}
        <div className="absolute top-4 right-4 bg-background/80 backdrop-blur-sm border border-border rounded-lg p-2 text-xs">
          <div className="font-semibold text-foreground mb-1">United States</div>
          <div className="text-muted-foreground">Geographic Distribution</div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap items-center gap-6 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-primary" />
          <span>Trial Site</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-success" />
          <span>High Performance (Score ≥85)</span>
        </div>
        {showPopulationOverlay && (
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-primary/20" />
            <span>Population Density</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Users className="h-3 w-3" />
          <span>Marker size = Est. Enrollment</span>
        </div>
      </div>
    </Card>
  )
}
