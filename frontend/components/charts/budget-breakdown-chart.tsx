"use client"

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { DollarSign } from 'lucide-react'

interface BudgetBreakdown {
  patient_costs: number
  site_costs: number
  monitoring_costs: number
  overhead: number
}

interface BudgetBreakdownChartProps {
  breakdown: BudgetBreakdown
  totalCost: number
  costPerPatient: number
  monthlyBurnRate: number
}

const COLORS = {
  patient_costs: 'hsl(var(--chart-1))',
  site_costs: 'hsl(var(--chart-2))',
  monitoring_costs: 'hsl(var(--chart-3))',
  overhead: 'hsl(var(--chart-4))',
}

export function BudgetBreakdownChart({
  breakdown,
  totalCost,
  costPerPatient,
  monthlyBurnRate
}: BudgetBreakdownChartProps) {
  // Helper to safely get numeric value
  const safeValue = (value: number): number => {
    if (value === null || value === undefined || isNaN(value)) {
      return 0
    }
    return value
  }

  // Prepare data for pie chart
  const pieData = [
    { name: 'Patient Costs', value: safeValue(breakdown.patient_costs), color: COLORS.patient_costs },
    { name: 'Site Costs', value: safeValue(breakdown.site_costs), color: COLORS.site_costs },
    { name: 'Monitoring Costs', value: safeValue(breakdown.monitoring_costs), color: COLORS.monitoring_costs },
    { name: 'Overhead', value: safeValue(breakdown.overhead), color: COLORS.overhead },
  ]

  // Prepare data for bar chart
  const barData = Object.entries(breakdown).map(([key, value]) => {
    const safeCost = safeValue(value)
    const percentage = totalCost > 0 ? (safeCost / totalCost) * 100 : 0
    return {
      name: key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      value: safeCost,
      percentage: isNaN(percentage) ? '0.0' : percentage.toFixed(1)
    }
  })

  const formatCurrency = (value: number) => {
    if (value === null || value === undefined || isNaN(value)) {
      return '$0'
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(value)
  }

  const formatPercentage = (value: number) => {
    if (value === null || value === undefined || isNaN(value) || totalCost === 0) {
      return '0.0%'
    }
    const percentage = (value / totalCost) * 100
    if (isNaN(percentage)) {
      return '0.0%'
    }
    return `${percentage.toFixed(1)}%`
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Total Budget</span>
            </div>
            <div className="text-3xl font-bold text-primary">
              {formatCurrency(totalCost)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Cost Per Patient</span>
            </div>
            <div className="text-3xl font-bold">
              {formatCurrency(costPerPatient)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Monthly Burn Rate</span>
            </div>
            <div className="text-3xl font-bold text-orange-600">
              {formatCurrency(monthlyBurnRate)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Budget Distribution</CardTitle>
            <CardDescription>Percentage breakdown by category</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${formatPercentage(entry.value)}`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Cost Comparison</CardTitle>
            <CardDescription>Absolute cost by category</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis 
                    dataKey="name" 
                    angle={-45}
                    textAnchor="end"
                    height={100}
                    className="text-xs"
                  />
                  <YAxis 
                    tickFormatter={(value) => formatCurrency(value)}
                    className="text-xs"
                  />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="hsl(var(--primary))" 
                    radius={[8, 8, 0, 0]}
                    label={{ 
                      position: 'top', 
                      formatter: (value: number) => formatCurrency(value),
                      fontSize: 11
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Breakdown Table */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Cost Breakdown</CardTitle>
          <CardDescription>Item-by-item cost analysis</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {barData.map((item, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{item.name}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">{item.percentage}%</span>
                    <span className="text-sm font-semibold">{formatCurrency(item.value)}</span>
                  </div>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-border">
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold">Total Budget</span>
              <span className="text-xl font-bold text-primary">{formatCurrency(totalCost)}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

