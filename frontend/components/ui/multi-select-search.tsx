"use client"

import React, { useState, useMemo } from 'react'
import { Check, ChevronsUpDown, Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

interface MultiSelectSearchProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  emptyText?: string
  maxHeight?: string
}

export function MultiSelectSearch({
  options,
  selected,
  onChange,
  placeholder = "Select items...",
  emptyText = "No items found",
  maxHeight = "300px"
}: MultiSelectSearchProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  // Normalize and deduplicate options
  const normalizedOptions = useMemo(() => {
    console.log('🔍 MultiSelectSearch: Raw options received:', {
      count: options?.length || 0,
      sample: options?.slice(0, 5),
      placeholder
    })
    
    const unique = new Set<string>()
    options.forEach(opt => {
      if (opt && opt.trim()) {
        // Normalize: trim, remove extra spaces, standardize case for comparison
        const normalized = opt.trim().replace(/\s+/g, ' ')
        unique.add(normalized)
      }
    })
    
    const result = Array.from(unique).sort()
    console.log('✅ MultiSelectSearch: Normalized options:', {
      count: result.length,
      sample: result.slice(0, 5),
      placeholder
    })
    
    return result
  }, [options, placeholder])

  // Filter options based on search
  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return normalizedOptions
    const query = searchQuery.toLowerCase()
    return normalizedOptions.filter(opt => 
      opt.toLowerCase().includes(query)
    )
  }, [normalizedOptions, searchQuery])

  const handleToggle = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter(s => s !== option))
    } else {
      onChange([...selected, option])
    }
  }

  const handleSelectAllVisible = () => {
    const newSelected = new Set(selected)
    filteredOptions.forEach(opt => newSelected.add(opt))
    onChange(Array.from(newSelected))
  }

  const handleDeselectAll = () => {
    // Only deselect items that are currently visible in the filtered list
    const visibleSet = new Set(filteredOptions)
    onChange(selected.filter(s => !visibleSet.has(s)))
  }

  const handleClearAll = () => {
    onChange([])
    setSearchQuery("")
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between h-auto min-h-[40px] px-3 py-2"
        >
          <div className="flex flex-wrap gap-1 flex-1">
            {selected.length === 0 ? (
              <span className="text-muted-foreground">{placeholder}</span>
            ) : (
              <>
                {selected.slice(0, 3).map(item => (
                  <Badge
                    key={item}
                    variant="secondary"
                    className="mr-1 max-w-[150px]"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleToggle(item)
                    }}
                    title={item}
                  >
                    <span className="truncate">{item}</span>
                    <X className="ml-1 h-3 w-3 shrink-0" />
                  </Badge>
                ))}
                {selected.length > 3 && (
                  <Badge variant="secondary">
                    +{selected.length - 3} more
                  </Badge>
                )}
              </>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        className="w-full min-w-[var(--radix-popover-trigger-width)] max-w-[min(90vw,500px)] p-0 border-border shadow-lg" 
        align="start"
        sideOffset={4}
        collisionPadding={10}
      >
        <div className="flex flex-col gap-2 p-3 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSelectAllVisible}
              className="flex-1 h-8 text-xs"
              disabled={filteredOptions.length === 0}
            >
              Select All Visible ({filteredOptions.length})
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDeselectAll}
              className="flex-1 h-8 text-xs"
              disabled={selected.length === 0}
            >
              Deselect All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearAll}
              className="h-8 text-xs"
              disabled={selected.length === 0}
            >
              Clear
            </Button>
          </div>
        </div>

        <ScrollArea className="overflow-y-auto" style={{ maxHeight }}>
          <div className="p-2">
            {filteredOptions.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                {emptyText}
              </div>
            ) : (
              <div className="space-y-1">
                {filteredOptions.map((option) => {
                  const isSelected = selected.includes(option)
                  return (
                    <div
                      key={option}
                      onClick={() => handleToggle(option)}
                      className={cn(
                        "flex items-center space-x-2 rounded-sm px-2 py-2 cursor-pointer hover:bg-accent",
                        isSelected && "bg-accent/50"
                      )}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => handleToggle(option)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="text-sm flex-1 truncate" title={option}>{option}</span>
                      {isSelected && <Check className="h-4 w-4 text-primary shrink-0" />}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </ScrollArea>

        {selected.length > 0 && (
          <div className="border-t p-2 bg-muted/50">
            <div className="text-xs text-muted-foreground">
              {selected.length} item{selected.length !== 1 ? 's' : ''} selected
              {searchQuery && ` • ${filteredOptions.length} visible`}
            </div>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

