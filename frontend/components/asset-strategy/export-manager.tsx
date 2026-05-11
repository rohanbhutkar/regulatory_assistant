"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Download, FileText, FileSpreadsheet, File } from 'lucide-react'
import { toast } from 'sonner'

interface ExportManagerProps {
  assetId: string
  assetName: string
  dataType: 'scenarios' | 'financial' | 'pricing' | 'hta' | 'full-report'
  data: any
}

export function ExportManager({ assetId, assetName, dataType, data }: ExportManagerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [exportOptions, setExportOptions] = useState({
    includeCharts: true,
    includeRawData: true,
    includeMetadata: true
  })

  const exportToCSV = () => {
    try {
      let csvContent = ''
      
      if (dataType === 'scenarios' && Array.isArray(data)) {
        // Export scenarios as CSV
        const headers = ['Name', 'List Price', 'Discount %', 'Uptake', 'HTA Outcome', 'NPV', 'Peak Sales']
        csvContent = headers.join(',') + '\n'
        
        data.forEach((scenario: any) => {
          const row = [
            scenario.name || '',
            scenario.parameters?.list_price || '',
            scenario.parameters?.discount_pct || '',
            scenario.parameters?.uptake_archetype || '',
            scenario.parameters?.hta_outcome || '',
            scenario.results?.results?.npv || '',
            scenario.results?.results?.peak_sales || ''
          ]
          csvContent += row.join(',') + '\n'
        })
      } else if (dataType === 'financial' && data) {
        // Export financial data
        const headers = ['Metric', 'Value']
        csvContent = headers.join(',') + '\n'
        
        if (data.patient_funnel) {
          csvContent += `Prevalence,${data.patient_funnel.prevalence || ''}\n`
          csvContent += `Treated Patients,${data.patient_funnel.treated || ''}\n`
        }
        if (data.revenue) {
          csvContent += `Peak Sales,${data.revenue.peak_sales || ''}\n`
          csvContent += `Time to Peak,${data.revenue.time_to_peak_years || ''}\n`
        }
        if (data.npv) {
          csvContent += `NPV,${data.npv.npv || ''}\n`
          csvContent += `rNPV,${data.npv.rnpv || ''}\n`
        }
        if (data.roi) {
          csvContent += `ROI,${data.roi.roi || ''}\n`
        }
      }
      
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${assetName.replace(/\s+/g, '_')}_${dataType}_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
      
      toast.success('CSV exported successfully')
      setIsOpen(false)
    } catch (error) {
      console.error('Export error:', error)
      toast.error('Failed to export CSV')
    }
  }

  const exportToJSON = () => {
    try {
      const jsonContent = JSON.stringify(data, null, 2)
      const blob = new Blob([jsonContent], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${assetName.replace(/\s+/g, '_')}_${dataType}_${new Date().toISOString().split('T')[0]}.json`
      a.click()
      window.URL.revokeObjectURL(url)
      
      toast.success('JSON exported successfully')
      setIsOpen(false)
    } catch (error) {
      console.error('Export error:', error)
      toast.error('Failed to export JSON')
    }
  }

  const exportToExcel = async () => {
    try {
      // For Excel, we'd need a library like xlsx, but for now, export as CSV with .xlsx extension
      // In production, would use backend service to generate proper Excel file
      toast.info('Excel export requires backend service. Use CSV export for now.')
    } catch (error) {
      console.error('Export error:', error)
      toast.error('Failed to export Excel')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Download className="h-4 w-4" />
          Export
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export {dataType.charAt(0).toUpperCase() + dataType.slice(1)} Data</DialogTitle>
          <DialogDescription>Choose export format and options</DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Export Options</Label>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="includeCharts"
                  checked={exportOptions.includeCharts}
                  onCheckedChange={(checked) => setExportOptions({ ...exportOptions, includeCharts: checked as boolean })}
                />
                <Label htmlFor="includeCharts" className="font-normal">Include Charts</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="includeRawData"
                  checked={exportOptions.includeRawData}
                  onCheckedChange={(checked) => setExportOptions({ ...exportOptions, includeRawData: checked as boolean })}
                />
                <Label htmlFor="includeRawData" className="font-normal">Include Raw Data</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="includeMetadata"
                  checked={exportOptions.includeMetadata}
                  onCheckedChange={(checked) => setExportOptions({ ...exportOptions, includeMetadata: checked as boolean })}
                />
                <Label htmlFor="includeMetadata" className="font-normal">Include Metadata</Label>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Button onClick={exportToCSV} variant="outline" className="gap-2">
              <FileSpreadsheet className="h-4 w-4" />
              CSV
            </Button>
            <Button onClick={exportToJSON} variant="outline" className="gap-2">
              <FileText className="h-4 w-4" />
              JSON
            </Button>
            <Button onClick={exportToExcel} variant="outline" className="gap-2">
              <FileSpreadsheet className="h-4 w-4" />
              Excel
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
