"use client"

import { useEffect, useState, useRef, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMapEvents, ZoomControl } from 'react-leaflet'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Building2, Users, MapPin, TrendingUp, Plus, X, CheckCircle2, MousePointer, Eraser, Phone, Building, Calendar, ExternalLink } from 'lucide-react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { API_CONFIG } from '@/lib/config/api'
import { NearestSitesDialog } from './nearest-sites-dialog'

// Fix for default marker icons in Next.js
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'

// Initialize Leaflet icons only on client side
if (typeof window !== 'undefined') {
  const DefaultIcon = L.icon({
    iconUrl: icon.src,
    shadowUrl: iconShadow.src,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
  })
  
  L.Marker.prototype.options.icon = DefaultIcon
}

interface SiteLocation {
  site_id: string
  site_name: string
  organization: string
  city: string
  state: string
  country: string
  latitude: number
  longitude: number
  historical_trials: number
  avg_enrollment: number
  therapeutic_areas: string[]
  recent_trials: any[]
  selected: boolean
  // Organization details
  organization_type?: string
  organization_address?: string
  postal_code?: string
  phones?: string
  faxes?: string
  region?: string
  npi_number?: string
  // Trial metrics
  total_trials: number
  ongoing_trials: number
  planned_trials?: number
  total_matching_trials?: number
  ongoing_matching_trials?: number
  planned_matching_trials?: number
  total_investigators?: number
  last_trial_start_date?: string
  // Specialization
  disease_areas?: string[]
  sponsors?: string[]  // Companies they've worked with
  // Parent organization
  parent_organization_name?: string
  parent_organization_type?: string
  parent_total_trials?: number
  // URLs
  record_url?: string
  supporting_urls?: string
}

interface PopulationHeatmapPoint {
  latitude: number
  longitude: number
  state: string
  city: string | null
  patient_count: number
  percentage: number
  icd_codes: string[]
}

interface SiteMapData {
  sites: SiteLocation[]
  population_heatmap: PopulationHeatmapPoint[]
  total_sites: number
  total_population: number
  coverage_analysis: {
    total_zip_codes: number
    covered_zip_codes: number
    coverage_percentage: number
    total_patients: number
    covered_patients: number
    patient_coverage_percentage: number
    underserved_areas: string[]
  }
}

interface SiteSelectionMapProps {
  reference_trial_ids?: string[]
  indication?: string
  phase?: string
  therapeutic_area?: string
  icd_codes?: string[]
  inclusion_criteria?: string[]
  exclusion_criteria?: string[]
  initialSelectedSiteIds?: Set<string>
  filteredSites?: SiteLocation[]
  onSitesSelected?: (sites: SiteLocation[]) => void
  onMapDataLoaded?: (mapData: SiteMapData) => void
}

// Component to handle map clicks
function MapClickHandler({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (e) => {
      onMapClick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

// Cache for site data to avoid re-fetching
const siteDataCache = new Map<string, SiteMapData>()

export function SiteSelectionMap({
  reference_trial_ids = [],
  indication = '',
  phase = '',
  therapeutic_area = '',
  icd_codes = [],
  inclusion_criteria = [],
  exclusion_criteria = [],
  initialSelectedSiteIds,
  filteredSites,
  onSitesSelected,
  onMapDataLoaded
}: SiteSelectionMapProps) {
  const [mapData, setMapData] = useState<SiteMapData | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedSites, setSelectedSites] = useState<Set<string>>(initialSelectedSiteIds || new Set())
  const [newSiteLocation, setNewSiteLocation] = useState<{ lat: number; lng: number } | null>(null)
  const [showPopulationHeatmap, setShowPopulationHeatmap] = useState(true)
  const [selectedSite, setSelectedSite] = useState<SiteLocation | null>(null)
  const isInitialMount = useRef(true)
  
  // Track the last set of trial IDs we loaded data for
  const lastTrialIdsRef = useRef<string>('')
  
  // Use filtered sites if provided, otherwise use all sites from mapData
  const displaySites = filteredSites || mapData?.sites || []
  
  // New state for mode toggle and nearest sites
  const [mapMode, setMapMode] = useState<'deselected' | 'add' | 'remove'>('deselected')
  const [showNearestDialog, setShowNearestDialog] = useState(false)
  const [nearestSites, setNearestSites] = useState<SiteLocation[]>([])
  const [nearestDistances, setNearestDistances] = useState<number[]>([])
  const [nearestLoading, setNearestLoading] = useState(false)
  const [openPopupSiteId, setOpenPopupSiteId] = useState<string | null>(null)

  useEffect(() => {
    if (indication || therapeutic_area || reference_trial_ids.length > 0) {
      console.log('🔄 Reloading site data for reference trials:', reference_trial_ids)
      loadMapData()
    }
  }, [indication, therapeutic_area, JSON.stringify(reference_trial_ids)])

  // Initialize selected sites from props (only on mount, since initialSelectedSiteIds is stable)
  useEffect(() => {
    if (initialSelectedSiteIds && initialSelectedSiteIds.size > 0) {
      setSelectedSites(initialSelectedSiteIds)
      console.log('🔄 Map: Initialized with selection from props:', initialSelectedSiteIds.size, 'sites')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - only run on mount

  // Notify parent when selected sites change (but skip initial mount if we have saved sites)
  useEffect(() => {
    // Skip calling onSitesSelected on initial mount to preserve saved selection
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }

    if (onSitesSelected && mapData) {
      const selectedSitesList = displaySites.filter(s => selectedSites.has(s.site_id))
      onSitesSelected(selectedSitesList)
      console.log('🔄 Map: Notifying parent of selection change:', selectedSitesList.length, 'sites')
    }
  }, [selectedSites, mapData, onSitesSelected])

  const loadMapData = async () => {
    // Create cache key from sorted trial IDs
    const cacheKey = [...reference_trial_ids].sort().join(',')
    
    // Check if we already have data for these exact trials
    if (cacheKey === lastTrialIdsRef.current && mapData) {
      console.log('✅ Using existing data (trials unchanged)')
      return
    }
    
    // Check cache
    const cachedData = siteDataCache.get(cacheKey)
    if (cachedData) {
      console.log('✅ Loading sites from cache:', {
        trials: reference_trial_ids.length,
        sites: cachedData.sites.length
      })
      setMapData(cachedData)
      lastTrialIdsRef.current = cacheKey
      
      // Notify parent with cached data
      if (onMapDataLoaded) {
        onMapDataLoaded(cachedData)
      }
      return
    }
    
    setLoading(true)
    try {
      // Ensure all arrays are defined (not undefined) to prevent JSON.stringify issues
      // Also convert all trial IDs to strings (backend expects List[str])
      const payload = {
        reference_trial_ids: (reference_trial_ids || []).map(id => String(id)),
        indication: indication || '',
        phase: phase || '',
        therapeutic_area: therapeutic_area || '',
        icd_codes: (icd_codes || []).map(code => String(code)),
        inclusion_criteria: (inclusion_criteria || []).map(c => String(c)),
        exclusion_criteria: (exclusion_criteria || []).map(c => String(c))
      }
      
      console.log('🌐 Fetching sites from backend for trials:', payload)
      
      const response = await fetch(`${API_CONFIG.baseURL}/api/site-map/sites-with-population`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()
        setMapData(data)
        
        // Cache the data
        siteDataCache.set(cacheKey, data)
        lastTrialIdsRef.current = cacheKey
        
        console.log('📍 Map data loaded and cached for trials:', reference_trial_ids, {
          sites: data.sites?.length,
          population_points: data.population_heatmap?.length,
          coverage: data.coverage_analysis?.coverage_percentage,
          cacheKey: cacheKey.substring(0, 50) + '...'
        })
        
        // Notify parent component with the loaded data
        if (onMapDataLoaded) {
          onMapDataLoaded(data)
        }
      } else {
        // Log detailed error for debugging
        const errorText = await response.text()
        console.error('Failed to load map data:', response.status, response.statusText)
        console.error('Error details:', errorText)
        console.error('Request payload was:', {
          reference_trial_ids,
          indication,
          phase,
          therapeutic_area,
          icd_codes,
          inclusion_criteria,
          exclusion_criteria
        })
      }
    } catch (error) {
      console.error('Error loading map data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMapClick = async (lat: number, lng: number) => {
    // Close any open popup when clicking on map
    setOpenPopupSiteId(null)
    
    if (mapMode === 'add') {
      // Find nearest real sites from SiteTrove
      setNewSiteLocation({ lat, lng })
      setShowNearestDialog(true)
      setNearestLoading(true)
      
      try {
        const response = await fetch(`${API_CONFIG.baseURL}/api/site-map/find-nearest-sites`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            latitude: lat,
            longitude: lng,
            max_results: 5,
            therapeutic_area: therapeutic_area || indication
          })
        })
        
        if (response.ok) {
          const data = await response.json()
          setNearestSites(data.sites)
          setNearestDistances(data.distances_miles)
          console.log('✅ Found nearest sites:', data.sites.length)
        } else {
          console.error('Failed to find nearest sites:', response.status)
          setNearestSites([])
          setNearestDistances([])
        }
      } catch (error) {
        console.error('Error finding nearest sites:', error)
        setNearestSites([])
        setNearestDistances([])
      } finally {
        setNearestLoading(false)
      }
    }
    // Remove mode is handled by clicking on markers directly
    // Deselected mode does nothing on map click
  }

  const handleSelectNearestSite = (site: SiteLocation) => {
    // Add the selected site to the map
    setMapData(prev => {
      if (!prev) return null
      
      // Check if site already exists
      const exists = prev.sites.some(s => s.site_id === site.site_id)
      if (exists) {
        console.log('Site already on map')
        return prev
      }
      
      return {
        ...prev,
        sites: [...prev.sites, { ...site, selected: true }],
        total_sites: prev.total_sites + 1
      }
    })

    // Automatically select the site (parent will be notified via useEffect)
    setSelectedSites(prev => new Set([...prev, site.site_id]))
    
    console.log(`✅ Added site: ${site.site_name}`)
  }

  const toggleSiteSelection = (site: SiteLocation) => {
    if (mapMode === 'deselected') {
      // In deselected mode, do nothing - user needs to select a mode first
      return
    }
    
    if (mapMode === 'remove') {
      // In remove mode, remove the site from the map
      setMapData(prev => {
        if (!prev) return null
        return {
          ...prev,
          sites: prev.sites.filter(s => s.site_id !== site.site_id),
          total_sites: prev.total_sites - 1
        }
      })
      
      // Also remove from selected sites (parent will be notified via useEffect)
      setSelectedSites(prev => {
        const newSet = new Set(prev)
        newSet.delete(site.site_id)
        return newSet
      })
      
      console.log(`🗑️ Removed site: ${site.site_name}`)
    } else if (mapMode === 'add') {
      // In add mode, toggle selection (parent will be notified via useEffect)
      setSelectedSites(prev => {
        const newSet = new Set(prev)
        if (newSet.has(site.site_id)) {
          newSet.delete(site.site_id)
        } else {
          newSet.add(site.site_id)
        }
        return newSet
      })
    }
  }

  const getPopulationCircleColor = (percentage: number): string => {
    if (percentage > 10) return '#ef4444' // red
    if (percentage > 5) return '#f59e0b'  // orange
    if (percentage > 2) return '#eab308'  // yellow
    return '#22c55e' // green
  }

  const getPopulationCircleRadius = (patient_count: number): number => {
    // Scale radius based on patient count (logarithmic scale)
    // For ZIP-level data, patient counts are typically 10-1000 per ZIP
    // Radius in meters on the map
    const minRadius = 5000   // 5km minimum
    const maxRadius = 50000  // 50km maximum
    const scaleFactor = 8000
    
    const radius = Math.log(patient_count + 1) * scaleFactor
    return Math.max(minRadius, Math.min(maxRadius, radius))
  }

  // Custom marker icons
  const selectedSiteIcon = new L.Icon({
    iconUrl: 'data:image/svg+xml;base64,' + btoa(`
      <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3" fill="#22c55e"/>
      </svg>
    `),
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
  })

  const unselectedSiteIcon = new L.Icon({
    iconUrl: 'data:image/svg+xml;base64,' + btoa(`
      <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3" fill="#3b82f6"/>
      </svg>
    `),
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-secondary/20 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading site and population data...</p>
        </div>
      </div>
    )
  }

  if (!mapData) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-secondary/20 rounded-lg">
        <div className="text-center">
          <MapPin className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Select reference trials or set indication to view site map</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Sites</p>
                <p className="text-2xl font-bold">{displaySites.length}</p>
                {filteredSites && filteredSites.length < (mapData?.total_sites || 0) && (
                  <p className="text-xs text-muted-foreground mt-1">
                    ({mapData?.total_sites} total, filtered)
                  </p>
                )}
              </div>
              <Building2 className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Selected Sites</p>
                <p className="text-2xl font-bold text-green-600">{selectedSites.size}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Patient Population</p>
                <p className="text-2xl font-bold">{mapData.total_population.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground mt-1">{mapData.coverage_analysis.total_zip_codes} ZIP codes</p>
              </div>
              <Users className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">ZIP Coverage</p>
                <p className="text-2xl font-bold">{mapData.coverage_analysis.coverage_percentage}%</p>
                <p className="text-xs text-muted-foreground mt-1">{mapData.coverage_analysis.covered_zip_codes}/{mapData.coverage_analysis.total_zip_codes} ZIPs</p>
              </div>
              <MapPin className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Patient Coverage</p>
                <p className="text-2xl font-bold">{mapData.coverage_analysis.patient_coverage_percentage}%</p>
                <p className="text-xs text-muted-foreground mt-1">{mapData.coverage_analysis.covered_patients.toLocaleString()} patients</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Map Controls */}
      <div className="flex gap-2 items-center flex-wrap">
        {/* Mode Toggle */}
        <div className="flex gap-1 p-1 bg-secondary/50 rounded-lg border border-border">
          <Button
            variant={mapMode === 'deselected' ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setMapMode('deselected')}
            className="gap-2 transition-all"
          >
            <MousePointer className="h-4 w-4" />
            View Only
          </Button>
          <Button
            variant={mapMode === 'add' ? "default" : "ghost"}
            size="sm"
            onClick={() => setMapMode('add')}
            className="gap-2 transition-all"
          >
            <Plus className="h-4 w-4" />
            Add Sites
          </Button>
          <Button
            variant={mapMode === 'remove' ? "destructive" : "ghost"}
            size="sm"
            onClick={() => setMapMode('remove')}
            className="gap-2 transition-all"
          >
            <Eraser className="h-4 w-4" />
            Remove Sites
          </Button>
        </div>

        <div className="h-6 w-px bg-border" />

        <Button
          variant={showPopulationHeatmap ? "default" : "outline"}
          size="sm"
          onClick={() => setShowPopulationHeatmap(!showPopulationHeatmap)}
        >
          <Users className="h-4 w-4 mr-2" />
          {showPopulationHeatmap ? 'Hide' : 'Show'} Population
        </Button>

        {selectedSites.size > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedSites(new Set())}
          >
            <X className="h-4 w-4 mr-2" />
            Clear Selection ({selectedSites.size})
          </Button>
        )}

        <div className="ml-auto text-sm text-muted-foreground">
          {mapMode === 'deselected' ? (
            <>👁️ View mode - click a site to see details</>
          ) : mapMode === 'add' ? (
            <>💡 Click anywhere to find nearest sites or click sites to select</>
          ) : (
            <>🗑️ Click on a site to remove it</>
          )}
        </div>
      </div>

      {/* Map */}
      <Card>
        <CardContent className="p-0">
          <MapContainer
            center={[39.8283, -98.5795]} // Center of USA
            zoom={4}
            style={{ height: '600px', width: '100%' }}
            zoomControl={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <ZoomControl position="topright" />

            <MapClickHandler onMapClick={handleMapClick} />

            {/* Population Heatmap (Circles) */}
            {showPopulationHeatmap && mapData.population_heatmap.map((point, idx) => (
              <Circle
                key={`pop-${idx}`}
                center={[point.latitude, point.longitude]}
                radius={getPopulationCircleRadius(point.patient_count)}
                pathOptions={{
                  color: getPopulationCircleColor(point.percentage),
                  fillColor: getPopulationCircleColor(point.percentage),
                  fillOpacity: 0.2,
                  weight: 2
                }}
              >
                <Popup>
                  <div className="p-2">
                    <div className="font-semibold text-lg mb-2">
                      {point.city ? `${point.city}, ${point.state}` : point.state}
                    </div>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Patients:</span>
                        <span className="font-medium">{point.patient_count.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Percentage:</span>
                        <span className="font-medium">{point.percentage.toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Location:</span>
                        <span className="font-medium text-xs">{point.latitude.toFixed(2)}°, {point.longitude.toFixed(2)}°</span>
                      </div>
                      {point.icd_codes.length > 0 && (
                        <div className="mt-2 pt-2 border-t">
                          <span className="text-muted-foreground text-xs">ICD Codes:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {point.icd_codes.map(code => (
                              <Badge key={code} variant="outline" className="text-xs">{code}</Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </Popup>
              </Circle>
            ))}

            {/* Site Markers */}
            {displaySites.map((site) => (
              <Marker
                key={site.site_id}
                position={[site.latitude, site.longitude]}
                icon={selectedSites.has(site.site_id) ? selectedSiteIcon : unselectedSiteIcon}
                eventHandlers={{
                  click: (e) => {
                    e.originalEvent?.stopPropagation()
                    // Open this popup
                    setOpenPopupSiteId(site.site_id)
                    // Don't toggle selection, just open popup - let the button in popup handle selection
                    if (mapMode !== 'deselected') {
                      // In interactive modes, we still toggle on marker click for convenience
                    toggleSiteSelection(site)
                    }
                    setSelectedSite(site)
                  }
                }}
              >
                <Popup 
                  maxWidth={500} 
                  minWidth={400} 
                  closeButton={true}
                  autoClose={false}
                  closeOnClick={false}
                  eventHandlers={{
                    remove: () => setOpenPopupSiteId(null)
                  }}
                >
                  <div className="p-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="flex-1">
                        <div className="font-semibold text-lg leading-tight">{site.site_name}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {site.organization_type && <span>{site.organization_type} • </span>}
                          {site.region}
                        </div>
                      </div>
                      {mapMode !== 'deselected' && (
                      <Button
                        size="sm"
                        variant={selectedSites.has(site.site_id) ? "default" : "outline"}
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleSiteSelection(site)
                          }}
                          className="shrink-0"
                      >
                        {selectedSites.has(site.site_id) ? (
                          <>
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Selected
                          </>
                        ) : (
                          <>
                            <Plus className="h-3 w-3 mr-1" />
                            Select
                          </>
                        )}
                      </Button>
                      )}
                    </div>
                    
                    <Tabs defaultValue="overview" className="w-full" onClick={(e) => e.stopPropagation()}>
                      <TabsList className="grid w-full grid-cols-4" onClick={(e) => e.stopPropagation()}>
                        <TabsTrigger value="overview" className="text-xs" onClick={(e) => e.stopPropagation()}>Overview</TabsTrigger>
                        <TabsTrigger value="trials" className="text-xs" onClick={(e) => e.stopPropagation()}>Trials</TabsTrigger>
                        <TabsTrigger value="partners" className="text-xs" onClick={(e) => e.stopPropagation()}>Partners</TabsTrigger>
                        <TabsTrigger value="contact" className="text-xs" onClick={(e) => e.stopPropagation()}>Contact</TabsTrigger>
                      </TabsList>

                      {/* Overview Tab */}
                      <TabsContent value="overview" className="space-y-3 mt-3">
                        {/* Location */}
                        <div className="flex items-start gap-2 text-sm">
                          <MapPin className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
                          <div className="flex-1">
                            <div className="font-medium">{site.city}, {site.state}</div>
                            {site.organization_address && (
                              <div className="text-xs text-muted-foreground">{site.organization_address}</div>
                            )}
                            <div className="text-xs text-muted-foreground mt-1">
                              {site.country} {site.postal_code && `• ${site.postal_code}`}
                            </div>
                          </div>
                      </div>
                      
                        {/* Quick Metrics */}
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-blue-50 dark:bg-blue-950/20 p-2 rounded">
                            <p className="text-xs text-muted-foreground">Total Trials</p>
                            <p className="text-lg font-bold text-blue-600 dark:text-blue-400">
                              {site.total_trials}
                            </p>
                          </div>
                          <div className="bg-green-50 dark:bg-green-950/20 p-2 rounded">
                            <p className="text-xs text-muted-foreground">Investigators</p>
                            <p className="text-lg font-bold text-green-600 dark:text-green-400">
                              {site.total_investigators || 0}
                            </p>
                          </div>
                        </div>

                        {/* Disease Areas */}
                        {site.disease_areas && site.disease_areas.length > 0 && (
                        <div>
                            <p className="text-xs text-muted-foreground mb-1 font-medium">Specializations:</p>
                            <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                              {site.disease_areas.slice(0, 8).map((da, idx) => (
                                <Badge key={idx} variant="secondary" className="text-xs">
                                  {da}
                                </Badge>
                              ))}
                              {site.disease_areas.length > 8 && (
                                <Badge variant="outline" className="text-xs">
                                  +{site.disease_areas.length - 8}
                                </Badge>
                              )}
                        </div>
                          </div>
                        )}
                      </TabsContent>

                      {/* Trials Tab */}
                      <TabsContent value="trials" className="space-y-3 mt-3">
                        <div className="grid grid-cols-3 gap-2 text-center">
                          <div className="bg-primary/10 p-2 rounded">
                            <p className="text-2xl font-bold text-primary">{site.ongoing_trials || 0}</p>
                            <p className="text-xs text-muted-foreground">Ongoing</p>
                          </div>
                          <div className="bg-blue-500/10 p-2 rounded">
                            <p className="text-2xl font-bold text-blue-600">{site.planned_trials || 0}</p>
                            <p className="text-xs text-muted-foreground">Planned</p>
                          </div>
                          <div className="bg-purple-500/10 p-2 rounded">
                            <p className="text-2xl font-bold text-purple-600">{site.total_trials}</p>
                            <p className="text-xs text-muted-foreground">Total</p>
                          </div>
                        </div>

                        {site.last_trial_start_date && (
                          <div className="flex items-center gap-2 text-sm p-2 bg-secondary/30 rounded">
                            <Calendar className="h-4 w-4 text-primary" />
                        <div>
                              <p className="text-xs text-muted-foreground">Last Trial Started</p>
                              <p className="font-medium">{new Date(site.last_trial_start_date).toLocaleDateString()}</p>
                        </div>
                      </div>
                        )}

                        {site.ongoing_matching_trials !== undefined && (
                          <div className="text-sm">
                            <p className="text-xs text-muted-foreground mb-1">Matching Trials:</p>
                            <div className="space-y-1">
                              <div className="flex justify-between">
                                <span>Total Matching:</span>
                                <Badge variant="secondary">{site.total_matching_trials || 0}</Badge>
                              </div>
                              <div className="flex justify-between">
                                <span>Ongoing Matching:</span>
                                <Badge>{site.ongoing_matching_trials || 0}</Badge>
                              </div>
                            </div>
                          </div>
                        )}
                      </TabsContent>

                      {/* Partners Tab */}
                      <TabsContent value="partners" className="space-y-3 mt-3">
                        {site.sponsors && site.sponsors.length > 0 ? (
                          <div>
                            <p className="text-sm font-medium mb-2 flex items-center gap-2">
                              <Building className="h-4 w-4 text-primary" />
                              Companies Worked With ({site.sponsors.length})
                            </p>
                            <div className="space-y-1 max-h-48 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                              {site.sponsors.map((sponsor, idx) => (
                                <div key={idx} className="text-xs bg-primary/5 p-2 rounded border border-primary/10">
                                  {sponsor}
                                </div>
                            ))}
                          </div>
                        </div>
                        ) : (
                          <div className="text-center text-muted-foreground text-sm py-4">
                            No partner information available
                          </div>
                        )}

                        {/* Parent Organization */}
                        {site.parent_organization_name && (
                          <div className="pt-3 border-t">
                            <p className="text-xs text-muted-foreground mb-1">Part of:</p>
                            <div className="text-sm font-medium">{site.parent_organization_name}</div>
                            {site.parent_organization_type && (
                              <div className="text-xs text-muted-foreground">{site.parent_organization_type}</div>
                            )}
                            {site.parent_total_trials > 0 && (
                              <Badge variant="outline" className="mt-1 text-xs">
                                {site.parent_total_trials} trials
                              </Badge>
                      )}
                    </div>
                        )}
                      </TabsContent>

                      {/* Contact Tab */}
                      <TabsContent value="contact" className="space-y-3 mt-3">
                        {site.phones && (
                          <div className="flex items-start gap-2 text-sm">
                            <Phone className="h-4 w-4 mt-0.5 text-primary" />
                            <div>
                              <p className="text-xs text-muted-foreground">Phone</p>
                              <p className="font-medium">{site.phones}</p>
                            </div>
                          </div>
                        )}

                        {site.faxes && (
                          <div className="text-sm">
                            <p className="text-xs text-muted-foreground">Fax</p>
                            <p className="font-medium">{site.faxes}</p>
                          </div>
                        )}

                        {site.npi_number && (
                          <div className="text-sm">
                            <p className="text-xs text-muted-foreground">NPI Number</p>
                            <p className="font-mono text-xs">{site.npi_number}</p>
                          </div>
                        )}

                        {/* Links */}
                        <div className="space-y-2 pt-2 border-t">
                          {site.record_url && (
                            <a
                              href={site.record_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2 text-xs text-primary hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="h-3 w-3" />
                              View Full Record
                            </a>
                          )}
                          {site.supporting_urls && (
                            <a
                              href={site.supporting_urls}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2 text-xs text-primary hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="h-3 w-3" />
                              Additional Information
                            </a>
                          )}
                        </div>

                        {(!site.phones && !site.faxes && !site.npi_number && !site.record_url) && (
                          <div className="text-center text-muted-foreground text-sm py-4">
                            No contact information available
                          </div>
                        )}
                      </TabsContent>
                    </Tabs>

                    {/* Site Status Footer */}
                    {selectedSites.has(site.site_id) && (
                      <div className="mt-3 pt-3 border-t">
                        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm">
                          <CheckCircle2 className="h-4 w-4" />
                          <span className="font-medium">Selected for Trial</span>
                        </div>
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}

          </MapContainer>
        </CardContent>
      </Card>

      {/* Underserved Areas Alert */}
      {mapData.coverage_analysis.underserved_areas.length > 0 && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-orange-500" />
              Underserved Areas
            </CardTitle>
            <CardDescription>
              ZIP codes with patients but no sites within 50 miles
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {mapData.coverage_analysis.underserved_areas.map((area, idx) => (
                <div key={idx} className="text-sm text-muted-foreground border-l-2 border-orange-300 pl-2">
                  {area}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Nearest Sites Dialog */}
      <NearestSitesDialog
        open={showNearestDialog}
        onOpenChange={setShowNearestDialog}
        sites={nearestSites}
        distances={nearestDistances}
        clickedLocation={newSiteLocation}
        onSelectSite={handleSelectNearestSite}
        loading={nearestLoading}
      />
    </div>
  )
}

