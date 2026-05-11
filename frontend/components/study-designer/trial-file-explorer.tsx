import { useState } from 'react'
import { Trial } from '@/lib/types/trial-types'
import { formatDate } from '@/lib/utils/time'

interface TrialFileExplorerProps {
  trials: Trial[]
  onTrialSelect: (trial: Trial) => void
  onCreateTrial: () => void
}

export function TrialFileExplorer({ trials, onTrialSelect, onCreateTrial }: TrialFileExplorerProps) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev?.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const filteredTrials = trials.filter(trial => 
    filterStatus === 'all' || trial.status === filterStatus
  )

  const sortedTrials = [...filteredTrials].sort((a, b) => {
    if (!sortConfig) return 0
    
    const aValue = a[sortConfig.key as keyof Trial]
    const bValue = b[sortConfig.key as keyof Trial]
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortConfig.direction === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }
    
    return 0
  })

  const getStatusBadge = (status: string) => {
    const statusStyles = {
      design: 'bg-blue-100 text-blue-800',
      active: 'bg-green-100 text-green-800',
      paused: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-gray-100 text-gray-800'
    }
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[status as keyof typeof statusStyles]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getActionButtons = (trial: Trial) => (
    <div className="flex space-x-2">
      <button
        onClick={() => onTrialSelect(trial)}
        className="text-blue-600 hover:text-blue-900 text-sm font-medium"
      >
        Open
      </button>
      <button className="text-gray-600 hover:text-gray-900 text-sm font-medium">
        Duplicate
      </button>
      <button className="text-gray-600 hover:text-gray-900 text-sm font-medium">
        Export
      </button>
    </div>
  )

  return (
    <div className="bg-white shadow-sm rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Trial File Explorer</h2>
          <div className="flex items-center space-x-4">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">All Status</option>
              <option value="design">Design</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </select>
            <button
              onClick={onCreateTrial}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              + Start New Design
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('title')}
              >
                Trial Name
                {sortConfig?.key === 'title' && (
                  <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                )}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Therapeutic Area
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Phase
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('last_modified')}
              >
                Recent Activity
                {sortConfig?.key === 'last_modified' && (
                  <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                )}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Modified By
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedTrials.map((trial) => (
              <tr key={trial.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <button
                    onClick={() => onTrialSelect(trial)}
                    className="text-sm font-medium text-blue-600 hover:text-blue-900 hover:underline"
                  >
                    {trial.title}
                  </button>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(trial.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {trial.therapeutic_area}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {trial.phase}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm text-gray-900">{trial.recent_activity}</div>
                    <div className="text-xs text-gray-500">{formatDate(new Date(trial.last_modified))}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {trial.last_modified_by}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {getActionButtons(trial)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {trials.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">📄</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No trials found</h3>
          <p className="text-gray-500">Get started by creating your first trial design.</p>
        </div>
      )}
    </div>
  )
}


import { formatDate } from '@/lib/utils/time'

interface TrialFileExplorerProps {
  trials: Trial[]
  onTrialSelect: (trial: Trial) => void
  onCreateTrial: () => void
}

export function TrialFileExplorer({ trials, onTrialSelect, onCreateTrial }: TrialFileExplorerProps) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev?.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const filteredTrials = trials.filter(trial => 
    filterStatus === 'all' || trial.status === filterStatus
  )

  const sortedTrials = [...filteredTrials].sort((a, b) => {
    if (!sortConfig) return 0
    
    const aValue = a[sortConfig.key as keyof Trial]
    const bValue = b[sortConfig.key as keyof Trial]
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortConfig.direction === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }
    
    return 0
  })

  const getStatusBadge = (status: string) => {
    const statusStyles = {
      design: 'bg-blue-100 text-blue-800',
      active: 'bg-green-100 text-green-800',
      paused: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-gray-100 text-gray-800'
    }
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[status as keyof typeof statusStyles]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getActionButtons = (trial: Trial) => (
    <div className="flex space-x-2">
      <button
        onClick={() => onTrialSelect(trial)}
        className="text-blue-600 hover:text-blue-900 text-sm font-medium"
      >
        Open
      </button>
      <button className="text-gray-600 hover:text-gray-900 text-sm font-medium">
        Duplicate
      </button>
      <button className="text-gray-600 hover:text-gray-900 text-sm font-medium">
        Export
      </button>
    </div>
  )

  return (
    <div className="bg-white shadow-sm rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Trial File Explorer</h2>
          <div className="flex items-center space-x-4">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">All Status</option>
              <option value="design">Design</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </select>
            <button
              onClick={onCreateTrial}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              + Start New Design
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('title')}
              >
                Trial Name
                {sortConfig?.key === 'title' && (
                  <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                )}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Therapeutic Area
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Phase
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('last_modified')}
              >
                Recent Activity
                {sortConfig?.key === 'last_modified' && (
                  <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                )}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Modified By
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedTrials.map((trial) => (
              <tr key={trial.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <button
                    onClick={() => onTrialSelect(trial)}
                    className="text-sm font-medium text-blue-600 hover:text-blue-900 hover:underline"
                  >
                    {trial.title}
                  </button>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(trial.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {trial.therapeutic_area}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {trial.phase}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm text-gray-900">{trial.recent_activity}</div>
                    <div className="text-xs text-gray-500">{formatDate(new Date(trial.last_modified))}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {trial.last_modified_by}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {getActionButtons(trial)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {trials.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">📄</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No trials found</h3>
          <p className="text-gray-500">Get started by creating your first trial design.</p>
        </div>
      )}
    </div>
  )
}











