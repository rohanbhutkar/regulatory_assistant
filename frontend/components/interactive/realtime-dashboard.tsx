import React, { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { formatTime } from '@/lib/utils/time'
import { 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  Users, 
  Clock, 
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw
} from 'lucide-react'

export interface RealTimeMetric {
  id: string
  label: string
  value: number
  change: number
  changeType: 'increase' | 'decrease' | 'neutral'
  status: 'success' | 'warning' | 'error' | 'info'
  timestamp: string
  trend?: number[]
}

export interface RealTimeUpdate {
  type: 'metric' | 'alert' | 'status'
  data: any
  timestamp: string
}

interface RealTimeDashboardProps {
  metrics: RealTimeMetric[]
  onRefresh?: () => void
  autoRefresh?: boolean
  refreshInterval?: number
  className?: string
}

export function RealTimeDashboard({ 
  metrics, 
  onRefresh, 
  autoRefresh = true, 
  refreshInterval = 5000,
  className 
}: RealTimeDashboardProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [ws, setWs] = useState<WebSocket | null>(null)

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const websocket = new WebSocket('ws://localhost:8001/ws/dashboard')
        
        websocket.onopen = () => {
          setIsConnected(true)
          console.log('WebSocket connected')
        }
        
        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            handleRealTimeUpdate(data)
            setLastUpdate(new Date())
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }
        
        websocket.onclose = () => {
          setIsConnected(false)
          console.log('WebSocket disconnected')
          // Reconnect after 3 seconds
          setTimeout(connectWebSocket, 3000)
        }
        
        websocket.onerror = (error) => {
          console.error('WebSocket error:', error)
          setIsConnected(false)
        }
        
        setWs(websocket)
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        setIsConnected(false)
      }
    }

    connectWebSocket()

    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [])

  const handleRealTimeUpdate = useCallback((update: RealTimeUpdate) => {
    // Handle different types of real-time updates
    switch (update.type) {
      case 'metric':
        // Update metrics in real-time
        console.log('Metric update:', update.data)
        break
      case 'alert':
        // Show alerts
        console.log('Alert:', update.data)
        break
      case 'status':
        // Update status
        console.log('Status update:', update.data)
        break
    }
  }, [])

  // Auto refresh
  useEffect(() => {
    if (!autoRefresh || !onRefresh) return

    const interval = setInterval(() => {
      onRefresh()
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, onRefresh])

  const getStatusIcon = (status: RealTimeMetric['status']) => {
    switch (status) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'warning': return <AlertCircle className="w-4 h-4 text-yellow-500" />
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />
      case 'info': return <Activity className="w-4 h-4 text-blue-500" />
      default: return <Activity className="w-4 h-4 text-gray-500" />
    }
  }

  const getChangeIcon = (changeType: RealTimeMetric['changeType']) => {
    switch (changeType) {
      case 'increase': return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'decrease': return <TrendingDown className="w-4 h-4 text-red-500" />
      case 'neutral': return <Activity className="w-4 h-4 text-gray-500" />
      default: return <Activity className="w-4 h-4 text-gray-500" />
    }
  }

  const getChangeColor = (changeType: RealTimeMetric['changeType']) => {
    switch (changeType) {
      case 'increase': return 'text-green-600'
      case 'decrease': return 'text-red-600'
      case 'neutral': return 'text-gray-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <div className={cn('bg-white rounded-lg border border-gray-200 p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-semibold text-gray-900">Real-Time Dashboard</h3>
          <div className="flex items-center space-x-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-green-500' : 'bg-red-500'
            )} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="text-sm text-gray-500">
            Last update: {formatTime(lastUpdate)}
          </div>
          <button
            onClick={onRefresh}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric) => (
          <div
            key={metric.id}
            className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                {getStatusIcon(metric.status)}
                <span className="text-sm font-medium text-gray-700">{metric.label}</span>
              </div>
              <div className="flex items-center space-x-1">
                {getChangeIcon(metric.changeType)}
                <span className={cn('text-sm font-medium', getChangeColor(metric.changeType))}>
                  {metric.change > 0 ? '+' : ''}{metric.change}%
                </span>
              </div>
            </div>
            
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {metric.value.toLocaleString()}
            </div>
            
            <div className="text-xs text-gray-500">
              Updated: {formatTime(new Date(metric.timestamp))}
            </div>
            
            {/* Mini trend chart */}
            {metric.trend && metric.trend.length > 0 && (
              <div className="mt-3 h-8 flex items-end space-x-1">
                {metric.trend.slice(-10).map((value, index) => (
                  <div
                    key={index}
                    className="bg-blue-500 rounded-sm flex-1"
                    style={{ 
                      height: `${(value / Math.max(...metric.trend!)) * 100}%`,
                      minHeight: '2px'
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Activity Feed */}
      <div className="mt-6">
        <h4 className="text-md font-semibold text-gray-900 mb-3">Recent Activity</h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {[
            { id: 1, message: 'New trial enrollment: 15 patients', time: '2 min ago', type: 'success' },
            { id: 2, message: 'Site capacity updated: Site A', time: '5 min ago', type: 'info' },
            { id: 3, message: 'Budget alert: Trial B approaching limit', time: '8 min ago', type: 'warning' },
            { id: 4, message: 'Data export completed', time: '12 min ago', type: 'success' },
            { id: 5, message: 'New site added to network', time: '15 min ago', type: 'info' }
          ].map((activity) => (
            <div key={activity.id} className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded">
              <div className="flex-shrink-0">
                {activity.type === 'success' && <CheckCircle className="w-4 h-4 text-green-500" />}
                {activity.type === 'warning' && <AlertCircle className="w-4 h-4 text-yellow-500" />}
                {activity.type === 'info' && <Activity className="w-4 h-4 text-blue-500" />}
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-900">{activity.message}</p>
                <p className="text-xs text-gray-500">{activity.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Live metrics component
interface LiveMetricsProps {
  className?: string
}

export function LiveMetrics({ className }: LiveMetricsProps) {
  const [metrics, setMetrics] = useState<RealTimeMetric[]>([])

  const handleRefresh = async () => {
    // TODO: Implement real-time data fetching from API
    console.log('Refreshing live metrics...')
  }

  return (
    <RealTimeDashboard
      metrics={metrics}
      onRefresh={handleRefresh}
      autoRefresh={true}
      refreshInterval={10000}
      className={className}
    />
  )
}














