"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SiteScoringChart } from '@/components/charts/site-scoring-chart'
import { SiteSelectionMap } from './site-selection-map'
import { useAPIPost } from '@/lib/hooks/use-api'
import { useStudyDesigner } from '@/lib/contexts/study-designer-context'
import { Loader2, MapPin, TrendingUp, Users, AlertTriangle, Building2, CheckCircle2, Map as MapIcon, List } from 'lucide-react'
import { toast } from 'sonner'

interface SiteScore {
  id: string
  name: string
  site_name: string
  location: string
  city: string
  state: string
  country: string
  score: number
  component_scores: {
    historical_performance: number
    therapeutic_expertise: number
    enrollment_capacity: number
    site_quality: number
    geographic: number
    patient_population: number
  }
  historical_performance: {
    total_trials: number
    avg_enrollment: number
    completion_rate: number
    avg_enrollment_velocity: number
  }
  estimated_enrollment: number
  risk_level: 'Low' | 'Medium' | 'High'
  recommendation: string
}

interface SiteAnalysisResponse {
  success: boolean
  data: {
    recommendedSites: SiteScore[]
    totalSites: number
    coverage: string
    estimatedEnrollment: number
    averageScore: number
    riskDistribution: {
      Low: number
      Medium: number
      High: number
    }
  }
}

export function EnhancedSiteSelectionTab() {
  const { studyContext, selectedTrials, inclusionCriteria, exclusionCriteria } = useStudyDesigner()
  const [selectedSite, setSelectedSite] = useState<SiteScore | null>(null)
  const [siteCount, setSiteCount] = useState(20)
  const [geographicFilter, setGeographicFilter] = useState({
    countries: '',
    states: '',
  })
  const [selectedSitesFromMap, setSelectedSitesFromMap] = useState<any[]>([])

  const {
    execute: analyzeSites,
    loading,
    data: analysisData,
    error
  } = useAPIPost<SiteAnalysisResponse>('/api/analysis/sites/analyze')

  // Auto-run analysis when study context changes
  useEffect(() => {
    if (studyContext.indication && studyContext.phase) {
      handleAnalyzeSites()
    }
  }, [studyContext.indication, studyContext.phase, studyContext.therapeuticArea])

  const handleAnalyzeSites = async () => {
    try {
      const result = await analyzeSites({
        studyDesign: {
          therapeuticArea: studyContext.therapeuticArea || '',
          indication: studyContext.indication || '',
          phase: studyContext.phase || 'Phase II',
          targetEnrollment: studyContext.patient_count || 300,
          siteCount: siteCount
        },
        criteria: {
          ...(geographicFilter.countries && {
            countries: geographicFilter.countries.split(',').map(c => c.trim())
          }),
          ...(geographicFilter.states && {
            states: geographicFilter.states.split(',').map(s => s.trim())
          })
        }
      })

      if (result && result.success) {
        toast.success(`Found ${result.data.recommendedSites.length} optimal sites`)
      }
    } catch (err: any) {
      // Silently ignore cancelled requests (this happens when context changes while request is in progress)
      if (err?.code === 'REQUEST_CANCELLED' || err?.message?.includes('cancelled')) {
        console.log('Site analysis request cancelled (context changed)')
        return
      }
      
      // Only show error for actual failures
      toast.error('Failed to analyze sites')
      console.error(err)
    }
  }

  const getRiskBadgeVariant = (risk: string) => {
    switch (risk) {
      case 'Low': return 'default'
      case 'Medium': return 'secondary'
      case 'High': return 'destructive'
      default: return 'outline'
    }
  }

  const sites = analysisData?.data?.recommendedSites || []
  const summary = analysisData?.data

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Site Selection Parameters</CardTitle>
          <CardDescription>
            Configure your site selection criteria based on study requirements
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="siteCount">Number of Sites</Label>
              <Input
                id="siteCount"
                type="number"
                value={siteCount}
                onChange={(e) => setSiteCount(parseInt(e.target.value) || 20)}
                min={5}
                max={50}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="countries">Countries (comma-separated)</Label>
              <Input
                id="countries"
                placeholder="e.g., United States, Canada"
                value={geographicFilter.countries}
                onChange={(e) => setGeographicFilter({ ...geographicFilter, countries: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="states">States (comma-separated)</Label>
              <Input
                id="states"
                placeholder="e.g., NY, CA, MA"
                value={geographicFilter.states}
                onChange={(e) => setGeographicFilter({ ...geographicFilter, states: e.target.value })}
              />
            </div>
          </div>

          <Button 
            onClick={handleAnalyzeSites} 
            disabled={loading}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing Sites...
              </>
            ) : (
              <>
                <TrendingUp className="mr-2 h-4 w-4" />
                Analyze Sites
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{summary.totalSites}</div>
              <p className="text-xs text-muted-foreground">Sites Recommended</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{summary.averageScore.toFixed(1)}</div>
              <p className="text-xs text-muted-foreground">Average Score</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{summary.estimatedEnrollment}</div>
              <p className="text-xs text-muted-foreground">Est. Total Enrollment</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{summary.coverage}</div>
              <p className="text-xs text-muted-foreground">Geographic Coverage</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <div className="text-sm">
                  <Badge variant="default" className="mr-1">{summary.riskDistribution.Low}</Badge>
                  <Badge variant="secondary" className="mr-1">{summary.riskDistribution.Medium}</Badge>
                  <Badge variant="destructive">{summary.riskDistribution.High}</Badge>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Risk Distribution (L/M/H)</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="map" className="space-y-4">
        <TabsList>
          <TabsTrigger value="map">
            <MapIcon className="h-4 w-4 mr-2" />
            Map View
          </TabsTrigger>
          {sites.length > 0 && (
            <>
              <TabsTrigger value="list">
                <List className="h-4 w-4 mr-2" />
                Site List
              </TabsTrigger>
              <TabsTrigger value="details">Site Details</TabsTrigger>
              <TabsTrigger value="comparison">Score Comparison</TabsTrigger>
            </>
          )}
        </TabsList>

        {/* Map View - NEW */}
        <TabsContent value="map" className="space-y-4">
          <SiteSelectionMap
            reference_trial_ids={selectedTrials?.map(t => t.nctId || t.id) || []}
            indication={studyContext.indication}
            phase={studyContext.phase}
            therapeutic_area={studyContext.therapeuticArea}
            icd_codes={inclusionCriteria?.flatMap(c => c.icdCodes || []) || []}
            inclusion_criteria={inclusionCriteria?.map(c => c.text || c.criterion) || []}
            exclusion_criteria={exclusionCriteria?.map(c => c.text || c.criterion) || []}
            onSitesSelected={setSelectedSitesFromMap}
          />
        </TabsContent>

        {sites.length > 0 && (
          <>

          {/* Site List */}
          <TabsContent value="list" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sites.map((site) => (
                <Card 
                  key={site.id} 
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => setSelectedSite(site)}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-1">{site.site_name}</h3>
                        <div className="flex items-center text-sm text-muted-foreground mb-2">
                          <MapPin className="h-3 w-3 mr-1" />
                          {site.location}
                        </div>
                      </div>
                      <Badge variant={getRiskBadgeVariant(site.risk_level)}>
                        {site.risk_level} Risk
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <div className="text-2xl font-bold text-primary">
                          {site.score.toFixed(1)}
                        </div>
                        <div className="text-xs text-muted-foreground">Overall Score</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold">
                          {site.estimated_enrollment}
                        </div>
                        <div className="text-xs text-muted-foreground">Est. Enrollment</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="flex items-center gap-1">
                        <Building2 className="h-3 w-3 text-muted-foreground" />
                        <span>{site.historical_performance.total_trials} trials</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Users className="h-3 w-3 text-muted-foreground" />
                        <span>{site.historical_performance.avg_enrollment} avg</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-muted-foreground" />
                        <span>{site.historical_performance.completion_rate}%</span>
                      </div>
                    </div>

                    <div className="mt-4 pt-4 border-t border-border">
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {site.recommendation}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Site Details */}
          <TabsContent value="details">
            {selectedSite ? (
              <SiteScoringChart
                componentScores={selectedSite.component_scores}
                totalScore={selectedSite.score}
                siteName={selectedSite.site_name}
              />
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Select a site from the list to view detailed scoring</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Score Comparison */}
          <TabsContent value="comparison">
            <Card>
              <CardHeader>
                <CardTitle>Site Score Comparison</CardTitle>
                <CardDescription>Compare scores across all recommended sites</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {sites.map((site, index) => (
                    <div key={site.id} className="flex items-center gap-4">
                      <div className="w-8 text-center font-semibold text-muted-foreground">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium">{site.site_name}</span>
                          <span className="text-sm font-semibold">{site.score.toFixed(1)}</span>
                        </div>
                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${site.score}%` }}
                          />
                        </div>
                      </div>
                      <Badge variant={getRiskBadgeVariant(site.risk_level)} className="w-20 justify-center">
                        {site.risk_level}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          </>
        )}
      </Tabs>

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              <p>Error: {error.message}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

