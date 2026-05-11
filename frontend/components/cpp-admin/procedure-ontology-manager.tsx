/**
 * Procedure Ontology Manager
 * Manage procedure codes, descriptions, and ontology mappings
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Loader2, FileText, Search, Plus, Edit, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'

interface ProcedureOntology {
  code: string
  short_description: string
  long_description: string
  category: string
  base_price_usd: number
  mapping_count: number
  confidence_level: 'high' | 'medium' | 'low'
  active: boolean
}

export function ProcedureOntologyManager() {
  const [procedures, setProcedures] = useState<ProcedureOntology[]>([
    {
      code: '*INCO',
      short_description: 'Inconvenience Fee',
      long_description: 'Patient inconvenience fee for study participation',
      category: 'Administrative',
      base_price_usd: 75.00,
      mapping_count: 156,
      confidence_level: 'high',
      active: true
    },
    {
      code: '*RNDO',
      short_description: 'Randomization',
      long_description: 'Patient randomization procedure',
      category: 'Administrative',
      base_price_usd: 150.00,
      mapping_count: 89,
      confidence_level: 'high',
      active: true
    },
    {
      code: '80053',
      short_description: 'Comprehensive Metabolic Panel',
      long_description: 'Blood test measuring glucose, electrolytes, kidney function',
      category: 'Laboratory',
      base_price_usd: 45.00,
      mapping_count: 234,
      confidence_level: 'high',
      active: true
    },
    {
      code: '93000',
      short_description: 'ECG',
      long_description: 'Electrocardiogram, complete',
      category: 'Cardiovascular',
      base_price_usd: 85.00,
      mapping_count: 412,
      confidence_level: 'high',
      active: true
    },
    {
      code: '71020',
      short_description: 'Chest X-Ray',
      long_description: 'Radiologic examination, chest, 2 views',
      category: 'Imaging',
      base_price_usd: 120.00,
      mapping_count: 178,
      confidence_level: 'medium',
      active: true
    },
    {
      code: '85025',
      short_description: 'CBC with Differential',
      long_description: 'Complete blood count with automated differential',
      category: 'Laboratory',
      base_price_usd: 35.00,
      mapping_count: 567,
      confidence_level: 'high',
      active: true
    }
  ])

  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedConfidence, setSelectedConfidence] = useState('all')

  const categories = ['Administrative', 'Laboratory', 'Imaging', 'Cardiovascular', 'Procedures']

  const filteredProcedures = procedures.filter(proc => {
    const matchesSearch = searchTerm === '' ||
      proc.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      proc.short_description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      proc.long_description.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesCategory = selectedCategory === 'all' || proc.category === selectedCategory
    const matchesConfidence = selectedConfidence === 'all' || proc.confidence_level === selectedConfidence

    return matchesSearch && matchesCategory && matchesConfidence
  })

  const getConfidenceBadge = (level: string) => {
    switch (level) {
      case 'high':
        return <Badge className="bg-green-500"><CheckCircle className="mr-1 h-3 w-3" />High</Badge>
      case 'medium':
        return <Badge className="bg-yellow-500"><AlertTriangle className="mr-1 h-3 w-3" />Medium</Badge>
      case 'low':
        return <Badge className="bg-red-500"><XCircle className="mr-1 h-3 w-3" />Low</Badge>
      default:
        return <Badge variant="outline">{level}</Badge>
    }
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(price)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <FileText className="h-8 w-8" />
            Procedure Ontology Manager
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage standardized procedure codes and their mappings
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Procedure
        </Button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{procedures.length}</div>
            <p className="text-sm text-muted-foreground">Total Procedures</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {procedures.filter(p => p.confidence_level === 'high').length}
            </div>
            <p className="text-sm text-muted-foreground">High Confidence</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">
              {procedures.reduce((sum, p) => sum + p.mapping_count, 0).toLocaleString()}
            </div>
            <p className="text-sm text-muted-foreground">Total Mappings</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">
              {categories.length}
            </div>
            <p className="text-sm text-muted-foreground">Categories</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-orange-600">
              {procedures.filter(p => p.active).length}
            </div>
            <p className="text-sm text-muted-foreground">Active</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by code or description..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Confidence Level</label>
              <Select value={selectedConfidence} onValueChange={setSelectedConfidence}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Levels</SelectItem>
                  <SelectItem value="high">High Confidence</SelectItem>
                  <SelectItem value="medium">Medium Confidence</SelectItem>
                  <SelectItem value="low">Low Confidence</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Procedures Table */}
      <Card>
        <CardHeader>
          <CardTitle>Procedure Ontology</CardTitle>
          <CardDescription>
            Showing {filteredProcedures.length} of {procedures.length} procedures
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">Base Price</TableHead>
                <TableHead className="text-center">Mappings</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredProcedures.map((proc) => (
                <TableRow key={proc.code}>
                  <TableCell>
                    {proc.active ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-gray-400" />
                    )}
                  </TableCell>
                  <TableCell>
                    <code className="font-mono font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded">
                      {proc.code}
                    </code>
                  </TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium">{proc.short_description}</div>
                      <div className="text-sm text-muted-foreground truncate max-w-md">
                        {proc.long_description}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{proc.category}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-semibold">
                    {formatPrice(proc.base_price_usd)}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge className="bg-purple-500">
                      {proc.mapping_count.toLocaleString()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {getConfidenceBadge(proc.confidence_level)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        View
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Mapping Quality Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 text-blue-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-blue-900">About Confidence Levels</h3>
              <div className="space-y-2 mt-2 text-sm text-blue-800">
                <p><strong>High Confidence:</strong> Mappings consistently match with 90%+ accuracy. Used widely across studies.</p>
                <p><strong>Medium Confidence:</strong> Mappings match with 70-90% accuracy. May require review for specific contexts.</p>
                <p><strong>Low Confidence:</strong> Mappings match with &lt;70% accuracy. Requires manual review and validation.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}







