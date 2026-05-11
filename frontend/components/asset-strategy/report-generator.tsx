"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { FileText, Download, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

interface ReportGeneratorProps {
  assetId: string
  assetName: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

const REPORT_TEMPLATES = [
  { value: 'early_opportunity_assessment', label: 'Early Opportunity Assessment' },
  { value: 'pricing_benchmark_handout', label: 'Pricing Benchmark Handout' },
  { value: 'hta_access_outlook', label: 'HTA Access Outlook' },
  { value: 'scenario_sensitivity_pack', label: 'Scenario Sensitivity Pack' },
  { value: 'executive_onepager', label: 'Executive One-Pager' }
]

export function ReportGenerator({ assetId, assetName }: ReportGeneratorProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedReport, setGeneratedReport] = useState<any>(null)

  const generateReport = async () => {
    if (!selectedTemplate) {
      toast.error('Please select a report template')
      return
    }

    setIsGenerating(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/asset-strategy/reports/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_name: selectedTemplate,
          asset_id: assetId,
          markets: ['US']
        })
      })

      if (response.ok) {
        const data = await response.json()
        setGeneratedReport(data)
        toast.success('Report generated successfully')
      } else {
        toast.error('Failed to generate report')
      }
    } catch (error) {
      console.error('Failed to generate report:', error)
      toast.error('Failed to generate report')
    } finally {
      setIsGenerating(false)
    }
  }

  const exportReport = async (format: 'pdf' | 'ppt' | 'excel') => {
    if (!generatedReport) {
      toast.error('No report to export. Generate a report first.')
      return
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/asset-strategy/reports/${generatedReport.id}/export?format=${format}`,
        { method: 'POST' }
      )

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${assetName.replace(/\s+/g, '_')}_${selectedTemplate}_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : format}`
        a.click()
        window.URL.revokeObjectURL(url)
        toast.success(`${format.toUpperCase()} exported successfully`)
      } else {
        toast.error(`Failed to export ${format.toUpperCase()}`)
      }
    } catch (error) {
      console.error(`Failed to export ${format}:`, error)
      toast.error(`Failed to export ${format.toUpperCase()}`)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Report Generation</CardTitle>
        <CardDescription>Generate and export professional reports</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">Report Template</label>
          <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
            <SelectTrigger>
              <SelectValue placeholder="Select a template" />
            </SelectTrigger>
            <SelectContent>
              {REPORT_TEMPLATES.map((template) => (
                <SelectItem key={template.value} value={template.value}>
                  {template.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          onClick={generateReport}
          disabled={!selectedTemplate || isGenerating}
          className="w-full gap-2"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <FileText className="h-4 w-4" />
              Generate Report
            </>
          )}
        </Button>

        {generatedReport && (
          <div className="space-y-2 pt-4 border-t">
            <p className="text-sm text-muted-foreground">Export as:</p>
            <div className="grid grid-cols-3 gap-2">
              <Button
                onClick={() => exportReport('pdf')}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Download className="h-3 w-3" />
                PDF
              </Button>
              <Button
                onClick={() => exportReport('ppt')}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Download className="h-3 w-3" />
                PPT
              </Button>
              <Button
                onClick={() => exportReport('excel')}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Download className="h-3 w-3" />
                Excel
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Report ID: {generatedReport.id}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
