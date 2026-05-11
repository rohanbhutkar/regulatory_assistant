'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Globe, Users, DollarSign, Plus, Trash2, AlertCircle, CheckCircle2 } from 'lucide-react'

interface CountryAllocation {
  country: string
  country_code: string
  patients: number
  sites: number
  percentage: number
  estimated_cost: number
  exchange_rate: number
  currency: string
}

interface CountryAllocationManagerProps {
  totalPatients: number
  totalBudget: number
  onAllocationChange?: (allocations: CountryAllocation[]) => void
}

export function CountryAllocationManager({
  totalPatients,
  totalBudget,
  onAllocationChange
}: CountryAllocationManagerProps) {
  const [allocations, setAllocations] = useState<CountryAllocation[]>([
    {
      country: 'United States',
      country_code: 'USA',
      patients: Math.round(totalPatients * 0.5),
      sites: 50,
      percentage: 50,
      estimated_cost: totalBudget * 0.6,
      exchange_rate: 1.0,
      currency: 'USD'
    },
    {
      country: 'United Kingdom',
      country_code: 'GBR',
      patients: Math.round(totalPatients * 0.2),
      sites: 20,
      percentage: 20,
      estimated_cost: totalBudget * 0.18,
      exchange_rate: 0.79,
      currency: 'GBP'
    },
    {
      country: 'Germany',
      country_code: 'DEU',
      patients: Math.round(totalPatients * 0.15),
      sites: 15,
      percentage: 15,
      estimated_cost: totalBudget * 0.12,
      exchange_rate: 0.92,
      currency: 'EUR'
    },
    {
      country: 'Canada',
      country_code: 'CAN',
      patients: Math.round(totalPatients * 0.15),
      sites: 15,
      percentage: 15,
      estimated_cost: totalBudget * 0.10,
      exchange_rate: 1.35,
      currency: 'CAD'
    }
  ])

  const [newCountry, setNewCountry] = useState('')
  const [newCountryCode, setNewCountryCode] = useState('')

  // Calculate totals
  const totalAllocatedPatients = allocations.reduce((sum, a) => sum + a.patients, 0)
  const totalAllocatedPercentage = allocations.reduce((sum, a) => sum + a.percentage, 0)
  const totalAllocatedCost = allocations.reduce((sum, a) => sum + a.estimated_cost, 0)

  const isValid = Math.abs(totalAllocatedPatients - totalPatients) < 1 && 
                  Math.abs(totalAllocatedPercentage - 100) < 0.1

  useEffect(() => {
    if (onAllocationChange) {
      onAllocationChange(allocations)
    }
  }, [allocations, onAllocationChange])

  const updateAllocation = (index: number, field: keyof CountryAllocation, value: any) => {
    const updated = [...allocations]
    updated[index] = { ...updated[index], [field]: value }

    // Recalculate dependent values
    if (field === 'percentage') {
      const pct = parseFloat(value) || 0
      updated[index].percentage = pct
      updated[index].patients = Math.round((pct / 100) * totalPatients)
      updated[index].estimated_cost = (pct / 100) * totalBudget
    } else if (field === 'patients') {
      const pts = parseInt(value) || 0
      updated[index].patients = pts
      updated[index].percentage = (pts / totalPatients) * 100
      updated[index].estimated_cost = (pts / totalPatients) * totalBudget
    }

    setAllocations(updated)
  }

  const addCountry = () => {
    if (!newCountry || !newCountryCode) return

    const remainingPatients = totalPatients - totalAllocatedPatients
    const remainingPercentage = 100 - totalAllocatedPercentage

    if (remainingPatients <= 0) {
      alert('All patients have been allocated')
      return
    }

    const newAllocation: CountryAllocation = {
      country: newCountry,
      country_code: newCountryCode,
      patients: Math.min(remainingPatients, Math.round(totalPatients * 0.1)),
      sites: 10,
      percentage: Math.min(remainingPercentage, 10),
      estimated_cost: Math.min(totalBudget - totalAllocatedCost, totalBudget * 0.1),
      exchange_rate: 1.0,
      currency: 'USD'
    }

    setAllocations([...allocations, newAllocation])
    setNewCountry('')
    setNewCountryCode('')
  }

  const removeCountry = (index: number) => {
    if (allocations.length <= 1) {
      alert('Must have at least one country')
      return
    }
    setAllocations(allocations.filter((_, i) => i !== index))
  }

  const autoBalance = () => {
    const numCountries = allocations.length
    const patientsPerCountry = Math.floor(totalPatients / numCountries)
    const remainder = totalPatients % numCountries

    const balanced = allocations.map((alloc, idx) => ({
      ...alloc,
      patients: patientsPerCountry + (idx < remainder ? 1 : 0),
      percentage: ((patientsPerCountry + (idx < remainder ? 1 : 0)) / totalPatients) * 100,
      estimated_cost: ((patientsPerCountry + (idx < remainder ? 1 : 0)) / totalPatients) * totalBudget
    }))

    setAllocations(balanced)
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className={isValid ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Users className="h-4 w-4" />
              Patient Allocation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalAllocatedPatients} / {totalPatients}
            </div>
            <Progress 
              value={(totalAllocatedPatients / totalPatients) * 100} 
              className="mt-2"
            />
            {!isValid && totalAllocatedPatients !== totalPatients && (
              <p className="text-xs text-amber-700 mt-2">
                {totalAllocatedPatients > totalPatients ? 'Over-allocated' : 'Under-allocated'} by {Math.abs(totalAllocatedPatients - totalPatients)} patients
              </p>
            )}
          </CardContent>
        </Card>

        <Card className={Math.abs(totalAllocatedPercentage - 100) < 0.1 ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Percentage Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalAllocatedPercentage.toFixed(1)}%
            </div>
            <Progress 
              value={totalAllocatedPercentage} 
              className="mt-2"
            />
            {Math.abs(totalAllocatedPercentage - 100) >= 0.1 && (
              <p className="text-xs text-amber-700 mt-2">
                {totalAllocatedPercentage > 100 ? 'Over' : 'Under'} by {Math.abs(100 - totalAllocatedPercentage).toFixed(1)}%
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Estimated Budget
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${(totalAllocatedCost / 1_000_000).toFixed(1)}M
            </div>
            <p className="text-xs text-slate-600 mt-2">
              of ${(totalBudget / 1_000_000).toFixed(1)}M total
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Country Allocations */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Country Allocations</CardTitle>
              <CardDescription>Distribute patients and budget across countries</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button onClick={autoBalance} variant="outline" size="sm">
                Auto Balance
              </Button>
              {isValid && (
                <Badge className="bg-green-100 text-green-800 border-green-200">
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Valid
                </Badge>
              )}
              {!isValid && (
                <Badge className="bg-amber-100 text-amber-800 border-amber-200">
                  <AlertCircle className="mr-1 h-3 w-3" />
                  Needs Adjustment
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Country</th>
                  <th className="text-center p-3 font-medium">Code</th>
                  <th className="text-center p-3 font-medium">Patients</th>
                  <th className="text-center p-3 font-medium">%</th>
                  <th className="text-center p-3 font-medium">Sites</th>
                  <th className="text-center p-3 font-medium">Est. Cost</th>
                  <th className="text-center p-3 font-medium">Currency</th>
                  <th className="text-center p-3 font-medium">FX Rate</th>
                  <th className="text-center p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {allocations.map((alloc, idx) => (
                  <tr key={idx} className="border-b hover:bg-slate-50">
                    <td className="p-3">
                      <Input
                        value={alloc.country}
                        onChange={(e) => updateAllocation(idx, 'country', e.target.value)}
                        className="min-w-[150px]"
                      />
                    </td>
                    <td className="p-3 text-center">
                      <Input
                        value={alloc.country_code}
                        onChange={(e) => updateAllocation(idx, 'country_code', e.target.value)}
                        className="w-20 text-center"
                        maxLength={3}
                      />
                    </td>
                    <td className="p-3">
                      <Input
                        type="number"
                        value={alloc.patients}
                        onChange={(e) => updateAllocation(idx, 'patients', e.target.value)}
                        className="w-24 text-center"
                        min={0}
                        max={totalPatients}
                      />
                    </td>
                    <td className="p-3">
                      <Input
                        type="number"
                        value={alloc.percentage.toFixed(1)}
                        onChange={(e) => updateAllocation(idx, 'percentage', e.target.value)}
                        className="w-20 text-center"
                        min={0}
                        max={100}
                        step={0.1}
                      />
                    </td>
                    <td className="p-3">
                      <Input
                        type="number"
                        value={alloc.sites}
                        onChange={(e) => updateAllocation(idx, 'sites', e.target.value)}
                        className="w-20 text-center"
                        min={1}
                      />
                    </td>
                    <td className="p-3 text-right font-medium">
                      ${(alloc.estimated_cost / 1_000_000).toFixed(2)}M
                    </td>
                    <td className="p-3 text-center">
                      <Input
                        value={alloc.currency}
                        onChange={(e) => updateAllocation(idx, 'currency', e.target.value)}
                        className="w-20 text-center"
                        maxLength={3}
                      />
                    </td>
                    <td className="p-3">
                      <Input
                        type="number"
                        value={alloc.exchange_rate}
                        onChange={(e) => updateAllocation(idx, 'exchange_rate', e.target.value)}
                        className="w-24 text-center"
                        min={0}
                        step={0.01}
                      />
                    </td>
                    <td className="p-3 text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeCountry(idx)}
                        disabled={allocations.length <= 1}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </td>
                  </tr>
                ))}

                {/* Add New Country Row */}
                <tr className="bg-slate-50">
                  <td className="p-3">
                    <Input
                      placeholder="Country name"
                      value={newCountry}
                      onChange={(e) => setNewCountry(e.target.value)}
                    />
                  </td>
                  <td className="p-3">
                    <Input
                      placeholder="Code"
                      value={newCountryCode}
                      onChange={(e) => setNewCountryCode(e.target.value.toUpperCase())}
                      className="w-20 text-center"
                      maxLength={3}
                    />
                  </td>
                  <td colSpan={6} className="p-3">
                    <Button 
                      onClick={addCountry} 
                      variant="outline" 
                      size="sm"
                      className="w-full"
                      disabled={!newCountry || !newCountryCode}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Add Country
                    </Button>
                  </td>
                </tr>

                {/* Totals Row */}
                <tr className="bg-blue-50 font-semibold">
                  <td className="p-3">TOTAL</td>
                  <td className="p-3 text-center">{allocations.length}</td>
                  <td className="p-3 text-center">{totalAllocatedPatients}</td>
                  <td className="p-3 text-center">{totalAllocatedPercentage.toFixed(1)}%</td>
                  <td className="p-3 text-center">{allocations.reduce((sum, a) => sum + a.sites, 0)}</td>
                  <td className="p-3 text-right">${(totalAllocatedCost / 1_000_000).toFixed(2)}M</td>
                  <td colSpan={3}></td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}







