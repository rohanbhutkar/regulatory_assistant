"use client"

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'

interface ComponentScores {
  historical_performance: number
  therapeutic_expertise: number
  enrollment_capacity: number
  site_quality: number
  geographic: number
  patient_population: number
}

interface SiteScoringChartProps {
  componentScores: ComponentScores
  totalScore: number
  siteName: string
}

export function SiteScoringChart({ componentScores, totalScore, siteName }: SiteScoringChartProps) {
  // Prepare data for radar chart
  const radarData = [
    { category: 'Historical Performance', value: componentScores.historical_performance, fullMark: 100 },
    { category: 'Therapeutic Expertise', value: componentScores.therapeutic_expertise, fullMark: 100 },
    { category: 'Enrollment Capacity', value: componentScores.enrollment_capacity, fullMark: 100 },
    { category: 'Site Quality', value: componentScores.site_quality, fullMark: 100 },
    { category: 'Geographic', value: componentScores.geographic, fullMark: 100 },
    { category: 'Patient Population', value: componentScores.patient_population, fullMark: 100 },
  ]

  // Prepare data for bar chart
  const barData = Object.entries(componentScores).map(([key, value]) => ({
    name: key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
    score: value,
  }))

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getScoreBadge = (score: number) => {
    if (score >= 90) return { label: 'Excellent', variant: 'default' as const }
    if (score >= 80) return { label: 'Very Good', variant: 'secondary' as const }
    if (score >= 70) return { label: 'Good', variant: 'secondary' as const }
    if (score >= 60) return { label: 'Fair', variant: 'outline' as const }
    return { label: 'Poor', variant: 'destructive' as const }
  }

  const scoreBadge = getScoreBadge(totalScore)

  return (
    <div className="space-y-6">
      {/* Overall Score Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{siteName}</CardTitle>
            <Badge variant={scoreBadge.variant}>{scoreBadge.label}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className={`text-5xl font-bold ${getScoreColor(totalScore)}`}>
              {totalScore.toFixed(1)}
            </div>
            <div className="flex-1">
              <Progress value={totalScore} className="h-3" />
              <p className="text-sm text-muted-foreground mt-2">
                Overall Site Score (out of 100)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Radar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Component Scores (Radar View)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="hsl(var(--border))" />
                <PolarAngleAxis 
                  dataKey="category" 
                  tick={{ fill: 'hsl(var(--foreground))', fontSize: 12 }}
                />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar
                  name="Score"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.6}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Component Scores (Bar View)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} layout="horizontal" margin={{ top: 5, right: 30, left: 120, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="name" className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Bar 
                  dataKey="score" 
                  fill="hsl(var(--primary))" 
                  radius={[0, 8, 8, 0]}
                  label={{ position: 'right', formatter: (value: number) => value.toFixed(1) }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Detailed Score Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.entries(componentScores).map(([key, value]) => {
            const name = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
            return (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{name}</span>
                  <span className={`text-sm font-semibold ${getScoreColor(value)}`}>
                    {value.toFixed(1)}
                  </span>
                </div>
                <Progress value={value} className="h-2" />
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}









