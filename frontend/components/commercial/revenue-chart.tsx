"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { RevenueDataPoint } from "@/lib/types/commercial-types"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { TrendingUp } from "lucide-react"

interface RevenueChartProps {
  data: RevenueDataPoint[]
}

export function RevenueChart({ data }: RevenueChartProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)
  }

  const totalRevenue = data.reduce((sum, point) => sum + point.revenue, 0)
  const peakRevenue = Math.max(...data.map((point) => point.revenue))

  return (
    <Card className="border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Quarterly Revenue Projection</CardTitle>
          <div className="flex items-center gap-2 text-success">
            <TrendingUp className="h-4 w-4" />
            <span className="text-sm font-semibold">Peak: {formatCurrency(peakRevenue)}</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Revenue Line Chart */}
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="quarter" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" tickFormatter={(value) => formatCurrency(value)} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px" }}
              formatter={(value: number) => formatCurrency(value)}
            />
            <Legend />
            <Line type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={3} name="Revenue" dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>

        {/* Patient Volume Bar Chart */}
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="quarter" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px" }} />
            <Legend />
            <Bar dataKey="patients" fill="#3b82f6" name="Patients" />
            <Bar dataKey="marketShare" fill="#8b5cf6" name="Market Share (%)" />
          </BarChart>
        </ResponsiveContainer>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Total Revenue</p>
            <p className="text-2xl font-bold text-foreground">{formatCurrency(totalRevenue)}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Peak Patients</p>
            <p className="text-2xl font-bold text-foreground">
              {Math.max(...data.map((p) => p.patients)).toLocaleString()}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Peak Market Share</p>
            <p className="text-2xl font-bold text-foreground">{Math.max(...data.map((p) => p.marketShare))}%</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
