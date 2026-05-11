/**
 * Procedure Mapper Component
 * Maps SoA procedures to standardized codes using fuzzy matching
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Loader2, Check, AlertTriangle, X, Search } from 'lucide-react'
import { cppApi } from '@/lib/api/cpp-api'
import type { ProcedureMatch } from '@/lib/types/cpp'

interface ProcedureMappingItem {
  id: string
  rawText: string
  match?: ProcedureMatch
  isLoading: boolean
  userOverride?: {
    code: string
    description: string
  }
}

interface ProcedureMapperProps {
  initialProcedures?: string[]
  onMappingsComplete?: (mappings: Array<{
    raw_text: string
    code: string
    description: string
    confidence: number
  }>) => void
}

export function ProcedureMapper({ initialProcedures = [], onMappingsComplete }: ProcedureMapperProps) {
  const [procedures, setProcedures] = useState<ProcedureMappingItem[]>(
    initialProcedures.map((text, idx) => ({
      id: `proc-${idx}`,
      rawText: text,
      isLoading: false
    }))
  )
  const [newProcedureText, setNewProcedureText] = useState('')
  const [isMapping, setIsMapping] = useState(false)

  const handleAddProcedure = () => {
    if (!newProcedureText.trim()) return

    const newProc: ProcedureMappingItem = {
      id: `proc-${Date.now()}`,
      rawText: newProcedureText,
      isLoading: false
    }

    setProcedures([...procedures, newProc])
    setNewProcedureText('')
  }

  const handleRemoveProcedure = (id: string) => {
    setProcedures(procedures.filter(p => p.id !== id))
  }

  const handleMapSingle = async (id: string) => {
    const proc = procedures.find(p => p.id === id)
    if (!proc) return

    // Update loading state
    setProcedures(prev => prev.map(p => 
      p.id === id ? { ...p, isLoading: true } : p
    ))

    try {
      const response = await cppApi.mapProcedure(proc.rawText, true)
      
      setProcedures(prev => prev.map(p => 
        p.id === id ? { ...p, match: response.match, isLoading: false } : p
      ))
    } catch (error) {
      console.error('Error mapping procedure:', error)
      setProcedures(prev => prev.map(p => 
        p.id === id ? { ...p, isLoading: false } : p
      ))
    }
  }

  const handleMapAll = async () => {
    setIsMapping(true)

    // Mark all as loading
    setProcedures(prev => prev.map(p => ({ ...p, isLoading: true })))

    try {
      const texts = procedures.map(p => p.rawText)
      const response = await cppApi.mapProceduresBatch(texts, true)

      // Update all procedures with their matches
      setProcedures(prev => prev.map((p, idx) => ({
        ...p,
        match: response.matches[idx],
        isLoading: false
      })))
    } catch (error) {
      console.error('Error mapping procedures:', error)
      setProcedures(prev => prev.map(p => ({ ...p, isLoading: false })))
    } finally {
      setIsMapping(false)
    }
  }

  const handleSelectAlternative = (procId: string, code: string, description: string) => {
    setProcedures(prev => prev.map(p => 
      p.id === procId 
        ? { ...p, userOverride: { code, description } } 
        : p
    ))
  }

  const getConfidenceBadge = (score: number) => {
    if (score >= 90) {
      return <Badge className="bg-green-500">High ({score}%)</Badge>
    } else if (score >= 70) {
      return <Badge className="bg-yellow-500">Medium ({score}%)</Badge>
    } else {
      return <Badge className="bg-red-500">Low ({score}%)</Badge>
    }
  }

  const handleComplete = () => {
    const mappings = procedures
      .filter(p => p.match || p.userOverride)
      .map(p => ({
        raw_text: p.rawText,
        code: p.userOverride?.code || p.match?.matched_code || '',
        description: p.userOverride?.description || p.match?.matched_description || '',
        confidence: p.userOverride ? 100 : (p.match?.confidence_score || 0)
      }))

    onMappingsComplete?.(mappings)
  }

  const completedCount = procedures.filter(p => p.match || p.userOverride).length

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Procedure Mapping</CardTitle>
          <CardDescription>
            Map your SoA procedures to standardized codes using AI-powered fuzzy matching
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Add Procedure */}
          <div className="flex gap-2">
            <Input
              placeholder="Enter procedure text (e.g., 'ECG monitoring')"
              value={newProcedureText}
              onChange={(e) => setNewProcedureText(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddProcedure()}
            />
            <Button onClick={handleAddProcedure}>Add</Button>
          </div>

          {/* Map All Button */}
          {procedures.length > 0 && (
            <div className="flex justify-between items-center">
              <p className="text-sm text-muted-foreground">
                {completedCount} of {procedures.length} procedures mapped
              </p>
              <Button 
                onClick={handleMapAll}
                disabled={isMapping}
              >
                {isMapping && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Map All Procedures
              </Button>
            </div>
          )}

          {/* Procedure List */}
          <div className="space-y-3">
            {procedures.map((proc) => (
              <Card key={proc.id} className="border-l-4 border-l-blue-500">
                <CardContent className="pt-4">
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="font-medium">{proc.rawText}</p>
                      </div>
                      <div className="flex gap-2">
                        {!proc.match && !proc.isLoading && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMapSingle(proc.id)}
                          >
                            <Search className="mr-1 h-3 w-3" />
                            Map
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemoveProcedure(proc.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Loading */}
                    {proc.isLoading && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Mapping procedure...
                      </div>
                    )}

                    {/* Match Result */}
                    {proc.match && !proc.isLoading && (
                      <div className="space-y-2">
                        {/* User Override or Best Match */}
                        <div className="p-3 bg-green-50 rounded-md border border-green-200">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Check className="h-4 w-4 text-green-600" />
                                <span className="font-medium">
                                  {proc.userOverride ? 'Manual Selection' : 'Best Match'}
                                </span>
                                {!proc.userOverride && getConfidenceBadge(proc.match.confidence_score)}
                              </div>
                              <p className="text-sm mt-1">
                                <span className="font-mono text-blue-600">
                                  {proc.userOverride?.code || proc.match.matched_code}
                                </span>
                                {' - '}
                                {proc.userOverride?.description || proc.match.matched_description}
                              </p>
                            </div>
                          </div>
                        </div>

                        {/* Show Alternatives if confidence is not high and no override */}
                        {!proc.userOverride && proc.match.confidence_score < 90 && proc.match.alternatives.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-sm font-medium flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-yellow-600" />
                              Consider these alternatives:
                            </p>
                            <div className="space-y-1">
                              {proc.match.alternatives.slice(0, 3).map((alt, idx) => (
                                <button
                                  key={idx}
                                  className="w-full text-left p-2 hover:bg-gray-50 rounded border text-sm"
                                  onClick={() => handleSelectAlternative(proc.id, alt.code, alt.description)}
                                >
                                  <div className="flex justify-between items-center">
                                    <span>
                                      <span className="font-mono text-blue-600">{alt.code}</span>
                                      {' - '}
                                      {alt.description}
                                    </span>
                                    <Badge variant="outline">{alt.score}%</Badge>
                                  </div>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Complete Button */}
          {procedures.length > 0 && completedCount === procedures.length && (
            <Button 
              onClick={handleComplete}
              className="w-full"
            >
              <Check className="mr-2 h-4 w-4" />
              Use These Mappings
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}







