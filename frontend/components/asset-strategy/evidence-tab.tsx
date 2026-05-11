"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Upload, FileText, X, Sparkles, Loader2, Search, ExternalLink, BookOpen, Database, Check } from 'lucide-react'
import { toast } from 'sonner'
import type { EvidenceArtifact } from '@/lib/types/asset-strategy-types'
import { assetStrategyAPI } from '@/lib/utils/asset-strategy-api'
import { useAssetStrategyGeneration } from '@/lib/hooks/use-asset-strategy-generation'
import { InlineActivityIndicator } from '@/components/activity/inline-activity-indicator'
import ReactMarkdown from 'react-markdown'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { useAssetStrategy } from '@/lib/contexts/asset-strategy-context'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface EvidenceTabProps {
  assetId: string
  asset?: {
    asset_name?: string
    therapeutic_area?: string
    indication?: string
  }
  readOnly?: boolean
}

export function EvidenceTab({ assetId, asset, readOnly = false }: EvidenceTabProps) {
  const { setTabContent, getTabContent } = useAssetStrategy()
  const [artifacts, setArtifacts] = useState<EvidenceArtifact[]>([])
  const [isUploading, setIsUploading] = useState(false)
  
  // Load saved state from context
  const savedState = getTabContent('evidence') || {}
  const [evidenceGapAnalysis, setEvidenceGapAnalysis] = useState<string | null>(savedState.evidenceGapAnalysis || null)
  const [isGeneratingGaps, setIsGeneratingGaps] = useState(false)
  const [searchQuery, setSearchQuery] = useState(savedState.searchQuery || '')
  const [searchType, setSearchType] = useState<'trialtrove' | 'pubmed' | 'discover'>(savedState.searchType || 'discover')
  const [searchResults, setSearchResults] = useState<any>(savedState.searchResults || null)
  const [isSearching, setIsSearching] = useState(false)
  const [expandedTrials, setExpandedTrials] = useState<Set<string>>(new Set(savedState.expandedTrials || []))
  const [addedEvidenceIds, setAddedEvidenceIds] = useState<Set<string>>(new Set(savedState.addedEvidenceIds || []))
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(savedState.collapsedSections || []))
  const { analyzeEvidenceGaps, isGenerating } = useAssetStrategyGeneration()

  // Save state to context whenever it changes
  useEffect(() => {
    setTabContent('evidence', {
      evidenceGapAnalysis,
      searchQuery,
      searchType,
      searchResults,
      expandedTrials: Array.from(expandedTrials),
      addedEvidenceIds: Array.from(addedEvidenceIds),
      collapsedSections: Array.from(collapsedSections)
    })
  }, [evidenceGapAnalysis, searchQuery, searchType, searchResults, expandedTrials, addedEvidenceIds, collapsedSections, setTabContent])

  useEffect(() => {
    loadArtifacts()
  }, [assetId])

  const loadArtifacts = async () => {
    try {
      const response = await fetch(assetStrategyAPI.getEvidence(assetId))
      if (response.ok) {
        const data = await response.json()
        setArtifacts(data)
      }
    } catch (error) {
      console.error('Failed to load evidence artifacts:', error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('artifact_type', 'protocol')

      const response = await fetch(assetStrategyAPI.createEvidence(assetId), {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        await loadArtifacts()
        toast.success('Evidence artifact uploaded successfully')
      }
    } catch (error) {
      console.error('Failed to upload evidence:', error)
      toast.error('Failed to upload evidence')
    } finally {
      setIsUploading(false)
    }
  }

  const getArtifactTypeBadge = (type: string) => {
    const colors = {
      tpp: 'bg-blue-100 text-blue-800',
      protocol: 'bg-green-100 text-green-800',
      publication: 'bg-purple-100 text-purple-800',
      submission: 'bg-orange-100 text-orange-800'
    }
    return <Badge className={colors[type as keyof typeof colors] || ''}>{type.toUpperCase()}</Badge>
  }

  const handleAIGenerateEvidenceGaps = async () => {
    const market = prompt('Enter market for evidence gap analysis:', 'US') || 'US'
    setIsGeneratingGaps(true)
    
    try {
      const response = await analyzeEvidenceGaps({
        asset_id: assetId,
        context: { market }
      })
      
      if (response?.content) {
        const analysisContent = response.content
        setEvidenceGapAnalysis(analysisContent)
        // State will be saved automatically via useEffect
        toast.success('Evidence gap analysis generated successfully')
      } else {
        toast.error('Failed to generate evidence gap analysis')
      }
    } catch (error) {
      console.error('Failed to generate evidence gaps:', error)
      toast.error('Failed to generate evidence gap analysis')
    } finally {
      setIsGeneratingGaps(false)
    }
  }

  const handleSearchEvidence = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query')
      return
    }

    setIsSearching(true)
    try {
      if (searchType === 'discover') {
        // Use the discover endpoint
        const response = await fetch(`${API_BASE_URL}/api/asset-strategy/ai/discover/evidence`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            asset_id: assetId,
            query: searchQuery
          })
        })

        if (response.ok) {
          const data = await response.json()
          setSearchResults(data)
          const totalResults = (data.trials?.length || 0) + 
                              (data.publications?.length || 0) + 
                              (data.web_results?.length || 0) +
                              (data.fda_labels?.length || 0) +
                              (data.comparators?.length || 0) +
                              (data.pricing_data?.length || 0) +
                              (data.product_brands?.length || 0) +
                              (data.sites?.length || 0)
          toast.success(`Found ${totalResults} results across all data sources`)
        } else {
          toast.error('Failed to discover evidence')
        }
      } else if (searchType === 'trialtrove') {
        // Search TrialTrove
        const response = await fetch(`${API_BASE_URL}/api/data/trialtrove`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: searchQuery,
            use_smart_search: true,
            limit: 20
          })
        })

        if (response.ok) {
          const data = await response.json()
          setSearchResults({ trials: data.trials || [] })
          toast.success(`Found ${data.trials?.length || 0} trials`)
        } else {
          toast.error('Failed to search TrialTrove')
        }
      } else if (searchType === 'pubmed') {
        // Search PubMed (would need a backend endpoint)
        toast.info('PubMed search coming soon')
      }
    } catch (error) {
      console.error('Search error:', error)
      toast.error('Search failed')
    } finally {
      setIsSearching(false)
    }
  }

  const handleAddTrialAsEvidence = async (trial: any, type: string = 'trial') => {
    try {
      // Generate unique ID for this evidence item
      // For comparators, use drug name + indication as ID
      const evidenceId = trial.nct_id || trial.pmid || trial.url || trial.id || 
                        (type === 'comparator' && trial.drug ? `comparator-${trial.drug}-${trial.indication || ''}` : null) ||
                        (type === 'pricing' && trial.procedure_code ? `pricing-${trial.procedure_code}-${trial.country || ''}` : null) ||
                        `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      
      // Check if already added
      if (addedEvidenceIds.has(evidenceId)) {
        toast.info('This evidence has already been added')
        return
      }
      
      // Handle both ClinicalTrialResult objects and raw dicts
      const trialTitle = trial.title || trial['Official Title'] || trial['Trial Title'] || 
                        trial.product_name || (type === 'comparator' ? `${trial.drug} - Comparator` : null) ||
                        (type === 'pricing' ? trialTitle || 'Pricing Data' : null) ||
                        'Evidence'
      const trialId = trial.nct_id || trial['Trial ID'] || trial['NCT ID'] || ''
      const url = trialId ? (trialId.startsWith('TrialTrove-') 
        ? `https://clinicaltrials.gov/ct2/show/${trialId.replace('TrialTrove-', '')}`
        : `https://clinicaltrials.gov/ct2/show/${trialId}`) : trial.url || undefined
      
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/assets/${assetId}/evidence/json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_type: type === 'publication' ? 'publication' : 'protocol',
          file_name: trialTitle,
          url: url,
          extracted_entities: {
            source_id: evidenceId,
            metadata: trial
          }
        })
      })

      if (response.ok) {
        // Mark as added
        setAddedEvidenceIds(new Set([...addedEvidenceIds, evidenceId]))
        await loadArtifacts()
        toast.success('Evidence added successfully')
      }
    } catch (error) {
      console.error('Failed to add evidence:', error)
      toast.error('Failed to add evidence')
    }
  }
  
  const isEvidenceAdded = (item: any, type: string = 'trial'): boolean => {
    // Generate same ID logic as handleAddTrialAsEvidence
    const evidenceId = item.nct_id || item.pmid || item.url || item.id || 
                      (type === 'comparator' && item.drug ? `comparator-${item.drug}-${item.indication || ''}` : null) ||
                      (type === 'pricing' && item.procedure_code ? `pricing-${item.procedure_code}-${item.country || ''}` : null) ||
                      `${type}-${item.title || ''}`
    return addedEvidenceIds.has(evidenceId)
  }
  
  const toggleSection = (section: string) => {
    const newCollapsed = new Set(collapsedSections)
    if (newCollapsed.has(section)) {
      newCollapsed.delete(section)
    } else {
      newCollapsed.add(section)
    }
    setCollapsedSections(newCollapsed)
  }

  const handleRemoveEvidence = async (artifactId: string) => {
    try {
      const response = await fetch(assetStrategyAPI.deleteEvidence(artifactId), {
        method: 'DELETE'
      })
      if (response.ok) {
        await loadArtifacts()
        toast.success('Evidence removed')
      } else {
        toast.error('Failed to remove evidence')
      }
    } catch (error) {
      console.error('Failed to remove evidence:', error)
      toast.error('Failed to remove evidence')
    }
  }

  const toggleTrialExpanded = (trialId: string) => {
    const newExpanded = new Set(expandedTrials)
    if (newExpanded.has(trialId)) {
      newExpanded.delete(trialId)
    } else {
      newExpanded.add(trialId)
    }
    setExpandedTrials(newExpanded)
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="artifacts" className="w-full">
        <TabsList>
          <TabsTrigger value="artifacts">Evidence Artifacts</TabsTrigger>
          <TabsTrigger value="gaps">Evidence Gap Analysis</TabsTrigger>
          <TabsTrigger value="search">Search Evidence</TabsTrigger>
        </TabsList>

        <TabsContent value="artifacts" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">Evidence Artifacts</h3>
            {!readOnly && (
              <Button
                onClick={handleAIGenerateEvidenceGaps}
                disabled={isGeneratingGaps}
                size="sm"
                variant="outline"
                className="gap-2"
              >
                {isGeneratingGaps ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Analyze Evidence Gaps
                  </>
                )}
              </Button>
            )}
          </div>

          {!readOnly && (
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <Upload className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4">
                <label htmlFor="evidence-upload" className="cursor-pointer">
                  <span className="mt-2 block text-sm font-medium text-gray-900">
                    Drop files here or click to upload
                  </span>
                  <input
                    id="evidence-upload"
                    type="file"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                    accept=".pdf,.docx,.doc"
                  />
                </label>
                <p className="mt-1 text-xs text-gray-500">PDF, DOCX, DOC up to 50MB</p>
                <p className="mt-2 text-xs text-gray-400">Uploaded documents will be analyzed for entities and linked to this asset</p>
              </div>
            </div>
          )}

          <div className="space-y-3">
            {artifacts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <FileText className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-2">No evidence artifacts uploaded</p>
              </div>
            ) : (
              artifacts.map((artifact) => (
                <Card key={artifact.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-gray-400" />
                        <div>
                          <CardTitle className="text-base">{artifact.file_name}</CardTitle>
                          <CardDescription>
                            {getArtifactTypeBadge(artifact.artifact_type)}
                            {' • '}
                            {new Date(artifact.uploaded_at).toLocaleDateString()}
                          </CardDescription>
                        </div>
                      </div>
                      {!readOnly && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveEvidence(artifact.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  {artifact.extracted_entities && Object.keys(artifact.extracted_entities).length > 0 && (
                    <CardContent>
                      <div className="text-sm text-gray-600">
                        <strong>Extracted entities:</strong> {Object.keys(artifact.extracted_entities).join(', ')}
                      </div>
                    </CardContent>
                  )}
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="gaps" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">Evidence Gap Analysis</h3>
            {!readOnly && (
              <Button
                onClick={handleAIGenerateEvidenceGaps}
                disabled={isGeneratingGaps}
                size="sm"
                variant="outline"
                className="gap-2"
              >
                {isGeneratingGaps ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Analysis
                  </>
                )}
              </Button>
            )}
          </div>

          {evidenceGapAnalysis ? (
            <Card>
              <CardContent className="pt-6">
                <div className="prose max-w-none">
                  <ReactMarkdown>{evidenceGapAnalysis}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2">No evidence gap analysis generated yet</p>
              <p className="text-sm mt-1">Click "Generate Analysis" to create one</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          <div className="flex items-center gap-2">
            <Input
              placeholder={`Search ${searchType === 'trialtrove' ? 'TrialTrove' : searchType === 'pubmed' ? 'PubMed' : 'all sources'}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearchEvidence()}
              className="flex-1"
            />
            <select
              value={searchType}
              onChange={(e) => setSearchType(e.target.value as any)}
              className="px-3 py-2 border rounded-md"
            >
              <option value="discover">All Sources</option>
              <option value="trialtrove">TrialTrove</option>
              <option value="pubmed">PubMed</option>
            </select>
            <Button
              onClick={handleSearchEvidence}
              disabled={isSearching || !searchQuery.trim()}
              className="gap-2"
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Search
            </Button>
          </div>
          <InlineActivityIndicator
            operationType="evidence_discovery"
            context={{ assetId, tab: 'evidence' }}
          />

          {searchResults && (
            <Accordion type="multiple" className="space-y-4">
              {searchResults.trials && searchResults.trials.length > 0 && (
                <AccordionItem value="trials" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Clinical Trials ({searchResults.trials.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.trials.slice(0, 20).map((trial: any, idx: number) => {
                        // Handle both ClinicalTrialResult objects and raw dicts
                        const trialId = trial.nct_id || trial['Trial ID'] || trial['NCT ID'] || `trial-${idx}`
                        const trialTitle = trial.title || trial['Official Title'] || trial['Trial Title'] || 'Untitled Trial'
                        const phase = trial.phase || trial['Phase'] || trial['Trial Phase'] || ''
                        const condition = trial.condition || trial['Disease'] || trial['Therapeutic Area'] || ''
                        const sponsor = trial.sponsor || trial['Sponsor/Collaborator'] || ''
                        const status = trial.status || trial['Trial Status'] || ''
                        const enrollment = trial.enrollment || trial['Target Accrual'] || ''
                        const startDate = trial.start_date || trial['Start Date'] || ''
                        const completionDate = trial.completion_date || trial['Full Completion Date'] || ''
                        const description = trial.description || ''
                        const intervention = trial.intervention || trial['Primary Tested Drug'] || ''
                        const metadata = trial.metadata || {}
                        const trialtroveData = metadata.trialtrove || {}
                        const isExpanded = expandedTrials.has(trialId)
                        
                        const clinicalTrialsUrl = trialId.startsWith('TrialTrove-') 
                          ? `https://clinicaltrials.gov/ct2/show/${trialId.replace('TrialTrove-', '')}`
                          : trialId ? `https://clinicaltrials.gov/ct2/show/${trialId}` : null
                        
                        return (
                        <Card key={trialId} className="hover:shadow-md transition-shadow">
                          <CardHeader className="pb-3">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <CardTitle 
                                  className="text-sm cursor-pointer hover:text-blue-600"
                                  onClick={() => toggleTrialExpanded(trialId)}
                                >
                                  {trialTitle}
                                </CardTitle>
                                <CardDescription className="mt-1 flex items-center gap-2 flex-wrap">
                                  {phase && <Badge variant="outline">{phase}</Badge>}
                                  {status && <Badge variant="outline" className={status.includes('Recruiting') ? 'bg-green-100' : ''}>{status}</Badge>}
                                  {clinicalTrialsUrl && (
                                    <a
                                      href={clinicalTrialsUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:underline text-xs"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {trialId}
                                    </a>
                                  )}
                                </CardDescription>
                              </div>
                              <div className="flex items-center gap-2">
                                {!readOnly && (() => {
                                  const isTrialAdded = isEvidenceAdded(trial, 'trial')
                                  return (
                                    <Button
                                      size="sm"
                                      variant={isTrialAdded ? "default" : "outline"}
                                      className="gap-2"
                                      onClick={() => handleAddTrialAsEvidence(trial, 'trial')}
                                      disabled={isTrialAdded}
                                    >
                                      {isTrialAdded ? (
                                        <>
                                          <Check className="h-4 w-4" />
                                          Added
                                        </>
                                      ) : (
                                        'Add'
                                      )}
                                    </Button>
                                  )
                                })()}
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => toggleTrialExpanded(trialId)}
                                >
                                  {isExpanded ? '−' : '+'}
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <div className="text-sm text-gray-600 space-y-1">
                              {condition && (
                                <p><strong>Condition:</strong> {condition}</p>
                              )}
                              {intervention && (
                                <p><strong>Intervention:</strong> {intervention}</p>
                              )}
                              {sponsor && (
                                <p><strong>Sponsor:</strong> {sponsor}</p>
                              )}
                              {(enrollment || startDate || completionDate) && (
                                <div className="flex gap-4 text-xs">
                                  {enrollment && <span><strong>Enrollment:</strong> {enrollment}</span>}
                                  {startDate && <span><strong>Start:</strong> {startDate}</span>}
                                  {completionDate && <span><strong>Completion:</strong> {completionDate}</span>}
                                </div>
                              )}
                            </div>
                            
                            {isExpanded && (
                              <div className="mt-4 pt-4 border-t space-y-3">
                                {description && (
                                  <div>
                                    <p className="text-xs font-semibold mb-1">Description:</p>
                                    <p className="text-xs text-gray-600">{description}</p>
                                  </div>
                                )}
                                {trialtroveData.patient_segment && (
                                  <div>
                                    <p className="text-xs font-semibold mb-1">Patient Segment:</p>
                                    <p className="text-xs text-gray-600">{trialtroveData.patient_segment}</p>
                                  </div>
                                )}
                                {trialtroveData.oncology_biomarker && (
                                  <div>
                                    <p className="text-xs font-semibold mb-1">Biomarker:</p>
                                    <p className="text-xs text-gray-600">{trialtroveData.oncology_biomarker}</p>
                                  </div>
                                )}
                                {trialtroveData.primary_endpoint && (
                                  <div>
                                    <p className="text-xs font-semibold mb-1">Primary Endpoint:</p>
                                    <p className="text-xs text-gray-600">{trialtroveData.primary_endpoint}</p>
                                  </div>
                                )}
                                {trialtroveData.inclusion_criteria && (
                                  <div>
                                    <p className="text-xs font-semibold mb-1">Inclusion Criteria:</p>
                                    <p className="text-xs text-gray-600 whitespace-pre-wrap">{trialtroveData.inclusion_criteria.substring(0, 500)}{trialtroveData.inclusion_criteria.length > 500 ? '...' : ''}</p>
                                  </div>
                                )}
                                {trialtroveData.countries && (
                                  <div>
                                    <p className="text-xs font-semibold mb-1">Countries:</p>
                                    <p className="text-xs text-gray-600">{trialtroveData.countries}</p>
                                  </div>
                                )}
                                {clinicalTrialsUrl && (
                                  <div className="pt-2">
                                    <a
                                      href={clinicalTrialsUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:underline text-xs"
                                    >
                                      View on ClinicalTrials.gov →
                                    </a>
                                  </div>
                                )}
                              </div>
                            )}
                          </CardContent>
                        </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {searchResults.publications && searchResults.publications.length > 0 && (
                <AccordionItem value="publications" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <BookOpen className="h-4 w-4" />
                      Publications ({searchResults.publications.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.publications.slice(0, 10).map((pub: any, idx: number) => {
                        const pubId = pub.pmid || pub.id || `pub-${idx}`
                        const isAdded = isEvidenceAdded(pub, 'publication')
                        return (
                          <Card key={idx} className={isAdded ? 'bg-green-50 border-green-200' : ''}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">{pub.title || 'Untitled Publication'}</CardTitle>
                              <CardDescription className="mt-1">
                                {pub.authors && <span>{pub.authors.join(', ')}</span>}
                                {pub.publication_date && <span className="ml-2">• {pub.publication_date}</span>}
                                {pub.pmid && (
                                  <a
                                    href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="ml-2 text-blue-600 hover:underline"
                                  >
                                    PMID: {pub.pmid}
                                  </a>
                                )}
                              </CardDescription>
                            </CardHeader>
                            {pub.abstract && (
                              <CardContent className="pt-0">
                                <p className="text-sm text-gray-600 line-clamp-3">{pub.abstract}</p>
                                {!readOnly && (
                                  <Button 
                                    size="sm" 
                                    variant={isAdded ? "default" : "outline"} 
                                    className="mt-2 gap-2"
                                    onClick={() => handleAddTrialAsEvidence(pub, 'publication')}
                                    disabled={isAdded}
                                  >
                                    {isAdded ? (
                                      <>
                                        <Check className="h-4 w-4" />
                                        Added
                                      </>
                                    ) : (
                                      'Add as Evidence'
                                    )}
                                  </Button>
                                )}
                              </CardContent>
                            )}
                          </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {searchResults.web_results && searchResults.web_results.length > 0 && (
                <AccordionItem value="web_results" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <ExternalLink className="h-4 w-4" />
                      Web Results ({searchResults.web_results.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.web_results.slice(0, 5).map((result: any, idx: number) => {
                        const isAdded = isEvidenceAdded(result, 'web_result')
                        return (
                          <Card key={idx} className={isAdded ? 'bg-green-50 border-green-200' : ''}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">
                                <a
                                  href={result.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline"
                                >
                                  {result.title || 'Untitled'}
                                </a>
                              </CardTitle>
                              <CardDescription>{result.url}</CardDescription>
                            </CardHeader>
                            {result.content && (
                              <CardContent className="pt-0">
                                <p className="text-sm text-gray-600 line-clamp-2">{result.content}</p>
                                {!readOnly && (
                                  <Button
                                    size="sm"
                                    variant={isAdded ? "default" : "outline"}
                                    className="mt-2 gap-2"
                                    onClick={() => handleAddTrialAsEvidence({
                                      title: result.title,
                                      url: result.url,
                                      content: result.content,
                                      type: 'web_result'
                                    }, 'web_result')}
                                    disabled={isAdded}
                                  >
                                    {isAdded ? (
                                      <>
                                        <Check className="h-4 w-4" />
                                        Added
                                      </>
                                    ) : (
                                      'Add as Evidence'
                                    )}
                                  </Button>
                                )}
                              </CardContent>
                            )}
                          </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {searchResults.fda_labels && searchResults.fda_labels.length > 0 && (
                <AccordionItem value="fda_labels" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      FDA Labels ({searchResults.fda_labels.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.fda_labels.slice(0, 10).map((label: any, idx: number) => {
                        const drugName = label.product_name || label.generic_name || label.drug_name || 'Unknown Drug'
                        const indication = label.indications || label.indication || 'N/A'
                        const labelId = label.id || label.document_id || `fda-${idx}`
                        const isAdded = isEvidenceAdded(label, 'fda_label')
                        return (
                          <Card key={idx} className={isAdded ? 'bg-green-50 border-green-200' : ''}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">{drugName}</CardTitle>
                              <CardDescription>{indication}</CardDescription>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="text-sm text-gray-600 space-y-1">
                                {label.clinical_pharmacology && (
                                  <p><strong>Clinical Pharmacology:</strong> {String(label.clinical_pharmacology).substring(0, 200)}...</p>
                                )}
                                {label.dosage && (
                                  <p><strong>Dosage:</strong> {String(label.dosage).substring(0, 150)}...</p>
                                )}
                              </div>
                              {!readOnly && (
                                <Button 
                                  size="sm" 
                                  variant={isAdded ? "default" : "outline"} 
                                  className="mt-2 gap-2"
                                  onClick={() => handleAddTrialAsEvidence({
                                    ...label,
                                    product_name: drugName,
                                    indications: indication
                                  }, 'fda_label')}
                                  disabled={isAdded}
                                >
                                  {isAdded ? (
                                    <>
                                      <Check className="h-4 w-4" />
                                      Added
                                    </>
                                  ) : (
                                    'Add as Evidence'
                                  )}
                                </Button>
                              )}
                            </CardContent>
                          </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {searchResults.comparators && searchResults.comparators.length > 0 && (
                <AccordionItem value="comparators" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Comparator Recommendations ({searchResults.comparators.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.comparators.slice(0, 10).map((comp: any, idx: number) => {
                        const compId = comp.drug || `comp-${idx}`
                        const isAdded = isEvidenceAdded(comp, 'comparator')
                        return (
                          <Card key={idx} className={isAdded ? 'bg-green-50 border-green-200' : ''}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">{comp.drug || 'Unknown'}</CardTitle>
                              <CardDescription>
                                {comp.indication && <span>{comp.indication}</span>}
                                {comp.similarity_score && <span className="ml-2">• Score: {comp.similarity_score.toFixed(1)}</span>}
                              </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-0">
                              {comp.rationale && <p className="text-sm text-gray-600">{comp.rationale}</p>}
                              {!readOnly && (
                                <Button 
                                  size="sm" 
                                  variant={isAdded ? "default" : "outline"} 
                                  className="mt-2 gap-2"
                                  onClick={async () => {
                                    await handleAddTrialAsEvidence({
                                      ...comp,
                                      title: `${comp.drug} - Comparator`,
                                      drug: comp.drug,
                                      indication: comp.indication
                                    }, 'comparator')
                                  }}
                                  disabled={isAdded}
                                >
                                  {isAdded ? (
                                    <>
                                      <Check className="h-4 w-4" />
                                      Added
                                    </>
                                  ) : (
                                    'Add as Evidence'
                                  )}
                                </Button>
                              )}
                            </CardContent>
                          </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {searchResults.pricing_data && searchResults.pricing_data.length > 0 && (
                <AccordionItem value="pricing_data" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Pricing Data ({searchResults.pricing_data.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.pricing_data.slice(0, 10).map((price: any, idx: number) => {
                        const priceData = price.data || price
                        // For cpp_drug_cost, get drug name from data
                        const drugName = priceData.drug || priceData.Drug || priceData.product_name || price.drug || ''
                        
                        // For cpp_spu, use the country and procedure info from backend
                        const country = price.country || priceData.country || priceData.Country || priceData.market || ''
                        const procedureCode = price.procedure_code || priceData.CPT_CODE || ''
                        const procedureDesc = price.procedure_desc || priceData.LONG_DESC || priceData.SHORT_DESC || priceData.description || ''
                        const spuPrice = price.price || (country && priceData[country] ? priceData[country] : null)
                        
                        const priceTitle = price.type === 'cpp_drug_cost' 
                          ? `Drug Cost: ${drugName || 'Unknown Drug'}` 
                          : price.type === 'cpp_spu' 
                          ? `SPU Pricing: ${country || 'Multiple Countries'}${procedureCode ? ` (${procedureCode})` : ''}` 
                          : 'Pricing Data'
                        const priceId = `${price.type}-${drugName || country || procedureCode || idx}`
                        const isAdded = isEvidenceAdded(price, 'pricing')
                        return (
                          <Card key={idx} className={isAdded ? 'bg-green-50 border-green-200' : ''}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">{priceTitle}</CardTitle>
                              <CardDescription>
                                Source: {price.source || 'cpp_data'}
                                {procedureDesc && price.type === 'cpp_spu' && (
                                  <span className="ml-2">• {procedureDesc}</span>
                                )}
                                {spuPrice && price.type === 'cpp_spu' && (
                                  <span className="ml-2">• ${spuPrice.toLocaleString()}</span>
                                )}
                              </CardDescription>
                            </CardHeader>
                            {!readOnly && (
                              <CardContent className="pt-0">
                                <Button 
                                  size="sm" 
                                  variant={isAdded ? "default" : "outline"}
                                  className="gap-2"
                                  onClick={() => handleAddTrialAsEvidence({
                                    ...price,
                                    title: priceTitle
                                  }, 'pricing')}
                                  disabled={isAdded}
                                >
                                  {isAdded ? (
                                    <>
                                      <Check className="h-4 w-4" />
                                      Added
                                    </>
                                  ) : (
                                    'Add as Evidence'
                                  )}
                                </Button>
                              </CardContent>
                            )}
                          </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {searchResults.product_brands && searchResults.product_brands.length > 0 && (
                <AccordionItem value="product_brands" className="border rounded-lg px-4">
                  <AccordionTrigger className="hover:no-underline">
                    <h4 className="font-medium flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Product Brands ({searchResults.product_brands.length})
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pt-2">
                      {searchResults.product_brands.slice(0, 10).map((product: any, idx: number) => {
                        const productId = product.product_name || `product-${idx}`
                        const isAdded = isEvidenceAdded(product, 'product_brand')
                        return (
                          <Card key={idx} className={isAdded ? 'bg-green-50 border-green-200' : ''}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">{product.product_name || 'Unknown Product'}</CardTitle>
                              <CardDescription>Source: {product.source || 'product_brand_dim'}</CardDescription>
                            </CardHeader>
                            {!readOnly && (
                              <CardContent className="pt-0">
                                <Button 
                                  size="sm" 
                                  variant={isAdded ? "default" : "outline"}
                                  className="gap-2"
                                  onClick={() => handleAddTrialAsEvidence({
                                    title: `${product.product_name} - Product Brand`,
                                    type: 'product_brand',
                                    metadata: product
                                  }, 'product_brand')}
                                  disabled={isAdded}
                                >
                                  {isAdded ? (
                                    <>
                                      <Check className="h-4 w-4" />
                                      Added
                                    </>
                                  ) : (
                                    'Add as Evidence'
                                  )}
                                </Button>
                              </CardContent>
                            )}
                          </Card>
                        )
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
