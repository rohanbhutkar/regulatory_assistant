'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Search, 
  AlertTriangle, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  DollarSign,
  FileText,
  BarChart3,
  Download
} from 'lucide-react'

interface FMVItem {
  procedure_name: string
  budgeted_amount: number
  benchmark_median: number | null
  benchmark_q1: number | null
  benchmark_q3: number | null
  difference_amount: number | null
  difference_percentage: number | null
  status: string
  risk_level: string | null
  category: string
  quantity: number
  total_budgeted: number
  total_benchmark: number | null
  total_difference: number | null
}

interface FMVAnalysisResult {
  summary: {
    total_procedures: number
    within_range: number
    above_range: number
    below_range: number
    no_benchmark: number
    total_budgeted: number
    total_benchmark: number
    total_variance: number
    within_range_pct: number
    above_range_pct: number
    below_range_pct: number
    no_benchmark_pct: number
    total_variance_pct: number
  }
  items: FMVItem[]
  tolerance: number
}

export default function FMVAnalysisPage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<FMVAnalysisResult | null>(null)
  const [recommendations, setRecommendations] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterCategory, setFilterCategory] = useState<string>('all')

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    try {
      // Mock budgeted costs for demo
      const mockBudgetedCosts = [
        { procedure_name: 'ECG', budgeted_amount: 120, quantity: 300 },
        { procedure_name: 'Echocardiogram', budgeted_amount: 950, quantity: 150 },
        { procedure_name: 'Complete Blood Count', budgeted_amount: 55, quantity: 600 },
        { procedure_name: 'HbA1c', budgeted_amount: 48, quantity: 450 },
        { procedure_name: 'Lipid Panel', budgeted_amount: 85, quantity: 300 },
        { procedure_name: 'MRI Brain', budgeted_amount: 2200, quantity: 50 },
        { procedure_name: 'CT Scan', budgeted_amount: 1350, quantity: 75 },
        { procedure_name: 'Bone Marrow Biopsy', budgeted_amount: 1500, quantity: 30 },
        { procedure_name: 'Screening Visit', budgeted_amount: 1600, quantity: 300 },
        { procedure_name: 'Follow-up Visit', budgeted_amount: 750, quantity: 900 },
      ]

      const response = await fetch('http://localhost:8001/fmv/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          budgeted_costs: mockBudgetedCosts,
          tolerance: 0.25
        })
      })

      if (!response.ok) {
        throw new Error('FMV analysis failed')
      }

      const data = await response.json()
      setAnalysisResult(data.analysis)
      setRecommendations(data.recommendations)
    } catch (error) {
      console.error('Error running FMV analysis:', error)
      alert('Failed to run FMV analysis')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const getStatusBadge = (status: string, risk_level: string | null) => {
    if (status === 'within_range') {
      return <Badge className="bg-green-100 text-green-800 border-green-200">✓ Within Range</Badge>
    } else if (status === 'above_range') {
      return <Badge className="bg-red-100 text-red-800 border-red-200">↑ Above Range</Badge>
    } else if (status === 'below_range') {
      return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">↓ Below Range</Badge>
    } else {
      return <Badge variant="outline">No Benchmark</Badge>
    }
  }

  const getRiskBadge = (risk_level: string | null) => {
    if (!risk_level) return null
    
    if (risk_level === 'high') {
      return <Badge className="bg-red-100 text-red-800 border-red-200">High Risk</Badge>
    } else if (risk_level === 'medium') {
      return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">Medium Risk</Badge>
    } else {
      return <Badge className="bg-green-100 text-green-800 border-green-200">Low Risk</Badge>
    }
  }

  const filteredItems = analysisResult?.items.filter(item => {
    const matchesSearch = item.procedure_name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus
    const matchesCategory = filterCategory === 'all' || item.category === filterCategory
    return matchesSearch && matchesStatus && matchesCategory
  }) || []

  const categories = Array.from(new Set(analysisResult?.items.map(item => item.category) || []))

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <BarChart3 className="h-8 w-8 text-blue-600" />
              Fair Market Value Analysis
            </h1>
            <p className="text-slate-600 mt-1">
              Compare budgeted costs against industry benchmarks
            </p>
          </div>
          <Button 
            onClick={runAnalysis} 
            disabled={isAnalyzing}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isAnalyzing ? 'Analyzing...' : 'Run FMV Analysis'}
          </Button>
        </div>

        {/* Summary Cards */}
        {analysisResult && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-green-200 bg-green-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-green-800">Within Range</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-900">
                  {analysisResult.summary.within_range}
                </div>
                <p className="text-xs text-green-700 mt-1">
                  {analysisResult.summary.within_range_pct.toFixed(1)}% of procedures
                </p>
              </CardContent>
            </Card>

            <Card className="border-red-200 bg-red-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-red-800">Above Range</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-900">
                  {analysisResult.summary.above_range}
                </div>
                <p className="text-xs text-red-700 mt-1">
                  {analysisResult.summary.above_range_pct.toFixed(1)}% of procedures
                </p>
              </CardContent>
            </Card>

            <Card className="border-yellow-200 bg-yellow-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-yellow-800">Below Range</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-900">
                  {analysisResult.summary.below_range}
                </div>
                <p className="text-xs text-yellow-700 mt-1">
                  {analysisResult.summary.below_range_pct.toFixed(1)}% of procedures
                </p>
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-slate-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-800">Total Variance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-slate-900">
                  {analysisResult.summary.total_variance >= 0 ? '+' : ''}
                  ${(analysisResult.summary.total_variance / 1000).toFixed(0)}K
                </div>
                <p className="text-xs text-slate-700 mt-1">
                  {analysisResult.summary.total_variance_pct.toFixed(1)}% vs benchmark
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <Card className="border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-blue-900">
                <FileText className="h-5 w-5" />
                Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {recommendations.map((rec, idx) => (
                <div key={idx} className="flex gap-2 text-sm text-blue-800">
                  <span>•</span>
                  <span>{rec}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Detailed Results */}
        {analysisResult && (
          <Card>
            <CardHeader>
              <CardTitle>Procedure Analysis</CardTitle>
              <CardDescription>
                Showing {filteredItems.length} of {analysisResult.items.length} procedures
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Filters */}
              <div className="flex flex-wrap gap-4 mb-6">
                <div className="flex-1 min-w-[200px]">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      placeholder="Search procedures..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="border rounded-md px-3 py-2 text-sm"
                >
                  <option value="all">All Statuses</option>
                  <option value="within_range">Within Range</option>
                  <option value="above_range">Above Range</option>
                  <option value="below_range">Below Range</option>
                  <option value="no_benchmark">No Benchmark</option>
                </select>
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="border rounded-md px-3 py-2 text-sm"
                >
                  <option value="all">All Categories</option>
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                <Button variant="outline" size="sm" className="gap-2">
                  <Download className="h-4 w-4" />
                  Export
                </Button>
              </div>

              {/* Results Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="text-left p-3 font-medium text-slate-700">Procedure</th>
                      <th className="text-left p-3 font-medium text-slate-700">Category</th>
                      <th className="text-right p-3 font-medium text-slate-700">Qty</th>
                      <th className="text-right p-3 font-medium text-slate-700">Budgeted</th>
                      <th className="text-right p-3 font-medium text-slate-700">Benchmark</th>
                      <th className="text-right p-3 font-medium text-slate-700">Variance</th>
                      <th className="text-center p-3 font-medium text-slate-700">Status</th>
                      <th className="text-center p-3 font-medium text-slate-700">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item, idx) => (
                      <tr key={idx} className="border-b hover:bg-slate-50">
                        <td className="p-3 font-medium">{item.procedure_name}</td>
                        <td className="p-3 text-slate-600">{item.category}</td>
                        <td className="p-3 text-right">{item.quantity}</td>
                        <td className="p-3 text-right font-medium">
                          ${item.budgeted_amount.toFixed(0)}
                        </td>
                        <td className="p-3 text-right text-slate-600">
                          {item.benchmark_median ? `$${item.benchmark_median.toFixed(0)}` : 'N/A'}
                        </td>
                        <td className={`p-3 text-right font-medium ${
                          item.difference_percentage && item.difference_percentage > 0 
                            ? 'text-red-600' 
                            : 'text-green-600'
                        }`}>
                          {item.difference_percentage !== null 
                            ? `${item.difference_percentage > 0 ? '+' : ''}${item.difference_percentage.toFixed(1)}%`
                            : 'N/A'
                          }
                        </td>
                        <td className="p-3 text-center">
                          {getStatusBadge(item.status, item.risk_level)}
                        </td>
                        <td className="p-3 text-center">
                          {getRiskBadge(item.risk_level)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!analysisResult && !isAnalyzing && (
          <Card className="border-dashed border-2">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <BarChart3 className="h-16 w-16 text-slate-300 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                No Analysis Run Yet
              </h3>
              <p className="text-slate-600 mb-6 max-w-md">
                Click "Run FMV Analysis" to compare your budgeted procedure costs against industry benchmarks
              </p>
              <Button onClick={runAnalysis} className="bg-blue-600 hover:bg-blue-700">
                Run FMV Analysis
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}







