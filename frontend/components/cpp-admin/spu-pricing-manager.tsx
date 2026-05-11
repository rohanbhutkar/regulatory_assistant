/**
 * SPU Pricing Management
 * View and manage Fair Market Value pricing for procedures
 */

"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Loader2, DollarSign, Search, Download, Upload, Filter } from 'lucide-react'
import { cppApi } from '@/lib/api/cpp-api'
import type { SPUPrice } from '@/lib/types/cpp'

interface PricingData {
  procedure_code: string
  description: string
  prices_by_country: Record<string, SPUPrice>
}

export function SPUPricingManager() {
  const [pricingData, setPricingData] = useState<PricingData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCountry, setSelectedCountry] = useState<string>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  const countries = [
    { code: 'USA', name: 'United States', currency: 'USD' },
    { code: 'GBR', name: 'United Kingdom', currency: 'GBP' },
    { code: 'DEU', name: 'Germany', currency: 'EUR' },
    { code: 'FRA', name: 'France', currency: 'EUR' },
    { code: 'JPN', name: 'Japan', currency: 'JPY' },
    { code: 'CHN', name: 'China', currency: 'CNY' },
    { code: 'IND', name: 'India', currency: 'INR' }
  ]

  useEffect(() => {
    loadPricingData()
  }, [])

  const loadPricingData = async () => {
    setIsLoading(true)
    try {
      // Mock data for now - in production, fetch from API
      const mockData: PricingData[] = [
        {
          procedure_code: '*INCO',
          description: 'Inconvenience Fee',
          prices_by_country: {
            'USA': { procedure_code: '*INCO', country_code: 'USA', local_price: 75.00, currency: 'USD', source: 'SPU 2025 Q2' },
            'GBR': { procedure_code: '*INCO', country_code: 'GBR', local_price: 60.00, currency: 'GBP', source: 'SPU 2025 Q2' },
            'DEU': { procedure_code: '*INCO', country_code: 'DEU', local_price: 65.00, currency: 'EUR', source: 'SPU 2025 Q2' }
          }
        },
        {
          procedure_code: '*RNDO',
          description: 'Randomization Fee',
          prices_by_country: {
            'USA': { procedure_code: '*RNDO', country_code: 'USA', local_price: 150.00, currency: 'USD', source: 'SPU 2025 Q2' },
            'GBR': { procedure_code: '*RNDO', country_code: 'GBR', local_price: 120.00, currency: 'GBP', source: 'SPU 2025 Q2' }
          }
        },
        {
          procedure_code: '80053',
          description: 'Comprehensive Metabolic Panel',
          prices_by_country: {
            'USA': { procedure_code: '80053', country_code: 'USA', local_price: 45.00, currency: 'USD', source: 'SPU 2025 Q2' },
            'GBR': { procedure_code: '80053', country_code: 'GBR', local_price: 38.00, currency: 'GBP', source: 'SPU 2025 Q2' }
          }
        },
        {
          procedure_code: '93000',
          description: 'Electrocardiogram (ECG)',
          prices_by_country: {
            'USA': { procedure_code: '93000', country_code: 'USA', local_price: 85.00, currency: 'USD', source: 'SPU 2025 Q2' },
            'DEU': { procedure_code: '93000', country_code: 'DEU', local_price: 70.00, currency: 'EUR', source: 'SPU 2025 Q2' }
          }
        }
      ]
      setPricingData(mockData)
    } catch (error) {
      console.error('Error loading pricing data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const filteredData = pricingData.filter(item => {
    const matchesSearch = searchTerm === '' || 
      item.procedure_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesCountry = selectedCountry === 'all' || 
      item.prices_by_country[selectedCountry] !== undefined
    
    return matchesSearch && matchesCountry
  })

  const formatPrice = (price: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  const getCountryName = (code: string) => {
    return countries.find(c => c.code === code)?.name || code
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <DollarSign className="h-8 w-8" />
            SPU Pricing Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Fair Market Value pricing for procedures across countries
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Import CSV
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{pricingData.length}</div>
            <p className="text-sm text-muted-foreground">Total Procedures</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{countries.length}</div>
            <p className="text-sm text-muted-foreground">Countries</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {pricingData.reduce((sum, p) => sum + Object.keys(p.prices_by_country).length, 0)}
            </div>
            <p className="text-sm text-muted-foreground">Total Prices</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">
              {(pricingData.reduce((sum, p) => sum + Object.keys(p.prices_by_country).length, 0) / pricingData.length).toFixed(1)}
            </div>
            <p className="text-sm text-muted-foreground">Avg Countries/Procedure</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
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
              <label className="text-sm font-medium">Country</label>
              <Select value={selectedCountry} onValueChange={setSelectedCountry}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Countries</SelectItem>
                  {countries.map(country => (
                    <SelectItem key={country.code} value={country.code}>
                      {country.name} ({country.currency})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="visits">Visits</SelectItem>
                  <SelectItem value="labs">Laboratory</SelectItem>
                  <SelectItem value="imaging">Imaging</SelectItem>
                  <SelectItem value="procedures">Procedures</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pricing Table */}
      <Card>
        <CardHeader>
          <CardTitle>Procedure Pricing</CardTitle>
          <CardDescription>
            Showing {filteredData.length} of {pricingData.length} procedures
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Description</TableHead>
                    {countries.map(country => (
                      <TableHead key={country.code} className="text-center">
                        {country.code}
                        <div className="text-xs text-muted-foreground">{country.currency}</div>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredData.map((item) => (
                    <TableRow key={item.procedure_code}>
                      <TableCell>
                        <code className="font-mono font-semibold text-blue-600">
                          {item.procedure_code}
                        </code>
                      </TableCell>
                      <TableCell className="max-w-md">{item.description}</TableCell>
                      {countries.map(country => {
                        const price = item.prices_by_country[country.code]
                        return (
                          <TableCell key={country.code} className="text-center">
                            {price ? (
                              <div>
                                <div className="font-semibold">
                                  {formatPrice(price.local_price, price.currency)}
                                </div>
                                <Badge variant="outline" className="text-xs mt-1">
                                  {price.source}
                                </Badge>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}







