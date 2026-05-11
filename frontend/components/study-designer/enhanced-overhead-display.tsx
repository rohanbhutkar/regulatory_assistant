'use client'

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Building2, Users, Briefcase, Shield, TrendingUp, Info } from 'lucide-react'

interface OverheadBreakdown {
  category: string
  amount: number
  percentage: number
  subcategories?: { name: string; amount: number }[]
}

interface EnhancedOverheadDisplayProps {
  overheadData: {
    total: number
    percentage: number
    breakdown?: any
    enhanced_overhead?: {
      by_type: {
        direct_overhead: number
        indirect_overhead: number
      }
      by_category: {
        facility_costs: number
        administrative_labor: number
        it_infrastructure: number
        quality_assurance: number
        regulatory_compliance: number
        training_development: number
        insurance_legal: number
        general_admin: number
      }
      details: any
    }
  }
  totalBudget: number
}

export function EnhancedOverheadDisplay({ overheadData, totalBudget }: EnhancedOverheadDisplayProps) {
  const enhanced = overheadData.enhanced_overhead

  const typeBreakdowns: OverheadBreakdown[] = enhanced ? [
    {
      category: 'Direct Overhead',
      amount: enhanced.by_type.direct_overhead,
      percentage: (enhanced.by_type.direct_overhead / overheadData.total) * 100,
      subcategories: [
        { name: 'Project-specific costs', amount: enhanced.by_type.direct_overhead * 0.7 },
        { name: 'Allocated resources', amount: enhanced.by_type.direct_overhead * 0.3 }
      ]
    },
    {
      category: 'Indirect Overhead',
      amount: enhanced.by_type.indirect_overhead,
      percentage: (enhanced.by_type.indirect_overhead / overheadData.total) * 100,
      subcategories: [
        { name: 'Shared services', amount: enhanced.by_type.indirect_overhead * 0.5 },
        { name: 'Corporate allocation', amount: enhanced.by_type.indirect_overhead * 0.5 }
      ]
    }
  ] : []

  const categoryBreakdowns: OverheadBreakdown[] = enhanced ? [
    {
      category: 'Facility Costs',
      amount: enhanced.by_category.facility_costs,
      percentage: (enhanced.by_category.facility_costs / overheadData.total) * 100
    },
    {
      category: 'Administrative Labor',
      amount: enhanced.by_category.administrative_labor,
      percentage: (enhanced.by_category.administrative_labor / overheadData.total) * 100
    },
    {
      category: 'IT Infrastructure',
      amount: enhanced.by_category.it_infrastructure,
      percentage: (enhanced.by_category.it_infrastructure / overheadData.total) * 100
    },
    {
      category: 'Quality Assurance',
      amount: enhanced.by_category.quality_assurance,
      percentage: (enhanced.by_category.quality_assurance / overheadData.total) * 100
    },
    {
      category: 'Regulatory Compliance',
      amount: enhanced.by_category.regulatory_compliance,
      percentage: (enhanced.by_category.regulatory_compliance / overheadData.total) * 100
    },
    {
      category: 'Training & Development',
      amount: enhanced.by_category.training_development,
      percentage: (enhanced.by_category.training_development / overheadData.total) * 100
    },
    {
      category: 'Insurance & Legal',
      amount: enhanced.by_category.insurance_legal,
      percentage: (enhanced.by_category.insurance_legal / overheadData.total) * 100
    },
    {
      category: 'General Admin',
      amount: enhanced.by_category.general_admin,
      percentage: (enhanced.by_category.general_admin / overheadData.total) * 100
    }
  ].sort((a, b) => b.amount - a.amount) : []

  const getCategoryIcon = (category: string) => {
    if (category.includes('Facility')) return <Building2 className="h-5 w-5" />
    if (category.includes('Labor') || category.includes('Admin')) return <Users className="h-5 w-5" />
    if (category.includes('IT')) return <Briefcase className="h-5 w-5" />
    if (category.includes('Quality') || category.includes('Regulatory') || category.includes('Insurance')) 
      return <Shield className="h-5 w-5" />
    return <TrendingUp className="h-5 w-5" />
  }

  const getColorForPercentage = (pct: number) => {
    if (pct > 20) return 'text-red-600 bg-red-50'
    if (pct > 10) return 'text-amber-600 bg-amber-50'
    return 'text-green-600 bg-green-50'
  }

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Total Overhead Costs</span>
            <Badge className="text-lg px-4 py-2">
              {overheadData.percentage.toFixed(1)}% Rate
            </Badge>
          </CardTitle>
          <CardDescription>
            Applied to base costs to cover indirect and support costs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-4xl font-bold text-blue-900">
            ${(overheadData.total / 1_000_000).toFixed(2)}M
          </div>
          <Progress 
            value={(overheadData.total / totalBudget) * 100} 
            className="mt-4"
          />
          <div className="text-sm text-blue-700 mt-2">
            {((overheadData.total / totalBudget) * 100).toFixed(1)}% of total budget
          </div>
        </CardContent>
      </Card>

      {/* Type Breakdown */}
      {enhanced && (
        <Card>
          <CardHeader>
            <CardTitle>Overhead by Type</CardTitle>
            <CardDescription>Direct vs Indirect overhead allocation</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {typeBreakdowns.map((item, idx) => (
              <div key={idx} className="space-y-2">
                <div className="flex justify-between items-center">
                  <div className="font-medium">{item.category}</div>
                  <div className="text-right">
                    <div className="font-bold">${(item.amount / 1_000_000).toFixed(2)}M</div>
                    <div className="text-sm text-slate-600">{item.percentage.toFixed(1)}%</div>
                  </div>
                </div>
                <Progress value={item.percentage} className="h-2" />
                
                {item.subcategories && (
                  <div className="ml-4 space-y-1 text-sm text-slate-600">
                    {item.subcategories.map((sub, subIdx) => (
                      <div key={subIdx} className="flex justify-between">
                        <span>• {sub.name}</span>
                        <span>${(sub.amount / 1_000_000).toFixed(2)}M</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Category Breakdown */}
      {enhanced && (
        <Card>
          <CardHeader>
            <CardTitle>Overhead by Category</CardTitle>
            <CardDescription>Detailed breakdown of overhead components</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {categoryBreakdowns.map((item, idx) => (
                <div 
                  key={idx}
                  className={`flex items-center justify-between p-3 rounded-lg border ${getColorForPercentage(item.percentage)}`}
                >
                  <div className="flex items-center gap-3">
                    {getCategoryIcon(item.category)}
                    <div>
                      <div className="font-medium">{item.category}</div>
                      <div className="text-sm opacity-80">{item.percentage.toFixed(1)}% of overhead</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg">
                      ${(item.amount / 1_000_000).toFixed(2)}M
                    </div>
                    <div className="text-sm opacity-80">
                      {((item.amount / totalBudget) * 100).toFixed(2)}% of total
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Legacy Breakdown (fallback) */}
      {!enhanced && overheadData.breakdown && (
        <Card>
          <CardHeader>
            <CardTitle>Overhead Breakdown</CardTitle>
            <CardDescription>Standard overhead allocation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(overheadData.breakdown).map(([key, value], idx) => {
                const amount = value as number
                const percentage = (amount / overheadData.total) * 100
                return (
                  <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                    <div className="font-medium capitalize">
                      {key.replace(/_/g, ' ')}
                    </div>
                    <div className="text-right">
                      <div className="font-bold">${(amount / 1_000_000).toFixed(2)}M</div>
                      <div className="text-sm text-slate-600">{percentage.toFixed(1)}%</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Card */}
      <Card className="border-slate-200 bg-slate-50">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Info className="h-5 w-5 text-slate-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-slate-700 space-y-2">
              <p>
                <strong>Overhead Rate:</strong> Applied as a percentage to direct costs to account for 
                organizational expenses not directly attributable to the study.
              </p>
              <p>
                <strong>Direct Overhead:</strong> Costs that can be specifically linked to supporting 
                this study (e.g., dedicated staff, equipment).
              </p>
              <p>
                <strong>Indirect Overhead:</strong> Shared organizational costs allocated proportionally 
                (e.g., facilities, corporate functions).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}







