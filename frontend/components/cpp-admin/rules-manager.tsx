/**
 * Rules Engine Management
 * View, edit, and create Golden, Country, and Indication rules
 */

"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Loader2, Plus, Edit, Trash2, CheckCircle, XCircle, Settings } from 'lucide-react'
import { cppApi } from '@/lib/api/cpp-api'
import type { Rule, RuleType, RuleAction } from '@/lib/types/cpp'

interface RuleFormData {
  name: string
  rule_type: RuleType
  description: string
  conditions: {
    field: string
    operator: string
    value: string
  }[]
  action: RuleAction
  value: number
  priority: number
  active: boolean
}

export function RulesManager() {
  const [rules, setRules] = useState<Rule[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedRule, setSelectedRule] = useState<Rule | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState<RuleFormData>({
    name: '',
    rule_type: 'Golden' as RuleType,
    description: '',
    conditions: [{ field: '', operator: '', value: '' }],
    action: 'multiply' as RuleAction,
    value: 1.0,
    priority: 1,
    active: true
  })

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    setIsLoading(true)
    try {
      const response = await cppApi.previewRules()
      setRules(response.rules as any)
    } catch (error) {
      console.error('Error loading rules:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getRulesByType = (type: string) => {
    return rules.filter(r => r.rule_type === type)
  }

  const getRuleBadge = (rule: Rule) => {
    if (!rule.active) {
      return <Badge variant="outline" className="bg-gray-100">Inactive</Badge>
    }
    
    switch (rule.rule_type) {
      case 'Golden':
        return <Badge className="bg-yellow-500">Golden Rule</Badge>
      case 'Country':
        return <Badge className="bg-blue-500">Country Rule</Badge>
      case 'Indication':
        return <Badge className="bg-green-500">Indication Rule</Badge>
      default:
        return <Badge variant="outline">{rule.rule_type}</Badge>
    }
  }

  const getActionDescription = (action: string, value: number) => {
    switch (action) {
      case 'multiply':
        return `Multiply by ${value}x`
      case 'add_cost':
        return `Add $${value.toLocaleString()}`
      case 'add_percentage':
        return `Add ${value}%`
      case 'set_value':
        return `Set to $${value.toLocaleString()}`
      default:
        return `${action}: ${value}`
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Rules Engine Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure Golden Rules, Country Rules, and Indication Rules
          </p>
        </div>
        <Button onClick={() => setIsEditing(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Rule
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{rules.length}</div>
            <p className="text-sm text-muted-foreground">Total Rules</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">
              {getRulesByType('Golden').length}
            </div>
            <p className="text-sm text-muted-foreground">Golden Rules</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">
              {getRulesByType('Country').length}
            </div>
            <p className="text-sm text-muted-foreground">Country Rules</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {getRulesByType('Indication').length}
            </div>
            <p className="text-sm text-muted-foreground">Indication Rules</p>
          </CardContent>
        </Card>
      </div>

      {/* Rules by Type */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList>
          <TabsTrigger value="all">All Rules ({rules.length})</TabsTrigger>
          <TabsTrigger value="golden">Golden ({getRulesByType('Golden').length})</TabsTrigger>
          <TabsTrigger value="country">Country ({getRulesByType('Country').length})</TabsTrigger>
          <TabsTrigger value="indication">Indication ({getRulesByType('Indication').length})</TabsTrigger>
        </TabsList>

        {/* All Rules */}
        <TabsContent value="all">
          <Card>
            <CardHeader>
              <CardTitle>All Rules</CardTitle>
              <CardDescription>Complete list of all rules in the system</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : (
                <RulesTable 
                  rules={rules} 
                  onEdit={setSelectedRule}
                  getRuleBadge={getRuleBadge}
                  getActionDescription={getActionDescription}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Golden Rules */}
        <TabsContent value="golden">
          <Card>
            <CardHeader>
              <CardTitle>Golden Rules</CardTitle>
              <CardDescription>
                Universal rules that apply to all studies regardless of context
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RulesTable 
                rules={getRulesByType('Golden')} 
                onEdit={setSelectedRule}
                getRuleBadge={getRuleBadge}
                getActionDescription={getActionDescription}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Country Rules */}
        <TabsContent value="country">
          <Card>
            <CardHeader>
              <CardTitle>Country Rules</CardTitle>
              <CardDescription>
                Country-specific adjustments and multipliers
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RulesTable 
                rules={getRulesByType('Country')} 
                onEdit={setSelectedRule}
                getRuleBadge={getRuleBadge}
                getActionDescription={getActionDescription}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Indication Rules */}
        <TabsContent value="indication">
          <Card>
            <CardHeader>
              <CardTitle>Indication Rules</CardTitle>
              <CardDescription>
                Therapeutic area and indication-specific rules
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RulesTable 
                rules={getRulesByType('Indication')} 
                onEdit={setSelectedRule}
                getRuleBadge={getRuleBadge}
                getActionDescription={getActionDescription}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function RulesTable({ 
  rules, 
  onEdit, 
  getRuleBadge,
  getActionDescription 
}: { 
  rules: Rule[]
  onEdit: (rule: Rule) => void
  getRuleBadge: (rule: Rule) => JSX.Element
  getActionDescription: (action: string, value: number) => string
}) {
  if (rules.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No rules found
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Status</TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Priority</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rules.map((rule) => (
          <TableRow key={rule.id}>
            <TableCell>
              {rule.active ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
            </TableCell>
            <TableCell className="font-medium">{rule.name}</TableCell>
            <TableCell>{getRuleBadge(rule)}</TableCell>
            <TableCell>
              <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                {getActionDescription(rule.action, rule.value)}
              </code>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{rule.priority}</Badge>
            </TableCell>
            <TableCell className="max-w-md truncate">
              {rule.description}
            </TableCell>
            <TableCell>
              <div className="flex gap-2">
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => onEdit(rule)}
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm"
                  className="text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}







