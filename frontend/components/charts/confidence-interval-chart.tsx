"use client"

import { LineChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

interface ConfidenceIntervalChartProps {
  data: Array<{
    month: number
    mean: number
    p10: number
    p50: number
    p90: number
  }>
  title: string
  description?: string
  yAxisLabel?: string
  showCumulative?: boolean
}

export function ConfidenceIntervalChart({
  data,
  title,
  description,
  yAxisLabel = "Patients",
  showCumulative = false
}: ConfidenceIntervalChartProps) {
  // Helper function to safely round numbers (handles NaN)
  const safeRound = (value: number): number => {
    if (value === null || value === undefined || isNaN(value)) {
      return 0
    }
    return Math.round(value)
  }

  // Transform data for visualization
  const chartData = data.map(point => ({
    month: point.month,
    mean: safeRound(point.mean),
    p50: safeRound(point.p50),
    range: [safeRound(point.p10), safeRound(point.p90)],
    p10: safeRound(point.p10),
    p90: safeRound(point.p90),
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="month" 
                label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
                className="text-xs"
              />
              <YAxis 
                label={{ value: yAxisLabel, angle: -90, position: 'insideLeft' }}
                className="text-xs"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: any) => safeRound(value)}
              />
              <Legend />
              
              {/* Confidence band (P10-P90) */}
              <Area
                type="monotone"
                dataKey="p90"
                fill="hsl(var(--primary))"
                fillOpacity={0.1}
                stroke="none"
                name="90th Percentile"
              />
              <Area
                type="monotone"
                dataKey="p10"
                fill="hsl(var(--background))"
                fillOpacity={1}
                stroke="none"
                name="10th Percentile"
              />
              
              {/* Median line (P50) */}
              <Line
                type="monotone"
                dataKey="p50"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))', r: 3 }}
                name="Median (P50)"
              />
              
              {/* Mean line */}
              <Line
                type="monotone"
                dataKey="mean"
                stroke="hsl(var(--chart-2))"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name="Mean"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted/50">
            <span className="text-muted-foreground">10th Percentile</span>
            <span className="text-lg font-semibold mt-1">
              {safeRound(chartData[chartData.length - 1]?.p10 || 0)}
            </span>
            <span className="text-xs text-muted-foreground">Pessimistic</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-primary/10">
            <span className="text-muted-foreground">50th Percentile</span>
            <span className="text-lg font-semibold mt-1">
              {safeRound(chartData[chartData.length - 1]?.p50 || 0)}
            </span>
            <span className="text-xs text-muted-foreground">Most Likely</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted/50">
            <span className="text-muted-foreground">90th Percentile</span>
            <span className="text-lg font-semibold mt-1">
              {safeRound(chartData[chartData.length - 1]?.p90 || 0)}
            </span>
            <span className="text-xs text-muted-foreground">Optimistic</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

