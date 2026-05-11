"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { SelectedSite } from "@/lib/types/study-types"
import { Search, Filter, Star, Loader2 } from "lucide-react"
import { InteractiveSiteMap } from "./interactive-site-map"
import { useAnalysisAPI } from "@/lib/hooks/use-analysis-api"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { toast } from "sonner"

interface SiteSelectionTabProps {
  sites?: SelectedSite[]
  onSitesChange?: (sites: SelectedSite[]) => void
  studyDesign?: {
    indication?: string
    phase?: string
    totalParticipants?: number
  }
}

export function SiteSelectionTab({ sites: propsSites, onSitesChange: propsOnChange, studyDesign: propsStudyDesign }: SiteSelectionTabProps = {}) {
  // Use context data with props as fallback
  const {
    selectedSites: contextSites,
    setSelectedSites: setContextSites,
    studyDesign: contextStudyDesign,
    indication,
    phase,
    isLoading: contextLoading
  } = useStudyDesigner()
  
  // Use context data if available, otherwise use props
  const sites = propsSites !== undefined ? propsSites : contextSites
  const studyDesign = propsStudyDesign !== undefined ? propsStudyDesign : contextStudyDesign
  
  const [searchTerm, setSearchTerm] = useState("")
  const [availableSites, setAvailableSites] = useState<SelectedSite[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const { analyzeSites } = useAnalysisAPI()
  
  console.log("🔍 Site Selection Tab:", {
    contextSites: contextSites.length,
    propsSites: propsSites?.length,
    usingContext: propsSites === undefined,
    indication,
    phase,
    studyDesign
  })

  const loadSiteAnalysis = async () => {
    if (!studyDesign) return
    
    setIsAnalyzing(true)
    try {
      const response = await analyzeSites({
        studyDesign,
        criteria: {
          indication: studyDesign.indication || 'Cancer',
          phase: studyDesign.phase || 'Phase II',
          targetEnrollment: studyDesign.totalParticipants || 200
        }
      })
      
      if (response.success && response.data?.recommendedSites) {
        const recommendedSites: SelectedSite[] = response.data.recommendedSites.map((site: {
          id?: string
          name?: string
          site_name?: string
          location?: string
          city?: string
          state?: string
          coordinates?: { lat: number; lng: number }
          score?: number
          historical_performance?: number
          estimated_enrollment?: number
        }) => ({
          id: site.id || `site-${Math.random()}`,
          name: site.name || site.site_name || 'Unknown Site',
          location: site.location || `${site.city || 'Unknown'}, ${site.state || 'Unknown'}`,
          coordinates: site.coordinates || { lat: 40.7128, lng: -74.0060 },
          score: site.score || Math.floor(Math.random() * 20) + 80,
          historicalPerformance: site.historical_performance || Math.floor(Math.random() * 20) + 80,
          estimatedEnrollment: site.estimated_enrollment || Math.floor(Math.random() * 20) + 20
        }))
        
        setAvailableSites(recommendedSites)
        toast.success(`Found ${recommendedSites.length} recommended sites`)
      } else {
        toast.error('Failed to analyze sites')
      }
    } catch (error) {
      console.error('Site analysis error:', error)
      toast.error('Error analyzing sites')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const toggleSite = (site: SelectedSite) => {
    const isSelected = sites.some((s) => s.id === site.id)
    const newSites = isSelected 
      ? sites.filter((s) => s.id !== site.id)
      : [...sites, site]
    
    // Use context or props method
    if (propsOnChange) {
      propsOnChange(newSites)
    } else {
      setContextSites(newSites)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Site Selection</h2>
          <p className="text-muted-foreground">Select optimal sites based on performance and enrollment potential</p>
        </div>
        <div className="flex items-center gap-4">
          <Button 
            onClick={loadSiteAnalysis} 
            disabled={isAnalyzing || !studyDesign}
            className="gap-2"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Analyze Sites'
            )}
          </Button>
          <Badge variant="secondary" className="text-lg px-4 py-2">
            {sites.length} Sites Selected
          </Badge>
        </div>
      </div>

      <InteractiveSiteMap sites={sites} onSiteClick={toggleSite} showPopulationOverlay={true} />

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sites by name or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline" className="gap-2 bg-transparent">
          <Filter className="h-4 w-4" />
          Filters
        </Button>
      </div>

      {/* Sites Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Site Name</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Historical Performance</TableHead>
              <TableHead>Est. Enrollment</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {availableSites.map((site) => {
              const isSelected = sites.some((s) => s.id === site.id)
              return (
                <TableRow key={site.id} className={isSelected ? "bg-primary/5" : ""}>
                  <TableCell className="font-medium">{site.name}</TableCell>
                  <TableCell>{site.location}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                      <span className="font-semibold">{site.score}</span>
                    </div>
                  </TableCell>
                  <TableCell>{site.historicalPerformance}%</TableCell>
                  <TableCell>{site.estimatedEnrollment} patients</TableCell>
                  <TableCell>
                    <Button variant={isSelected ? "secondary" : "outline"} size="sm" onClick={() => toggleSite(site)}>
                      {isSelected ? "Selected" : "Select"}
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
