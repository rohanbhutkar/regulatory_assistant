"use client"

import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Check, ChevronsUpDown, Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ProcedureOption {
  code: string
  name: string
  confidence_score?: number
  isMatched?: boolean
  isCurrent?: boolean
}

interface ProcedureSelectorProps {
  currentCode: string
  currentName: string
  matchedOptions: ProcedureOption[]
  otherProcedures: ProcedureOption[]
  onSelect: (code: string, name: string, confidenceScore?: number) => void
}

export function ProcedureSelectorDropdown({
  currentCode,
  currentName,
  matchedOptions,
  otherProcedures,
  onSelect
}: ProcedureSelectorProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  // Filter procedures based on search
  const filteredMatched = useMemo(() => {
    if (!searchQuery.trim()) return matchedOptions
    const query = searchQuery.toLowerCase()
    return matchedOptions.filter(opt => 
      opt.code.toLowerCase().includes(query) ||
      opt.name.toLowerCase().includes(query)
    )
  }, [matchedOptions, searchQuery])

  const filteredOther = useMemo(() => {
    if (!searchQuery.trim()) return otherProcedures.slice(0, 100) // Limit initial display
    const query = searchQuery.toLowerCase()
    return otherProcedures.filter(opt => 
      opt.code.toLowerCase().includes(query) ||
      opt.name.toLowerCase().includes(query)
    ).slice(0, 100) // Limit results
  }, [otherProcedures, searchQuery])

  const handleSelect = (option: ProcedureOption) => {
    onSelect(option.code, option.name, option.confidence_score)
    setOpen(false)
    setSearchQuery("")
  }

  const getConfidenceBadge = (score?: number) => {
    if (!score) return null
    const percentage = Math.round(score * 100)
    return (
      <Badge 
        variant={percentage >= 80 ? "default" : "secondary"}
        className={`text-xs ${percentage >= 80 ? "bg-green-600" : "bg-amber-600"}`}
      >
        {percentage}%
      </Badge>
    )
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
          <div className="flex items-center gap-2 flex-1 text-left">
            <code className="text-xs bg-gray-100 px-2 py-1 rounded">
              {currentCode}
            </code>
            <span className="text-sm truncate">{currentName}</span>
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        className="w-full min-w-[var(--radix-popover-trigger-width)] max-w-[min(90vw,700px)] p-0" 
        align="start"
        sideOffset={4}
      >
        {/* Search Input */}
        <div className="flex items-center border-b px-3 py-2">
          <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
          <Input
            placeholder="Search procedures by code or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 border-0 p-0 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
        </div>

        {/* Options List */}
        <ScrollArea className="max-h-[400px]">
          <div className="p-2">
            {/* Matched Procedures Section */}
            {filteredMatched.length > 0 && (
              <div className="mb-2">
                <div className="px-2 py-1 text-xs font-semibold text-muted-foreground">
                  AI Matched Procedures
                </div>
                {filteredMatched.map((option) => {
                  const isSelected = option.code === currentCode
                  return (
                    <div
                      key={option.code}
                      onClick={() => handleSelect(option)}
                      className={cn(
                        "flex items-center justify-between rounded-sm px-2 py-2 cursor-pointer hover:bg-accent",
                        isSelected && "bg-accent/50"
                      )}
                      title={option.name}
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {isSelected && <Check className="h-4 w-4 text-primary shrink-0" />}
                        {!isSelected && <div className="h-4 w-4 shrink-0" />}
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded shrink-0">
                          {option.code}
                        </code>
                        <span className="text-sm truncate">{option.name}</span>
                      </div>
                      {getConfidenceBadge(option.confidence_score)}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Divider */}
            {filteredMatched.length > 0 && filteredOther.length > 0 && (
              <div className="my-2 border-t" />
            )}

            {/* All Other Procedures Section */}
            {filteredOther.length > 0 && (
              <div>
                <div className="px-2 py-1 text-xs font-semibold text-muted-foreground">
                  All Procedures {!searchQuery && `(showing first 100)`}
                </div>
                {filteredOther.map((option) => {
                  const isSelected = option.code === currentCode
                  return (
                    <div
                      key={option.code}
                      onClick={() => handleSelect(option)}
                      className={cn(
                        "flex items-center gap-2 rounded-sm px-2 py-2 cursor-pointer hover:bg-accent",
                        isSelected && "bg-accent/50"
                      )}
                      title={option.name}
                    >
                      {isSelected && <Check className="h-4 w-4 text-primary shrink-0" />}
                      {!isSelected && <div className="h-4 w-4 shrink-0" />}
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded shrink-0">
                        {option.code}
                      </code>
                      <span className="text-sm truncate flex-1">{option.name}</span>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Empty State */}
            {filteredMatched.length === 0 && filteredOther.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground">
                No procedures found matching "{searchQuery}"
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        {searchQuery && (filteredMatched.length > 0 || filteredOther.length > 0) && (
          <div className="border-t px-3 py-2 text-xs text-muted-foreground">
            {filteredMatched.length + filteredOther.length} result{(filteredMatched.length + filteredOther.length) !== 1 ? 's' : ''} found
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

