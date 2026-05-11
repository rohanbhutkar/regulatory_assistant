"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Building2, MapPin, CheckCircle2 } from 'lucide-react'

// CSS to ensure dialog appears above Leaflet map (z-index: 400-1000)
// Leaflet uses z-index up to ~1000, so we use 10000+ to be safe
const dialogStyles = `
  /* Target Radix Portal wrapper */
  [data-radix-portal] {
    z-index: 10000 !important;
  }
  
  /* Target overlay directly */
  [data-radix-dialog-overlay] {
    z-index: 10000 !important;
    background: rgba(0, 0, 0, 0.8) !important;
    backdrop-filter: blur(4px) !important;
  }
  
  /* Target content */
  [data-radix-dialog-content] {
    z-index: 10001 !important;
  }
  
  /* Alternative selectors for when state is open */
  [data-state="open"] {
    z-index: 10000 !important;
  }
`

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
}

interface NearestSitesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sites: SiteLocation[]
  distances: number[]
  clickedLocation: { lat: number; lng: number } | null
  onSelectSite: (site: SiteLocation) => void
  loading: boolean
}

export function NearestSitesDialog({
  open,
  onOpenChange,
  sites,
  distances,
  clickedLocation,
  onSelectSite,
  loading
}: NearestSitesDialogProps) {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: dialogStyles }} />
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-purple-500" />
            Select a Nearby Site
          </DialogTitle>
          <DialogDescription>
            {clickedLocation && (
              <span className="text-xs text-muted-foreground">
                Clicked location: {clickedLocation.lat.toFixed(4)}°, {clickedLocation.lng.toFixed(4)}°
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="py-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-sm text-muted-foreground">Finding nearest sites...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sites.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">
                <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No sites found nearby</p>
              </div>
            ) : (
              <>
                <p className="text-sm text-muted-foreground mb-4">
                  Found {sites.length} real sites from SiteTrove. Click one to add it to your study.
                </p>
                {sites.map((site, index) => (
                  <button
                    key={site.site_id}
                    onClick={() => {
                      onSelectSite(site)
                      onOpenChange(false)
                    }}
                    className="w-full p-4 border rounded-lg hover:bg-secondary/50 transition-all text-left group hover:shadow-md hover:border-primary"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                            {index + 1}
                          </span>
                          <h4 className="font-semibold text-base group-hover:text-primary transition-colors">
                            {site.site_name}
                          </h4>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                          <div className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            <span>{site.city}, {site.state}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Building2 className="h-3 w-3" />
                            <span>{site.historical_trials} trials</span>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            📍 {distances[index]} miles away
                          </Badge>
                          {site.historical_trials > 50 && (
                            <Badge variant="default" className="text-xs bg-green-500">
                              ⭐ High Experience
                            </Badge>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-center">
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                          <CheckCircle2 className="h-8 w-8 text-primary" />
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </>
            )}
          </div>
        )}

        <div className="flex justify-end pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

