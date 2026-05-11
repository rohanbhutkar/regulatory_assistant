"use client"

import React, { useState, useEffect, useMemo } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import type { ReferenceTrial } from "@/lib/types/study-types"
import { useTrialTroveData } from "@/lib/hooks/use-trialtrove-data"
import { convertTrialTroveToReferenceTrial } from "@/lib/utils/trialtrove-converter"
import { 
  Search, 
  ExternalLink, 
  Check, 
  RefreshCw, 
  Filter, 
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  X
} from "lucide-react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"

interface ReferenceTrialsTabProps {
  trials: ReferenceTrial[]
  onTrialsChange: (trials: ReferenceTrial[]) => void
}

type SortDirection = 'asc' | 'desc' | null
type SortableColumn = 'trialId' | 'nctId' | 'title' | 'indication' | 'phase' | 'status' | 'therapeuticArea' | 'primaryEndpoint' | 'sponsor' | 'countries' | 'startDate'

interface ColumnFilter {
  column: string
  values: Set<string>
}

interface ColumnFilterProps {
  column: string
  label: string
  allValues: string[]
  selectedValues: Set<string>
  onFilterChange: (values: Set<string>) => void
  sortDirection: SortDirection
  onSort: () => void
}

function ColumnFilterDropdown({ 
  column, 
  label, 
  allValues, 
  selectedValues, 
  onFilterChange,
  sortDirection,
  onSort
}: ColumnFilterProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [isOpen, setIsOpen] = useState(false)
  
  // Filter values based on search term
  const filteredValues = useMemo(() => {
    return allValues.filter(value => {
      // Convert to string and handle null/undefined
      const valueStr = String(value || '').toLowerCase()
      return valueStr.includes(searchTerm.toLowerCase())
    }).sort()
  }, [allValues, searchTerm])
  
  const allSelected = allValues.length > 0 && selectedValues.size === allValues.length
  const someSelected = selectedValues.size > 0 && selectedValues.size < allValues.length
  
  const handleToggleAll = () => {
    if (allSelected) {
      onFilterChange(new Set())
    } else {
      onFilterChange(new Set(allValues))
    }
  }
  
  const handleToggle = (value: string) => {
    const newValues = new Set(selectedValues)
    if (newValues.has(value)) {
      newValues.delete(value)
    } else {
      newValues.add(value)
    }
    onFilterChange(newValues)
  }
  
  const handleSelectAllVisible = () => {
    const newValues = new Set(selectedValues)
    filteredValues.forEach(value => newValues.add(value))
    onFilterChange(newValues)
  }
  
  const handleDeselectAllVisible = () => {
    const newValues = new Set(selectedValues)
    filteredValues.forEach(value => newValues.delete(value))
    onFilterChange(newValues)
  }
  
  const hasActiveFilter = selectedValues.size > 0 && selectedValues.size < allValues.length
  
  return (
    <div className="flex items-center gap-1">
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button 
            variant="ghost" 
            size="sm" 
            className={`h-8 px-2 hover:bg-secondary/80 ${hasActiveFilter ? 'text-primary font-semibold' : ''}`}
          >
            <span className="mr-1">{label}</span>
            {hasActiveFilter && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                {selectedValues.size}
              </Badge>
            )}
            <ChevronDown className="ml-1 h-3 w-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0" align="start">
          <div className="space-y-2 p-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={`Search ${label.toLowerCase()}...`}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 h-8 text-sm"
              />
              {searchTerm && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                  onClick={() => setSearchTerm("")}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
            
            {/* Action Buttons */}
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                className="h-7 text-xs flex-1"
                onClick={handleToggleAll}
              >
                {allSelected ? 'Deselect All' : 'Select All'}
              </Button>
              {searchTerm && filteredValues.length < allValues.length && (
                <>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="h-7 text-xs flex-1"
                    onClick={handleSelectAllVisible}
                  >
                    Select Visible
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="h-7 text-xs flex-1"
                    onClick={handleDeselectAllVisible}
                  >
                    Deselect Visible
                  </Button>
                </>
              )}
            </div>
            
            <div className="border-b border-border/50 my-2" />
            
            {/* Values List */}
            <ScrollArea className="h-64">
              <div className="space-y-1">
                {filteredValues.length === 0 ? (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    No matches found
                  </div>
                ) : (
                  filteredValues.map((value) => (
                    <div
                      key={value}
                      className="flex items-center space-x-2 px-2 py-1.5 hover:bg-secondary/50 rounded cursor-pointer"
                      onClick={() => handleToggle(value)}
                    >
                      <Checkbox
                        checked={selectedValues.has(value)}
                        onCheckedChange={() => handleToggle(value)}
                      />
                      <span className="text-sm flex-1 truncate" title={value}>
                        {value}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
            
            {/* Summary */}
            <div className="border-b border-border/50 my-2" />
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span>{selectedValues.size} of {allValues.length} selected</span>
              {hasActiveFilter && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => onFilterChange(new Set())}
                >
                  Clear
                </Button>
              )}
            </div>
          </div>
        </PopoverContent>
      </Popover>
      
      {/* Sort Button */}
      <Button
        variant="ghost"
        size="sm"
        className="h-8 w-8 p-0"
        onClick={onSort}
      >
        {sortDirection === 'asc' && <ChevronUp className="h-4 w-4" />}
        {sortDirection === 'desc' && <ChevronDown className="h-4 w-4" />}
        {sortDirection === null && <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />}
      </Button>
    </div>
  )
}

export function ReferenceTrialsTab({ trials, onTrialsChange }: ReferenceTrialsTabProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [sortColumn, setSortColumn] = useState<SortableColumn | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)
  
  // Column filters state
  const [columnFilters, setColumnFilters] = useState<Map<string, Set<string>>>(new Map())
  
  // Fetch TrialTrove data
  const { data: trialTroveData, loading, error, totalCount, refetch } = useTrialTroveData(searchTerm, 1000)
  
  // Convert TrialTrove data to ReferenceTrial format
  const convertedFromBackend = trialTroveData.map(convertTrialTroveToReferenceTrial)
  
  // Merge trials from context with backend data
  const convertedTrials = useMemo(() => {
    const trialMap = new Map()
    
    trials.forEach(trial => {
      trialMap.set(trial.id, trial)
    })
    
    convertedFromBackend.forEach(trial => {
      if (!trialMap.has(trial.id)) {
        trialMap.set(trial.id, trial)
      }
    })
    
    return Array.from(trialMap.values())
  }, [trials, convertedFromBackend])
  
  // Extract unique values for each column
  const uniqueColumnValues = useMemo(() => {
    // Helper to safely extract and filter values
    const getUniqueValues = (values: any[]) => {
      return [...new Set(values
        .filter(v => v != null && String(v).trim() !== '') // Filter out null, undefined, empty
        .map(v => String(v).trim()) // Convert to string and trim
      )].sort()
    }
    
    return {
      trialId: getUniqueValues(convertedTrials.map(t => t.trialId)),
      nctId: getUniqueValues(convertedTrials.map(t => t.nctId)),
      indication: getUniqueValues(convertedTrials.map(t => t.indication)),
      phase: getUniqueValues(convertedTrials.map(t => t.phase)),
      status: getUniqueValues(convertedTrials.map(t => t.status)),
      therapeuticArea: getUniqueValues(convertedTrials.map(t => t.therapeuticArea)),
      primaryEndpoint: getUniqueValues(convertedTrials.map(t => t.primaryEndpoint)),
      sponsor: getUniqueValues(convertedTrials.map(t => t.sponsor)),
      countries: getUniqueValues(convertedTrials.map(t => t.countries)),
    }
  }, [convertedTrials])
  
  // Apply filters and sorting
  const filteredAndSortedTrials = useMemo(() => {
    let filtered = convertedTrials.filter((trial) => {
      // Helper to safely convert to lowercase string
      const toLower = (val: any) => String(val || '').toLowerCase()
      
      // Global search filter
      const matchesSearch = !searchTerm || 
        toLower(trial.title).includes(searchTerm.toLowerCase()) ||
        toLower(trial.indication).includes(searchTerm.toLowerCase()) ||
        toLower(trial.nctId).includes(searchTerm.toLowerCase()) ||
        toLower(trial.sponsor).includes(searchTerm.toLowerCase()) ||
        toLower(trial.trialId).includes(searchTerm.toLowerCase()) ||
        toLower(trial.therapeuticArea).includes(searchTerm.toLowerCase()) ||
        toLower(trial.primaryEndpoint).includes(searchTerm.toLowerCase()) ||
        toLower(trial.countries).includes(searchTerm.toLowerCase())
      
      if (!matchesSearch) return false
      
      // Column filters
      for (const [column, selectedValues] of columnFilters.entries()) {
        if (selectedValues.size === 0) continue
        
        const trialValue = trial[column as keyof ReferenceTrial]
        const normalizedValue = String(trialValue || '').trim()
        
        if (!selectedValues.has(normalizedValue)) {
          return false
        }
      }
      
      return true
    })
    
    // Apply sorting
    if (sortColumn && sortDirection) {
      filtered = [...filtered].sort((a, b) => {
        const aValue = a[sortColumn]
        const bValue = b[sortColumn]
        
        // Handle dates
        if (sortColumn === 'startDate') {
          const aDate = aValue ? new Date(aValue as string).getTime() : 0
          const bDate = bValue ? new Date(bValue as string).getTime() : 0
          return sortDirection === 'asc' ? aDate - bDate : bDate - aDate
        }
        
        // Handle strings
        const aStr = String(aValue || '').toLowerCase()
        const bStr = String(bValue || '').toLowerCase()
        
        if (sortDirection === 'asc') {
          return aStr < bStr ? -1 : aStr > bStr ? 1 : 0
        } else {
          return aStr > bStr ? -1 : aStr < bStr ? 1 : 0
        }
      })
    }
    
    return filtered
  }, [convertedTrials, searchTerm, columnFilters, sortColumn, sortDirection])
  
  const toggleTrial = (trialId: string) => {
    const updatedTrials = convertedTrials.map((trial) => 
      trial.id === trialId ? { ...trial, selected: !trial.selected } : trial
    )
    onTrialsChange(updatedTrials)
  }
  
  const selectedCount = convertedTrials.filter((t) => t.selected).length
  
  const handleColumnFilterChange = (column: string, values: Set<string>) => {
    setColumnFilters(prev => {
      const newFilters = new Map(prev)
      if (values.size === 0) {
        newFilters.delete(column)
      } else {
        newFilters.set(column, values)
      }
      return newFilters
    })
  }
  
  const handleSort = (column: SortableColumn) => {
    if (sortColumn === column) {
      if (sortDirection === 'asc') {
        setSortDirection('desc')
      } else if (sortDirection === 'desc') {
        setSortDirection(null)
        setSortColumn(null)
      }
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }
  
  const clearAllFilters = () => {
    setColumnFilters(new Map())
    setSearchTerm("")
    setSortColumn(null)
    setSortDirection(null)
  }
  
  const hasActiveFilters = columnFilters.size > 0 || searchTerm !== ""
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-4">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Loading TrialTrove data...</p>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-4">
          <p className="text-destructive">Error loading trials: {error}</p>
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-4">
      {/* Header with search and controls */}
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search across all columns..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-card border-border/50"
            />
            {searchTerm && (
              <Button
                variant="ghost"
                size="sm"
                className="absolute right-2 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                onClick={() => setSearchTerm("")}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearAllFilters}
              >
                <X className="h-4 w-4 mr-2" />
                Clear All Filters
              </Button>
            )}
            <Badge variant="outline" className="text-sm">
              {selectedCount} selected
            </Badge>
            <Badge variant="secondary" className="text-sm">
              {filteredAndSortedTrials.length} of {totalCount.toLocaleString()} trials
            </Badge>
          </div>
        </div>
        
        {/* Active Filters Summary */}
        {hasActiveFilters && (
          <div className="flex flex-wrap gap-2">
            {searchTerm && (
              <Badge variant="secondary" className="text-xs">
                Search: "{searchTerm}"
                <button
                  onClick={() => setSearchTerm("")}
                  className="ml-1 hover:text-destructive"
                >
                  ×
                </button>
              </Badge>
            )}
            {Array.from(columnFilters.entries()).map(([column, values]) => (
              <Badge key={column} variant="secondary" className="text-xs">
                {column}: {values.size} selected
                <button
                  onClick={() => handleColumnFilterChange(column, new Set())}
                  className="ml-1 hover:text-destructive"
                >
                  ×
                </button>
              </Badge>
            ))}
            {sortColumn && (
              <Badge variant="secondary" className="text-xs">
                Sorted by: {sortColumn} ({sortDirection})
                <button
                  onClick={() => { setSortColumn(null); setSortDirection(null) }}
                  className="ml-1 hover:text-destructive"
                >
                  ×
                </button>
              </Badge>
            )}
          </div>
        )}
      </div>
      
      {/* Table with column filters */}
      <div className="border border-border/50 rounded-lg overflow-hidden bg-card">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-secondary/50 hover:bg-secondary/50">
                <TableHead className="w-12">
                  <Checkbox
                    checked={selectedCount === filteredAndSortedTrials.length && filteredAndSortedTrials.length > 0}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        const updatedTrials = convertedTrials.map(trial => 
                          filteredAndSortedTrials.find(ft => ft.id === trial.id)
                            ? { ...trial, selected: true }
                            : trial
                        )
                        onTrialsChange(updatedTrials)
                      } else {
                        const updatedTrials = convertedTrials.map(trial => 
                          filteredAndSortedTrials.find(ft => ft.id === trial.id)
                            ? { ...trial, selected: false }
                            : trial
                        )
                        onTrialsChange(updatedTrials)
                      }
                    }}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="trialId"
                    label="Trial ID"
                    allValues={uniqueColumnValues.trialId}
                    selectedValues={columnFilters.get('trialId') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('trialId', values)}
                    sortDirection={sortColumn === 'trialId' ? sortDirection : null}
                    onSort={() => handleSort('trialId')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="nctId"
                    label="NCT ID"
                    allValues={uniqueColumnValues.nctId}
                    selectedValues={columnFilters.get('nctId') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('nctId', values)}
                    sortDirection={sortColumn === 'nctId' ? sortDirection : null}
                    onSort={() => handleSort('nctId')}
                  />
                </TableHead>
                <TableHead>
                  <div className="flex items-center gap-1">
                    <span>Trial Title</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => handleSort('title')}
                    >
                      {sortColumn === 'title' && sortDirection === 'asc' && <ChevronUp className="h-4 w-4" />}
                      {sortColumn === 'title' && sortDirection === 'desc' && <ChevronDown className="h-4 w-4" />}
                      {(sortColumn !== 'title' || sortDirection === null) && <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />}
                    </Button>
                  </div>
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="indication"
                    label="Indication"
                    allValues={uniqueColumnValues.indication}
                    selectedValues={columnFilters.get('indication') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('indication', values)}
                    sortDirection={sortColumn === 'indication' ? sortDirection : null}
                    onSort={() => handleSort('indication')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="phase"
                    label="Phase"
                    allValues={uniqueColumnValues.phase}
                    selectedValues={columnFilters.get('phase') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('phase', values)}
                    sortDirection={sortColumn === 'phase' ? sortDirection : null}
                    onSort={() => handleSort('phase')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="status"
                    label="Status"
                    allValues={uniqueColumnValues.status}
                    selectedValues={columnFilters.get('status') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('status', values)}
                    sortDirection={sortColumn === 'status' ? sortDirection : null}
                    onSort={() => handleSort('status')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="therapeuticArea"
                    label="Therapeutic Area"
                    allValues={uniqueColumnValues.therapeuticArea}
                    selectedValues={columnFilters.get('therapeuticArea') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('therapeuticArea', values)}
                    sortDirection={sortColumn === 'therapeuticArea' ? sortDirection : null}
                    onSort={() => handleSort('therapeuticArea')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="primaryEndpoint"
                    label="Primary Endpoint"
                    allValues={uniqueColumnValues.primaryEndpoint}
                    selectedValues={columnFilters.get('primaryEndpoint') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('primaryEndpoint', values)}
                    sortDirection={sortColumn === 'primaryEndpoint' ? sortDirection : null}
                    onSort={() => handleSort('primaryEndpoint')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="sponsor"
                    label="Sponsor"
                    allValues={uniqueColumnValues.sponsor}
                    selectedValues={columnFilters.get('sponsor') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('sponsor', values)}
                    sortDirection={sortColumn === 'sponsor' ? sortDirection : null}
                    onSort={() => handleSort('sponsor')}
                  />
                </TableHead>
                <TableHead>
                  <ColumnFilterDropdown
                    column="countries"
                    label="Countries"
                    allValues={uniqueColumnValues.countries}
                    selectedValues={columnFilters.get('countries') || new Set()}
                    onFilterChange={(values) => handleColumnFilterChange('countries', values)}
                    sortDirection={sortColumn === 'countries' ? sortDirection : null}
                    onSort={() => handleSort('countries')}
                  />
                </TableHead>
                <TableHead>
                  <div className="flex items-center gap-1">
                    <span>Start Date</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => handleSort('startDate')}
                    >
                      {sortColumn === 'startDate' && sortDirection === 'asc' && <ChevronUp className="h-4 w-4" />}
                      {sortColumn === 'startDate' && sortDirection === 'desc' && <ChevronDown className="h-4 w-4" />}
                      {(sortColumn !== 'startDate' || sortDirection === null) && <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />}
                    </Button>
                  </div>
                </TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAndSortedTrials.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={13} className="text-center py-8 text-muted-foreground">
                    No trials match the current filters
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedTrials.map((trial) => (
                  <TableRow key={trial.id} className="hover:bg-secondary/30 transition-colors">
                    <TableCell>
                      <Checkbox checked={trial.selected} onCheckedChange={() => toggleTrial(trial.id)} />
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-mono">
                        {trial.trialId}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-mono">
                        {trial.nctId}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium text-foreground max-w-md">
                      <div className="line-clamp-2">{trial.title}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {trial.indication}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {trial.phase}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={trial.status === 'Open' ? 'default' : 'secondary'} 
                        className="text-xs"
                      >
                        {trial.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {trial.therapeuticArea}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs">
                      <div className="line-clamp-2">{trial.primaryEndpoint}</div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs">
                      <div className="line-clamp-2">{trial.sponsor}</div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {trial.countries}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {trial.startDate ? new Date(trial.startDate).toLocaleDateString() : 'N/A'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {trial.recordUrl && (
                          <Button variant="ghost" size="sm" asChild>
                            <a href={trial.recordUrl} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
      
      {/* Results summary */}
      <div className="text-sm text-muted-foreground text-center">
        Showing {filteredAndSortedTrials.length} of {totalCount.toLocaleString()} trials
        {hasActiveFilters && " (filtered)"}
      </div>
      
      {/* Selected Trials Summary */}
      {selectedCount > 0 && (
        <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Check className="h-4 w-4 text-primary" />
            <span className="font-semibold text-foreground">{selectedCount} Reference Trials Selected</span>
          </div>
          <p className="text-sm text-muted-foreground">
            These trials will be used as references for protocol generation and design optimization.
          </p>
        </div>
      )}
    </div>
  )
}

