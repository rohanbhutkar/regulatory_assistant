"use client"

import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Users } from 'lucide-react'
import type { SiteFilterState, SiteFilterOptions } from '@/lib/types/site-filter-types'

interface DemographicFilterDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  filters: SiteFilterState
  options: SiteFilterOptions | null
  onFilterChange: (filters: SiteFilterState) => void
  onReset: () => void
}

export function DemographicFilterDialog({
  open,
  onOpenChange,
  filters,
  options,
  onFilterChange,
  onReset
}: DemographicFilterDialogProps) {
  const [localFilters, setLocalFilters] = useState<SiteFilterState>(filters)

  useEffect(() => {
    setLocalFilters(filters)
  }, [filters])

  const handleApply = () => {
    onFilterChange(localFilters)
    onOpenChange(false)
  }

  const handleReset = () => {
    onReset()
    onOpenChange(false)
  }

  const toggleHouseholdIncome = (income: string) => {
    setLocalFilters(prev => ({
      ...prev,
      householdIncome: prev.householdIncome.includes(income)
        ? prev.householdIncome.filter(i => i !== income)
        : [...prev.householdIncome, income]
    }))
  }

  const toggleEducationLevel = (level: string) => {
    setLocalFilters(prev => ({
      ...prev,
      educationLevel: prev.educationLevel.includes(level)
        ? prev.educationLevel.filter(l => l !== level)
        : [...prev.educationLevel, level]
    }))
  }

  const toggleInsuranceCoverage = (coverage: string) => {
    setLocalFilters(prev => ({
      ...prev,
      insuranceCoverage: prev.insuranceCoverage.includes(coverage)
        ? prev.insuranceCoverage.filter(c => c !== coverage)
        : [...prev.insuranceCoverage, coverage]
    }))
  }

  if (!options) {
    return null
  }

  const demographicFilterCount = 
    localFilters.householdIncome.length +
    localFilters.educationLevel.length +
    localFilters.insuranceCoverage.length

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Users className="h-4 w-4" />
          Demographics
          {demographicFilterCount > 0 && (
            <Badge variant="secondary" className="ml-1">
              {demographicFilterCount}
            </Badge>
          )}
        </Button>
      </DialogTrigger>
      <DialogContent 
        className="max-w-3xl max-h-[80vh] border-border shadow-2xl"
      >
        <DialogHeader>
          <DialogTitle>Demographic Filters</DialogTitle>
          <DialogDescription>
            Filter sites based on Social Determinants of Health (SDOH) data
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[500px] pr-4">
          <Accordion type="multiple" className="w-full">
            {/* Socioeconomic Factors */}
            <AccordionItem value="socioeconomic">
              <AccordionTrigger>
                Socioeconomic Factors
                {localFilters.householdIncome.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.householdIncome.length}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                {/* Household Income */}
                {options.householdIncome.length > 0 && (
                  <div className="space-y-2">
                    <Label>Household Income ({localFilters.householdIncome.length} selected)</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {options.householdIncome.map(income => (
                        <div key={income} className="flex items-center space-x-2">
                          <Checkbox
                            id={`income-${income}`}
                            checked={localFilters.householdIncome.includes(income)}
                            onCheckedChange={() => toggleHouseholdIncome(income)}
                          />
                          <label
                            htmlFor={`income-${income}`}
                            className="text-sm cursor-pointer"
                          >
                            {income}
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Unemployment Rate */}
                {options.unemploymentRateRange[1] > 0 && (
                  <div className="space-y-2">
                    <Label>
                      Unemployment Rate: {localFilters.unemploymentRate[0].toFixed(0)}% - {localFilters.unemploymentRate[1].toFixed(0)}%
                    </Label>
                    <Slider
                      min={options.unemploymentRateRange[0]}
                      max={options.unemploymentRateRange[1]}
                      step={1}
                      value={localFilters.unemploymentRate}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, unemploymentRate: value as [number, number] }))
                      }
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{options.unemploymentRateRange[0]}%</span>
                      <span>{options.unemploymentRateRange[1]}%</span>
                    </div>
                  </div>
                )}

                {/* Vehicle Ownership */}
                {options.vehicleOwnershipRange[1] > 0 && (
                  <div className="space-y-2">
                    <Label>
                      Vehicle Ownership: {localFilters.vehicleOwnership[0].toFixed(0)}% - {localFilters.vehicleOwnership[1].toFixed(0)}%
                    </Label>
                    <Slider
                      min={options.vehicleOwnershipRange[0]}
                      max={options.vehicleOwnershipRange[1]}
                      step={1}
                      value={localFilters.vehicleOwnership}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, vehicleOwnership: value as [number, number] }))
                      }
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{options.vehicleOwnershipRange[0]}%</span>
                      <span>{options.vehicleOwnershipRange[1]}%</span>
                    </div>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Education */}
            <AccordionItem value="education">
              <AccordionTrigger>
                Education
                {localFilters.educationLevel.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.educationLevel.length}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                {options.educationLevel.length > 0 && (
                  <div className="space-y-2">
                    <Label>Education Level ({localFilters.educationLevel.length} selected)</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {options.educationLevel.map(level => (
                        <div key={level} className="flex items-center space-x-2">
                          <Checkbox
                            id={`education-${level}`}
                            checked={localFilters.educationLevel.includes(level)}
                            onCheckedChange={() => toggleEducationLevel(level)}
                          />
                          <label
                            htmlFor={`education-${level}`}
                            className="text-sm cursor-pointer"
                          >
                            {level}
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Healthcare Access */}
            <AccordionItem value="healthcare">
              <AccordionTrigger>
                Healthcare Access
                {localFilters.insuranceCoverage.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.insuranceCoverage.length}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                {options.insuranceCoverage.length > 0 && (
                  <div className="space-y-2">
                    <Label>Insurance Coverage ({localFilters.insuranceCoverage.length} selected)</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {options.insuranceCoverage.map(coverage => (
                        <div key={coverage} className="flex items-center space-x-2">
                          <Checkbox
                            id={`insurance-${coverage}`}
                            checked={localFilters.insuranceCoverage.includes(coverage)}
                            onCheckedChange={() => toggleInsuranceCoverage(coverage)}
                          />
                          <label
                            htmlFor={`insurance-${coverage}`}
                            className="text-sm cursor-pointer"
                          >
                            {coverage}
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </ScrollArea>

        <DialogFooter className="pt-4">
          <Button variant="outline" onClick={handleReset}>
            Reset All
          </Button>
          <Button onClick={handleApply}>
            Apply Filters
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

