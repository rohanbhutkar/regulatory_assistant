import React from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ComposedChart
} from 'recharts'
import { cn } from '@/lib/utils'

export interface ChartData {
  name: string
  value: number
  [key: string]: any
}

export interface ChartProps {
  data: ChartData[]
  type: 'line' | 'area' | 'bar' | 'pie' | 'scatter' | 'composed'
  title?: string
  subtitle?: string
  height?: number
  className?: string
  colors?: string[]
  showLegend?: boolean
  showTooltip?: boolean
  showGrid?: boolean
  xAxisKey?: string
  yAxisKey?: string
  dataKey?: string
  children?: React.ReactNode
}

const defaultColors = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
]

export function InteractiveChart({
  data,
  type,
  title,
  subtitle,
  height = 300,
  className,
  colors = defaultColors,
  showLegend = true,
  showTooltip = true,
  showGrid = true,
  xAxisKey = 'name',
  yAxisKey = 'value',
  dataKey = 'value',
  children
}: ChartProps) {
  const renderChart = (): React.ReactElement => {
    const commonProps = {
      data,
      margin: { top: 20, right: 30, left: 20, bottom: 5 }
    }

    switch (type) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}
            <XAxis dataKey={xAxisKey} stroke="#666" />
            <YAxis stroke="#666" />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={colors[0]}
              strokeWidth={2}
              dot={{ fill: colors[0], strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: colors[0], strokeWidth: 2 }}
            />
            {children}
          </LineChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}
            <XAxis dataKey={xAxisKey} stroke="#666" />
            <YAxis stroke="#666" />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={colors[0]}
              fill={colors[0]}
              fillOpacity={0.3}
              strokeWidth={2}
            />
            {children}
          </AreaChart>
        )

      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}
            <XAxis dataKey={xAxisKey} stroke="#666" />
            <YAxis stroke="#666" />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            <Bar dataKey={dataKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
            {children}
          </BarChart>
        )

      case 'pie':
        return (
          <PieChart {...commonProps}>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey={dataKey}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            {children}
          </PieChart>
        )

      case 'scatter':
        return (
          <ScatterChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}
            <XAxis dataKey={xAxisKey} stroke="#666" />
            <YAxis dataKey={yAxisKey} stroke="#666" />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            <Scatter dataKey={yAxisKey} fill={colors[0]} />
            {children}
          </ScatterChart>
        )

      case 'composed':
        return (
          <ComposedChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />}
            <XAxis dataKey={xAxisKey} stroke="#666" />
            <YAxis stroke="#666" />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            <Bar dataKey={dataKey} fill={colors[0]} />
            <Line type="monotone" dataKey={dataKey} stroke={colors[1]} strokeWidth={2} />
            {children}
          </ComposedChart>
        )

      default:
        return <div>Unsupported chart type</div>
    }
  }

  return (
    <div className={cn('bg-white rounded-lg border border-gray-200 p-6', className)}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
          {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  )
}

// Specialized chart components
export function RevenueChart({ data }: { data: ChartData[] }) {
  return (
    <InteractiveChart
      data={data}
      type="area"
      title="Revenue Trend"
      subtitle="Monthly revenue progression"
      colors={['#10B981', '#059669']}
    />
  )
}

export function PortfolioChart({ data }: { data: ChartData[] }) {
  return (
    <InteractiveChart
      data={data}
      type="pie"
      title="Portfolio Distribution"
      subtitle="Asset allocation by therapeutic area"
      height={400}
    />
  )
}

export function PerformanceChart({ data }: { data: ChartData[] }) {
  return (
    <InteractiveChart
      data={data}
      type="composed"
      title="Performance Metrics"
      subtitle="Combined view of key performance indicators"
      colors={['#3B82F6', '#10B981']}
    />
  )
}

export function TrialTimelineChart({ data }: { data: ChartData[] }) {
  return (
    <InteractiveChart
      data={data}
      type="line"
      title="Trial Timeline"
      subtitle="Progress tracking over time"
      colors={['#8B5CF6', '#A855F7']}
    />
  )
}
