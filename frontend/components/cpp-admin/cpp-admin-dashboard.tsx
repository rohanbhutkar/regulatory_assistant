/**
 * CPP Admin Dashboard
 * Main administration dashboard for CPP system management
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Settings, 
  DollarSign, 
  FileText, 
  Calculator, 
  TrendingUp, 
  Users,
  Database,
  CheckCircle,
  AlertTriangle,
  Activity,
  BarChart3
} from 'lucide-react'
import { RulesManager } from './rules-manager'
import { SPUPricingManager } from './spu-pricing-manager'
import { OPALConfigManager } from './opal-config-manager'
import { ProcedureOntologyManager } from './procedure-ontology-manager'

interface SystemMetrics {
  total_procedures: number
  total_rules: number
  total_countries: number
  total_mappings: number
  data_quality_score: number
  last_update: string
}

export function CPPAdminDashboard() {
  const [metrics] = useState<SystemMetrics>({
    total_procedures: 13556,
    total_rules: 47,
    total_countries: 15,
    total_mappings: 8234,
    data_quality_score: 94.5,
    last_update: '2025-10-27'
  })

  const quickActions = [
    {
      title: 'Add New Procedure',
      description: 'Create a new procedure code',
      icon: FileText,
      action: () => console.log('Add procedure'),
      color: 'bg-blue-500'
    },
    {
      title: 'Create Rule',
      description: 'Add a new budget rule',
      icon: Settings,
      action: () => console.log('Create rule'),
      color: 'bg-green-500'
    },
    {
      title: 'Update Pricing',
      description: 'Bulk import SPU pricing',
      icon: DollarSign,
      action: () => console.log('Update pricing'),
      color: 'bg-purple-500'
    },
    {
      title: 'Configure OPAL',
      description: 'Adjust overhead hours',
      icon: Calculator,
      action: () => console.log('Configure OPAL'),
      color: 'bg-orange-500'
    }
  ]

  const recentActivity = [
    {
      action: 'SPU Pricing Updated',
      details: 'USA pricing refreshed for Q2 2025',
      time: '2 hours ago',
      type: 'update'
    },
    {
      action: 'New Rule Created',
      details: 'Country rule for Japan added',
      time: '5 hours ago',
      type: 'create'
    },
    {
      action: 'Procedure Mapped',
      details: '23 new procedures mapped with high confidence',
      time: '1 day ago',
      type: 'mapping'
    },
    {
      action: 'OPAL Hours Adjusted',
      details: 'Treatment visit hours updated',
      time: '2 days ago',
      type: 'config'
    }
  ]

  const dataQualityMetrics = [
    {
      label: 'Procedures with Pricing',
      value: 98.5,
      total: 13556,
      complete: 13348,
      status: 'excellent'
    },
    {
      label: 'High Confidence Mappings',
      value: 89.2,
      total: 8234,
      complete: 7346,
      status: 'good'
    },
    {
      label: 'Active Rules',
      value: 100,
      total: 47,
      complete: 47,
      status: 'excellent'
    },
    {
      label: 'Countries Covered',
      value: 93.8,
      total: 16,
      complete: 15,
      status: 'good'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Database className="h-8 w-8" />
            CPP Administration
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage Clinical Per-Patient costing system configuration
          </p>
        </div>
        <Badge className="bg-green-500 text-lg px-4 py-2">
          <Activity className="mr-2 h-4 w-4" />
          System Healthy
        </Badge>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="rules">Rules Engine</TabsTrigger>
          <TabsTrigger value="pricing">SPU Pricing</TabsTrigger>
          <TabsTrigger value="opal">OPAL Config</TabsTrigger>
          <TabsTrigger value="procedures">Procedures</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-5 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">
                      {metrics.total_procedures.toLocaleString()}
                    </div>
                    <p className="text-sm text-muted-foreground">Procedures</p>
                  </div>
                  <FileText className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-green-600">
                      {metrics.total_rules}
                    </div>
                    <p className="text-sm text-muted-foreground">Rules</p>
                  </div>
                  <Settings className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-purple-600">
                      {metrics.total_countries}
                    </div>
                    <p className="text-sm text-muted-foreground">Countries</p>
                  </div>
                  <DollarSign className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-orange-600">
                      {metrics.total_mappings.toLocaleString()}
                    </div>
                    <p className="text-sm text-muted-foreground">Mappings</p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-orange-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-indigo-600">
                      {metrics.data_quality_score}%
                    </div>
                    <p className="text-sm text-muted-foreground">Quality Score</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-indigo-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Common administrative tasks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={action.action}
                    className="p-4 border rounded-lg hover:bg-gray-50 transition-all hover:shadow-md text-left"
                  >
                    <div className={`w-12 h-12 rounded-lg ${action.color} flex items-center justify-center mb-3`}>
                      <action.icon className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="font-semibold mb-1">{action.title}</h3>
                    <p className="text-sm text-muted-foreground">{action.description}</p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Data Quality Dashboard */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                Data Quality Metrics
              </CardTitle>
              <CardDescription>System data completeness and quality</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {dataQualityMetrics.map((metric, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{metric.label}</span>
                      <span className="text-sm text-muted-foreground">
                        {metric.complete.toLocaleString()} / {metric.total.toLocaleString()}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          metric.status === 'excellent' ? 'bg-green-500' :
                          metric.status === 'good' ? 'bg-blue-500' :
                          'bg-yellow-500'
                        }`}
                        style={{ width: `${metric.value}%` }}
                      />
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <Badge variant="outline" className={
                        metric.status === 'excellent' ? 'border-green-500 text-green-700' :
                        metric.status === 'good' ? 'border-blue-500 text-blue-700' :
                        'border-yellow-500 text-yellow-700'
                      }>
                        {metric.value}%
                      </Badge>
                      <span className="text-muted-foreground capitalize">{metric.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Recent Activity
              </CardTitle>
              <CardDescription>Latest system changes and updates</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentActivity.map((activity, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50">
                    <div className={`w-2 h-2 rounded-full mt-2 ${
                      activity.type === 'update' ? 'bg-blue-500' :
                      activity.type === 'create' ? 'bg-green-500' :
                      activity.type === 'mapping' ? 'bg-purple-500' :
                      'bg-orange-500'
                    }`} />
                    <div className="flex-1">
                      <div className="font-medium">{activity.action}</div>
                      <div className="text-sm text-muted-foreground">{activity.details}</div>
                    </div>
                    <div className="text-sm text-muted-foreground">{activity.time}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* System Info */}
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-6 w-6 text-blue-600" />
                <div className="flex-1">
                  <h3 className="font-semibold text-blue-900 mb-1">System Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm text-blue-800">
                    <div>
                      <strong>Last Data Update:</strong> {metrics.last_update}
                    </div>
                    <div>
                      <strong>System Version:</strong> CPP v2.0
                    </div>
                    <div>
                      <strong>Database Status:</strong> Healthy
                    </div>
                    <div>
                      <strong>API Status:</strong> Operational
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rules Tab */}
        <TabsContent value="rules">
          <RulesManager />
        </TabsContent>

        {/* Pricing Tab */}
        <TabsContent value="pricing">
          <SPUPricingManager />
        </TabsContent>

        {/* OPAL Tab */}
        <TabsContent value="opal">
          <OPALConfigManager />
        </TabsContent>

        {/* Procedures Tab */}
        <TabsContent value="procedures">
          <ProcedureOntologyManager />
        </TabsContent>
      </Tabs>
    </div>
  )
}







