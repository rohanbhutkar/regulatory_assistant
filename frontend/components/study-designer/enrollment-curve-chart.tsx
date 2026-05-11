"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { SimulationResult } from "@/lib/types/study-types"
import { TrendingUp, TrendingDown } from "lucide-react"

interface EnrollmentCurveChartProps {
  simulation: SimulationResult
}

export function EnrollmentCurveChart({ simulation }: EnrollmentCurveChartProps) {
  // Check if enrollmentCurve exists and has data
  if (!simulation.enrollmentCurve || simulation.enrollmentCurve.length === 0) {
    return (
      <Card className="p-6 bg-card">
        <h3 className="text-lg font-semibold text-foreground mb-2">Enrollment Projection</h3>
        <p className="text-sm text-muted-foreground text-center py-8">No enrollment data available</p>
      </Card>
    )
  }

  const maxEnrolled = Math.max(...simulation.enrollmentCurve.map((d) => Math.max(d.enrolled, d.projected)))
  const chartHeight = 300
  const chartWidth = 800
  const padding = { top: 20, right: 40, bottom: 40, left: 60 }

  // Calculate chart dimensions
  const innerWidth = chartWidth - padding.left - padding.right
  const innerHeight = chartHeight - padding.top - padding.bottom

  // Scale functions
  const xScale = (month: number) => padding.left + (month / simulation.enrollmentCurve.length) * innerWidth
  const yScale = (value: number) => padding.top + innerHeight - (value / maxEnrolled) * innerHeight

  // Generate path for projected line
  const projectedPath = simulation.enrollmentCurve
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.month)} ${yScale(d.projected)}`)
    .join(" ")

  // Generate path for actual enrollment line
  const enrolledPath = simulation.enrollmentCurve
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.month)} ${yScale(d.enrolled)}`)
    .join(" ")

  // Calculate variance
  const lastPoint = simulation.enrollmentCurve[simulation.enrollmentCurve.length - 1]
  const variance = lastPoint.enrolled - lastPoint.projected
  const variancePercent = ((variance / lastPoint.projected) * 100).toFixed(1)

  return (
    <Card className="p-6 bg-card">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Enrollment Projection</h3>
          <p className="text-sm text-muted-foreground">Projected vs. actual patient enrollment over time</p>
        </div>
        <div className="flex items-center gap-2">
          {variance >= 0 ? (
            <Badge variant="default" className="gap-1">
              <TrendingUp className="h-3 w-3" />
              {variancePercent}% ahead
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1">
              <TrendingDown className="h-3 w-3" />
              {Math.abs(Number(variancePercent))}% behind
            </Badge>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-border bg-muted/20 p-4">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-auto">
          {/* Grid lines */}
          <g stroke="hsl(var(--border))" strokeWidth="1" opacity="0.3">
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const y = padding.top + innerHeight * (1 - ratio)
              return <line key={ratio} x1={padding.left} y1={y} x2={chartWidth - padding.right} y2={y} />
            })}
          </g>

          {/* Y-axis labels */}
          <g fill="hsl(var(--muted-foreground))" fontSize="12">
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const y = padding.top + innerHeight * (1 - ratio)
              const value = Math.round(maxEnrolled * ratio)
              return (
                <text key={ratio} x={padding.left - 10} y={y + 4} textAnchor="end">
                  {value}
                </text>
              )
            })}
          </g>

          {/* X-axis labels */}
          <g fill="hsl(var(--muted-foreground))" fontSize="12">
            {simulation.enrollmentCurve
              .filter((_, i) => i % 4 === 0)
              .map((d) => (
                <text key={d.month} x={xScale(d.month)} y={chartHeight - padding.bottom + 20} textAnchor="middle">
                  Month {d.month}
                </text>
              ))}
          </g>

          {/* Area under projected curve */}
          <path
            d={`${projectedPath} L ${xScale(lastPoint.month)} ${chartHeight - padding.bottom} L ${padding.left} ${chartHeight - padding.bottom} Z`}
            fill="hsl(var(--primary))"
            opacity="0.1"
          />

          {/* Projected line */}
          <path d={projectedPath} stroke="hsl(var(--primary))" strokeWidth="2" fill="none" strokeDasharray="5,5" />

          {/* Actual enrollment line */}
          <path d={enrolledPath} stroke="hsl(var(--accent))" strokeWidth="3" fill="none" />

          {/* Data points */}
          {simulation.enrollmentCurve.map((d) => (
            <g key={d.month}>
              <circle cx={xScale(d.month)} cy={yScale(d.projected)} r="3" fill="hsl(var(--primary))" opacity="0.6" />
              <circle cx={xScale(d.month)} cy={yScale(d.enrolled)} r="4" fill="hsl(var(--accent))" />
            </g>
          ))}

          {/* Axis labels */}
          <text
            x={padding.left - 45}
            y={chartHeight / 2}
            fill="hsl(var(--muted-foreground))"
            fontSize="12"
            textAnchor="middle"
            transform={`rotate(-90, ${padding.left - 45}, ${chartHeight / 2})`}
          >
            Patients Enrolled
          </text>
          <text
            x={chartWidth / 2}
            y={chartHeight - 5}
            fill="hsl(var(--muted-foreground))"
            fontSize="12"
            textAnchor="middle"
          >
            Study Timeline (Months)
          </text>
        </svg>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="h-0.5 w-8 bg-primary" style={{ borderTop: "2px dashed hsl(var(--primary))" }} />
          <span className="text-muted-foreground">Projected Enrollment</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1 w-8 bg-accent rounded" />
          <span className="text-muted-foreground">Actual Enrollment</span>
        </div>
      </div>
    </Card>
  )
}
