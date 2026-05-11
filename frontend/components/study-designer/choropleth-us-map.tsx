"use client"

import React, { useMemo, useState, useCallback } from 'react'
import { ComposableMap, Geographies, Geography, ZoomableGroup } from 'react-simple-maps'
import { scaleQuantize } from 'd3-scale'
import { Card, CardContent } from '@/components/ui/card'
import type { SiteLocation } from '@/lib/types/site-filter-types'

const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json"

// Color scale: light to dark blue based on site density
const colorScale = scaleQuantize<string>()
  .domain([0, 100])
  .range([
    "rgb(233, 237, 240)",  // Lightest
    "rgb(207, 216, 220)",
    "rgb(181, 196, 201)",
    "rgb(156, 175, 183)",
    "rgb(130, 154, 165)",
    "rgb(104, 133, 147)",
    "rgb(78, 112, 129)",
    "rgb(52, 91, 111)",
    "rgb(26, 70, 93)",
    "rgb(0, 49, 75)"       // Darkest
  ])

interface ChoroplethUSMapProps {
  sites: SiteLocation[]
  selectedSiteIds?: Set<string>
  onStateClick?: (stateName: string) => void
  onStateHover?: (stateName: string | null) => void
  height?: string
  showLegend?: boolean
}

export function ChoroplethUSMap({
  sites,
  selectedSiteIds = new Set(),
  onStateClick,
  onStateHover,
  height = "600px",
  showLegend = true
}: ChoroplethUSMapProps) {
  const [position, setPosition] = useState({ coordinates: [-96, 37.5] as [number, number], zoom: 1 })
  const [tooltipContent, setTooltipContent] = useState("")
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [hoveredState, setHoveredState] = useState<string | null>(null)

  // Calculate sites per state
  const sitesByState = useMemo(() => {
    const stateMap = new Map<string, SiteLocation[]>()
    
    sites.forEach(site => {
      if (!site.state) return
      
      const existing = stateMap.get(site.state) || []
      stateMap.set(site.state, [...existing, site])
    })
    
    return stateMap
  }, [sites])

  // Get site count for state
  const getSiteCount = useCallback((stateName: string) => {
    const sites = sitesByState.get(stateName) || []
    return sites.length
  }, [sitesByState])

  // Check if state has selected sites
  const hasSelectedSites = useCallback((stateName: string) => {
    const sites = sitesByState.get(stateName) || []
    return sites.some(site => selectedSiteIds.has(site.site_id))
  }, [sitesByState, selectedSiteIds])

  // Handle state hover
  const handleStateEnter = useCallback((geo: any, e: React.MouseEvent) => {
    const stateName = geo.properties.name
    const stateSites = sitesByState.get(stateName) || []
    const totalTrials = stateSites.reduce((sum, site) => sum + (site.historical_trials || 0), 0)
    const avgEnrollment = stateSites.length > 0
      ? stateSites.reduce((sum, site) => sum + (site.avg_enrollment || 0), 0) / stateSites.length
      : 0

    setTooltipContent(`
      <div style="padding: 8px;">
        <strong style="font-size: 14px;">${stateName}</strong><br/>
        <span style="font-size: 12px;">Sites: ${stateSites.length}</span><br/>
        <span style="font-size: 12px;">Total Trials: ${totalTrials}</span><br/>
        <span style="font-size: 12px;">Avg Enrollment: ${avgEnrollment.toFixed(1)}</span>
      </div>
    `)
    setTooltipPosition({ x: e.clientX, y: e.clientY })
    setHoveredState(stateName)
    onStateHover?.(stateName)
  }, [sitesByState, onStateHover])

  const handleStateLeave = useCallback(() => {
    setTooltipContent("")
    setHoveredState(null)
    onStateHover?.(null)
  }, [onStateHover])

  const handleStateClickInternal = useCallback((geo: any) => {
    const stateName = geo.properties.name
    onStateClick?.(stateName)
  }, [onStateClick])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (tooltipContent) {
      setTooltipPosition({ x: e.clientX, y: e.clientY })
    }
  }, [tooltipContent])

  const handleMoveEnd = useCallback((position: { coordinates: [number, number], zoom: number }) => {
    setPosition(position)
  }, [])

  const handleZoomIn = useCallback(() => {
    setPosition(pos => ({ ...pos, zoom: pos.zoom * 1.5 }))
  }, [])

  const handleZoomOut = useCallback(() => {
    setPosition(pos => ({ ...pos, zoom: pos.zoom / 1.5 }))
  }, [])

  const handleResetZoom = useCallback(() => {
    setPosition({ coordinates: [-96, 37.5], zoom: 1 })
  }, [])

  return (
    <div className="relative w-full" style={{ height }} onMouseMove={handleMouseMove}>
      <ComposableMap
        projection="geoAlbersUsa"
        projectionConfig={{
          scale: 1000
        }}
        style={{
          width: '100%',
          height: '100%'
        }}
      >
        <ZoomableGroup
          zoom={position.zoom}
          center={position.coordinates}
          onMoveEnd={handleMoveEnd}
        >
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const stateName = geo.properties.name
                const siteCount = getSiteCount(stateName)
                const isHovered = hoveredState === stateName
                const isSelected = hasSelectedSites(stateName)

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={colorScale(siteCount)}
                    stroke="#FFF"
                    strokeWidth={0.5}
                    style={{
                      default: {
                        outline: 'none',
                        stroke: isSelected ? '#22c55e' : '#FFF',
                        strokeWidth: isSelected ? 2 : 0.5,
                        transition: 'all 250ms'
                      },
                      hover: {
                        outline: 'none',
                        stroke: '#3b82f6',
                        strokeWidth: 2,
                        cursor: 'pointer',
                        filter: 'brightness(1.1)'
                      },
                      pressed: {
                        outline: 'none',
                        stroke: '#22c55e',
                        strokeWidth: 2
                      }
                    }}
                    onMouseEnter={(e: any) => handleStateEnter(geo, e)}
                    onMouseLeave={handleStateLeave}
                    onClick={() => handleStateClickInternal(geo)}
                  />
                )
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {/* Tooltip */}
      {tooltipContent && (
        <div
          className="absolute pointer-events-none z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          style={{
            top: tooltipPosition.y + 10,
            left: tooltipPosition.x + 10,
          }}
          dangerouslySetInnerHTML={{ __html: tooltipContent }}
        />
      )}

      {/* Zoom Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 z-40">
        <button
          onClick={handleZoomIn}
          className="w-10 h-10 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-center font-semibold text-lg"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          className="w-10 h-10 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-center font-semibold text-lg"
          title="Zoom out"
        >
          −
        </button>
        <button
          onClick={handleResetZoom}
          className="w-10 h-10 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-center text-xs"
          title="Reset zoom"
        >
          ⟲
        </button>
      </div>

      {/* Legend */}
      {showLegend && (
        <Card className="absolute bottom-4 left-4 z-40">
          <CardContent className="p-4">
            <div className="text-sm font-semibold mb-2">Site Density</div>
            <div className="flex items-center gap-1">
              {colorScale.range().map((color, i) => (
                <div key={i} className="flex flex-col items-center">
                  <div
                    className="w-6 h-6 border border-gray-300"
                    style={{ backgroundColor: color }}
                  />
                  {i === 0 && <span className="text-xs mt-1">0</span>}
                  {i === colorScale.range().length - 1 && (
                    <span className="text-xs mt-1">100+</span>
                  )}
                </div>
              ))}
            </div>
            <div className="text-xs text-muted-foreground mt-2">
              Click state to select all sites
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}








