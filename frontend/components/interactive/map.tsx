import React, { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { cn } from '@/lib/utils'
import { MapPin, Users, Calendar, DollarSign, Star, Filter, Search } from 'lucide-react'

// Dynamically import map components to avoid SSR issues
const MapContainer = dynamic(() => import('react-leaflet').then(mod => mod.MapContainer), { ssr: false })
const TileLayer = dynamic(() => import('react-leaflet').then(mod => mod.TileLayer), { ssr: false })
const Marker = dynamic(() => import('react-leaflet').then(mod => mod.Marker), { ssr: false })
const Popup = dynamic(() => import('react-leaflet').then(mod => mod.Popup), { ssr: false })

export interface Site {
  id: string
  name: string
  location: {
    lat: number
    lng: number
  }
  address: string
  city: string
  country: string
  capacity: number
  experience: number
  rating: number
  costPerPatient: number
  specialties: string[]
  status: 'available' | 'busy' | 'unavailable'
  lastTrial?: string
  nextAvailable?: string
}

interface InteractiveMapProps {
  sites: Site[]
  onSiteSelect?: (site: Site) => void
  selectedSites?: string[]
  className?: string
}

export function InteractiveMap({ sites, onSiteSelect, selectedSites = [], className }: InteractiveMapProps) {
  const [filteredSites, setFilteredSites] = useState<Site[]>(sites)
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState({
    status: 'all',
    specialty: 'all',
    minCapacity: 0,
    maxCost: Infinity
  })

  useEffect(() => {
    let filtered = sites

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(site =>
        site.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        site.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
        site.specialties.some(s => s.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    // Apply status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(site => site.status === filters.status)
    }

    // Apply specialty filter
    if (filters.specialty !== 'all') {
      filtered = filtered.filter(site => site.specialties.includes(filters.specialty))
    }

    // Apply capacity filter
    filtered = filtered.filter(site => site.capacity >= filters.minCapacity)

    // Apply cost filter
    filtered = filtered.filter(site => site.costPerPatient <= filters.maxCost)

    setFilteredSites(filtered)
  }, [sites, searchTerm, filters])

  const getStatusColor = (status: Site['status']) => {
    switch (status) {
      case 'available': return 'text-green-600 bg-green-100'
      case 'busy': return 'text-yellow-600 bg-yellow-100'
      case 'unavailable': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getMarkerColor = (site: Site) => {
    if (selectedSites.includes(site.id)) return 'blue'
    switch (site.status) {
      case 'available': return 'green'
      case 'busy': return 'yellow'
      case 'unavailable': return 'red'
      default: return 'gray'
    }
  }

  const specialties = Array.from(new Set(sites.flatMap(site => site.specialties)))

  return (
    <div className={cn('bg-white rounded-lg border border-gray-200', className)}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Site Selection Map</h3>
          <div className="text-sm text-gray-600">
            {filteredSites.length} of {sites.length} sites
          </div>
        </div>

        {/* Search and Filters */}
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search sites..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <select
              value={filters.status}
              onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="available">Available</option>
              <option value="busy">Busy</option>
              <option value="unavailable">Unavailable</option>
            </select>

            <select
              value={filters.specialty}
              onChange={(e) => setFilters(prev => ({ ...prev, specialty: e.target.value }))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Specialties</option>
              {specialties.map(specialty => (
                <option key={specialty} value={specialty}>{specialty}</option>
              ))}
            </select>

            <input
              type="number"
              placeholder="Min Capacity"
              value={filters.minCapacity || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, minCapacity: parseInt(e.target.value) || 0 }))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />

            <input
              type="number"
              placeholder="Max Cost"
              value={filters.maxCost === Infinity ? '' : filters.maxCost}
              onChange={(e) => setFilters(prev => ({ ...prev, maxCost: parseInt(e.target.value) || Infinity }))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="h-96 relative">
        {typeof window !== 'undefined' && (
          <MapContainer
            center={[39.8283, -98.5795]} // Center of US
            zoom={4}
            className="h-full w-full"
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            {filteredSites.map((site) => (
              <Marker
                key={site.id}
                position={[site.location.lat, site.location.lng]}
                eventHandlers={{
                  click: () => onSiteSelect?.(site)
                }}
              >
                <Popup>
                  <div className="p-2 min-w-[200px]">
                    <h4 className="font-semibold text-gray-900 mb-2">{site.name}</h4>
                    <div className="space-y-1 text-sm text-gray-600">
                      <div className="flex items-center space-x-2">
                        <MapPin className="w-4 h-4" />
                        <span>{site.city}, {site.country}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Users className="w-4 h-4" />
                        <span>Capacity: {site.capacity}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <DollarSign className="w-4 h-4" />
                        <span>${site.costPerPatient.toLocaleString()}/patient</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Star className="w-4 h-4" />
                        <span>Rating: {site.rating}/5</span>
                      </div>
                      <div className="mt-2">
                        <span className={cn('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(site.status))}>
                          {site.status}
                        </span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>

      {/* Site List */}
      <div className="p-4 border-t border-gray-200">
        <h4 className="font-semibold text-gray-900 mb-3">Site Details</h4>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {filteredSites.map((site) => (
            <div
              key={site.id}
              className={cn(
                'p-3 border rounded-lg cursor-pointer transition-colors',
                selectedSites.includes(site.id)
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              )}
              onClick={() => onSiteSelect?.(site)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h5 className="font-medium text-gray-900">{site.name}</h5>
                  <p className="text-sm text-gray-600">{site.city}, {site.country}</p>
                  <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                    <span>Capacity: {site.capacity}</span>
                    <span>${site.costPerPatient.toLocaleString()}/patient</span>
                    <span>Rating: {site.rating}/5</span>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={cn('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(site.status))}>
                    {site.status}
                  </span>
                  {selectedSites.includes(site.id) && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}






















