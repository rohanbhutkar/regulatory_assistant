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
import { Badge } from '@/components/ui/badge'
import { Settings } from 'lucide-react'
import { MultiSelectSearch } from '@/components/ui/multi-select-search'
import type { SiteFilterState, SiteFilterOptions } from '@/lib/types/site-filter-types'

interface SiteFilterDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  filters: SiteFilterState
  options: SiteFilterOptions | null
  onFilterChange: (filters: SiteFilterState) => void
  onReset: () => void
}

export function SiteFilterDialog({
  open,
  onOpenChange,
  filters,
  options,
  onFilterChange,
  onReset
}: SiteFilterDialogProps) {
  const [localFilters, setLocalFilters] = useState<SiteFilterState>(() => ({
    ...filters,
    regions: filters.regions || []
  }))

  // Update local filters when prop changes
  useEffect(() => {
    setLocalFilters({
      ...filters,
      regions: filters.regions || []
    })
  }, [filters])

  const handleApply = () => {
    onFilterChange(localFilters)
    onOpenChange(false)
  }

  const handleReset = () => {
    onReset()
    onOpenChange(false)
  }

  if (!options) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Settings className="h-4 w-4" />
          Filters
          {(() => {
            const filterCount = 
              (localFilters.states?.length || 0) +
              (localFilters.countries?.length || 0) +
              (localFilters.regions?.length || 0) +
              (localFilters.siteTypes?.length || 0) +
              (localFilters.therapeuticAreas?.length || 0) +
              (localFilters.sponsors?.length || 0) +
              (localFilters.minTotalTrials > 0 ? 1 : 0) +
              (localFilters.minOngoingTrials > 0 ? 1 : 0)
            
            return filterCount > 0 ? (
              <Badge variant="secondary" className="ml-1">
                {filterCount}
              </Badge>
            ) : null
          })()}
        </Button>
      </DialogTrigger>
      <DialogContent 
        className="max-w-3xl max-h-[80vh] border-border shadow-2xl"
      >
        <DialogHeader>
          <DialogTitle>Filter Sites</DialogTitle>
          <DialogDescription>
            Filter sites by trial metrics, location, and trial status
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[min(500px,60vh)] pr-4">
          <Accordion type="multiple" className="w-full">
            {/* Trial Metrics */}
            <AccordionItem value="metrics">
              <AccordionTrigger>Trial Metrics</AccordionTrigger>
              <AccordionContent className="space-y-6 pt-4">
                {/* Historical Trials */}
                <div className="space-y-2">
                  <Label>
                    Historical Trials: {localFilters.historicalTrials[0]} - {localFilters.historicalTrials[1]}
                  </Label>
                  <Slider
                    min={options.historicalTrialsRange[0]}
                    max={options.historicalTrialsRange[1]}
                    step={1}
                    value={localFilters.historicalTrials}
                    onValueChange={(value) =>
                      setLocalFilters(prev => ({ ...prev, historicalTrials: value as [number, number] }))
                    }
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{options.historicalTrialsRange[0]}</span>
                    <span>{options.historicalTrialsRange[1]}</span>
                  </div>
                </div>

                {/* Avg Enrollment */}
                <div className="space-y-2">
                  <Label>
                    Avg Enrollment: {localFilters.avgEnrollment[0].toFixed(0)} - {localFilters.avgEnrollment[1].toFixed(0)}
                  </Label>
                  <Slider
                    min={options.avgEnrollmentRange[0]}
                    max={options.avgEnrollmentRange[1]}
                    step={1}
                    value={localFilters.avgEnrollment}
                    onValueChange={(value) =>
                      setLocalFilters(prev => ({ ...prev, avgEnrollment: value as [number, number] }))
                    }
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{options.avgEnrollmentRange[0]}</span>
                    <span>{options.avgEnrollmentRange[1]}</span>
                  </div>
                </div>

                {/* Avg PSM */}
                {options.avgPsmRange[1] > 0 && (
                  <div className="space-y-2">
                    <Label>
                      Avg PSM Score: {localFilters.avgPsm[0].toFixed(0)} - {localFilters.avgPsm[1].toFixed(0)}
                    </Label>
                    <Slider
                      min={options.avgPsmRange[0]}
                      max={options.avgPsmRange[1]}
                      step={1}
                      value={localFilters.avgPsm}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, avgPsm: value as [number, number] }))
                      }
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{options.avgPsmRange[0]}</span>
                      <span>{options.avgPsmRange[1]}</span>
                    </div>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Location */}
            <AccordionItem value="location">
              <AccordionTrigger>
                Location
                {(localFilters.states?.length || 0) > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.states?.length || 0}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                {/* States */}
                <div className="space-y-2">
                  <Label>States ({localFilters.states?.length || 0} selected)</Label>
                  <div className="text-xs text-muted-foreground mb-2">
                    Search and select states to filter sites by location
                  </div>
                  <MultiSelectSearch
                    options={options.states || []}
                    selected={localFilters.states || []}
                    onChange={(selected) => setLocalFilters(prev => ({ ...prev, states: selected }))}
                    placeholder="Search and select states..."
                    emptyText="No states available"
                    maxHeight="300px"
                  />
                  {(options.states?.length || 0) > 0 && (
                    <p className="text-xs text-muted-foreground italic">
                      {options.states?.length} states available
                    </p>
                  )}
                </div>

                {/* Countries */}
                {options.countries.length > 1 && (
                  <div className="space-y-2">
                    <Label>Countries ({localFilters.countries?.length || 0} selected)</Label>
                    <div className="text-xs text-muted-foreground mb-2">
                      Search and select countries to filter sites
                    </div>
                    <MultiSelectSearch
                      options={options.countries || []}
                      selected={localFilters.countries || []}
                      onChange={(selected) => setLocalFilters(prev => ({ ...prev, countries: selected }))}
                      placeholder="Search and select countries..."
                      emptyText="No countries available"
                      maxHeight="300px"
                    />
                    {(options.countries?.length || 0) > 0 && (
                      <p className="text-xs text-muted-foreground italic">
                        {options.countries?.length} countries available
                      </p>
                    )}
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Trial Status */}
            <AccordionItem value="status">
              <AccordionTrigger>Trial Status Percentages</AccordionTrigger>
              <AccordionContent className="space-y-6 pt-4">
                {/* Planned % */}
                {options.plannedPctRange[1] > 0 && (
                  <div className="space-y-2">
                    <Label>
                      Planned: {localFilters.plannedPct[0].toFixed(0)}% - {localFilters.plannedPct[1].toFixed(0)}%
                    </Label>
                    <Slider
                      min={options.plannedPctRange[0]}
                      max={options.plannedPctRange[1]}
                      step={1}
                      value={localFilters.plannedPct}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, plannedPct: value as [number, number] }))
                      }
                    />
                  </div>
                )}

                {/* Open % */}
                {options.openPctRange[1] > 0 && (
                  <div className="space-y-2">
                    <Label>
                      Open: {localFilters.openPct[0].toFixed(0)}% - {localFilters.openPct[1].toFixed(0)}%
                    </Label>
                    <Slider
                      min={options.openPctRange[0]}
                      max={options.openPctRange[1]}
                      step={1}
                      value={localFilters.openPct}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, openPct: value as [number, number] }))
                      }
                    />
                  </div>
                )}

                {/* Completed % */}
                {options.completedPctRange[1] > 0 && (
                  <div className="space-y-2">
                    <Label>
                      Completed: {localFilters.completedPct[0].toFixed(0)}% - {localFilters.completedPct[1].toFixed(0)}%
                    </Label>
                    <Slider
                      min={options.completedPctRange[0]}
                      max={options.completedPctRange[1]}
                      step={1}
                      value={localFilters.completedPct}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, completedPct: value as [number, number] }))
                      }
                    />
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Site Type */}
            <AccordionItem value="siteType">
              <AccordionTrigger>
                Site Type
                {(localFilters.siteTypes?.length || 0) > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.siteTypes?.length || 0}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>Organization Type ({localFilters.siteTypes?.length || 0} selected)</Label>
                  <MultiSelectSearch
                    options={options.siteTypes || []}
                    selected={localFilters.siteTypes || []}
                    onChange={(selected) => setLocalFilters(prev => ({ ...prev, siteTypes: selected }))}
                    placeholder="Select organization types..."
                    emptyText="No site types available"
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Therapeutic Areas */}
            <AccordionItem value="therapeuticAreas">
              <AccordionTrigger>
                Therapeutic Areas (Experience)
                {(localFilters.therapeuticAreas?.length || 0) > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.therapeuticAreas?.length || 0}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>Disease Areas ({localFilters.therapeuticAreas?.length || 0} selected)</Label>
                  <div className="text-xs text-muted-foreground mb-2">
                    Filter sites by therapeutic areas they have experience in
                  </div>
                  <MultiSelectSearch
                    options={options.therapeuticAreas || []}
                    selected={localFilters.therapeuticAreas || []}
                    onChange={(selected) => setLocalFilters(prev => ({ ...prev, therapeuticAreas: selected }))}
                    placeholder="Search and select therapeutic areas..."
                    emptyText="No therapeutic areas available"
                    maxHeight="400px"
                  />
                  {(options.therapeuticAreas?.length || 0) > 0 && (
                    <p className="text-xs text-muted-foreground italic">
                      {options.therapeuticAreas?.length} therapeutic areas available
                    </p>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Sponsors/Companies */}
            <AccordionItem value="sponsors">
              <AccordionTrigger>
                Previous Sponsors
                {(localFilters.sponsors?.length || 0) > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {localFilters.sponsors?.length || 0}
                  </Badge>
                )}
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>Companies ({localFilters.sponsors?.length || 0} selected)</Label>
                  <div className="text-xs text-muted-foreground mb-2">
                    Filter by companies/sponsors the site has worked with
                  </div>
                  <MultiSelectSearch
                    options={options.sponsors || []}
                    selected={localFilters.sponsors || []}
                    onChange={(selected) => setLocalFilters(prev => ({ ...prev, sponsors: selected }))}
                    placeholder="Search and select sponsors..."
                    emptyText="No sponsors available"
                    maxHeight="400px"
                  />
                  {(options.sponsors?.length || 0) > 0 && (
                    <p className="text-xs text-muted-foreground italic">
                      {options.sponsors?.length} sponsors available
                    </p>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Trial Experience */}
            <AccordionItem value="experience">
              <AccordionTrigger>Trial Experience</AccordionTrigger>
              <AccordionContent className="space-y-6 pt-4">
                {/* Minimum Total Trials */}
                {options.totalTrialsRange && (
                  <div className="space-y-2">
                    <Label>
                      Minimum Total Trials: {localFilters.minTotalTrials}
                    </Label>
                    <Slider
                      min={options.totalTrialsRange[0]}
                      max={Math.min(options.totalTrialsRange[1], 500)}
                      step={10}
                      value={[localFilters.minTotalTrials]}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, minTotalTrials: value[0] }))
                      }
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{options.totalTrialsRange[0]}</span>
                      <span>{Math.min(options.totalTrialsRange[1], 500)}</span>
                    </div>
                  </div>
                )}

                {/* Minimum Ongoing Trials */}
                {options.ongoingTrialsRange && (
                  <div className="space-y-2">
                    <Label>
                      Minimum Ongoing Trials: {localFilters.minOngoingTrials}
                    </Label>
                    <Slider
                      min={options.ongoingTrialsRange[0]}
                      max={Math.min(options.ongoingTrialsRange[1], 100)}
                      step={5}
                      value={[localFilters.minOngoingTrials]}
                      onValueChange={(value) =>
                        setLocalFilters(prev => ({ ...prev, minOngoingTrials: value[0] }))
                      }
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{options.ongoingTrialsRange[0]}</span>
                      <span>{Math.min(options.ongoingTrialsRange[1], 100)}</span>
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

