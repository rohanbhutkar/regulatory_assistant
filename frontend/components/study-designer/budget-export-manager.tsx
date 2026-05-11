'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Download, FileText, FileSpreadsheet, FileImage } from 'lucide-react'

interface BudgetExportManagerProps {
  budgetData: any
  studyName: string
}

export function BudgetExportManager({ budgetData, studyName }: BudgetExportManagerProps) {
  const [exportOptions, setExportOptions] = useState({
    summary: true,
    patientCosts: true,
    siteCosts: true,
    operationalCosts: true,
    additionalCosts: true,
    drugSupply: true,
    countryBreakdown: true,
    timeline: true,
    opal: true,
    procedures: true
  })

  const toggleOption = (key: keyof typeof exportOptions) => {
    setExportOptions(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const exportToPDF = async () => {
    try {
      // In production, this would call a backend service to generate PDF
      const response = await fetch('http://localhost:8001/api/analysis/budget/export/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          budget_data: budgetData,
          study_name: studyName,
          options: exportOptions
        })
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${studyName.replace(/\s+/g, '_')}_Budget.pdf`
        a.click()
      } else {
        throw new Error('PDF export failed')
      }
    } catch (error) {
      console.error('Error exporting PDF:', error)
      alert('PDF export is currently not available. This feature requires backend implementation.')
    }
  }

  const exportToCSV = () => {
    try {
      // Generate CSV data
      let csvContent = `Study Budget Export - ${studyName}\n\n`

      if (exportOptions.summary && budgetData?.grand_total) {
        csvContent += 'SUMMARY\n'
        csvContent += `Grand Total,${budgetData.grand_total}\n`
        csvContent += `Currency,${budgetData.currency || 'USD'}\n\n`
      }

      if (exportOptions.patientCosts && budgetData?.patient_costs) {
        csvContent += 'PATIENT COSTS\n'
        csvContent += `CPP Base,${budgetData.patient_costs.cpp_base}\n`
        csvContent += `Total Patients,${budgetData.patient_costs.total_patients}\n`
        csvContent += `Total Patient Costs,${budgetData.patient_costs.total}\n\n`
      }

      if (exportOptions.siteCosts && budgetData?.site_costs) {
        csvContent += 'SITE COSTS\n'
        csvContent += `Total Site Costs,${budgetData.site_costs.total}\n`
        if (budgetData.site_costs.breakdown) {
          Object.entries(budgetData.site_costs.breakdown).forEach(([key, value]) => {
            csvContent += `${key},${value}\n`
          })
        }
        csvContent += '\n'
      }

      if (exportOptions.operationalCosts && budgetData?.operational_costs) {
        csvContent += 'OPERATIONAL COSTS\n'
        csvContent += `Total Operational Costs,${budgetData.operational_costs.total}\n`
        if (budgetData.operational_costs.breakdown) {
          Object.entries(budgetData.operational_costs.breakdown).forEach(([key, value]) => {
            csvContent += `${key},${value}\n`
          })
        }
        csvContent += '\n'
      }

      if (exportOptions.countryBreakdown && budgetData?.country_budgets) {
        csvContent += 'COUNTRY BREAKDOWN\n'
        csvContent += 'Country,Patients,Sites,Currency,Total Budget USD\n'
        budgetData.country_budgets.forEach((country: any) => {
          csvContent += `${country.country},${country.patients},${country.sites},${country.currency},${country.total_budget_usd}\n`
        })
        csvContent += '\n'
      }

      // Create download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${studyName.replace(/\s+/g, '_')}_Budget.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error exporting CSV:', error)
      alert('CSV export failed')
    }
  }

  const exportToExcel = async () => {
    try {
      // In production, this would call a backend service to generate Excel
      const response = await fetch('http://localhost:8001/api/analysis/budget/export/excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          budget_data: budgetData,
          study_name: studyName,
          options: exportOptions
        })
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${studyName.replace(/\s+/g, '_')}_Budget.xlsx`
        a.click()
      } else {
        throw new Error('Excel export failed')
      }
    } catch (error) {
      console.error('Error exporting Excel:', error)
      alert('Excel export is currently not available. This feature requires backend implementation.')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="h-5 w-5" />
          Export Budget
        </CardTitle>
        <CardDescription>
          Select sections to include and export format
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Export Options */}
        <div className="space-y-3">
          <div className="font-medium text-sm text-slate-700 mb-2">Include Sections:</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(exportOptions).map(([key, checked]) => (
              <div key={key} className="flex items-center space-x-2">
                <Checkbox
                  id={key}
                  checked={checked}
                  onCheckedChange={() => toggleOption(key as keyof typeof exportOptions)}
                />
                <label
                  htmlFor={key}
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Export Buttons */}
        <div className="space-y-2">
          <div className="font-medium text-sm text-slate-700 mb-2">Export As:</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Button
              onClick={exportToPDF}
              variant="outline"
              className="w-full justify-start gap-2 h-auto py-3"
            >
              <FileText className="h-5 w-5 text-red-600" />
              <div className="text-left">
                <div className="font-medium">PDF Report</div>
                <div className="text-xs text-slate-500">Professional format</div>
              </div>
            </Button>

            <Button
              onClick={exportToCSV}
              variant="outline"
              className="w-full justify-start gap-2 h-auto py-3"
            >
              <FileSpreadsheet className="h-5 w-5 text-green-600" />
              <div className="text-left">
                <div className="font-medium">CSV File</div>
                <div className="text-xs text-slate-500">Simple data export</div>
              </div>
            </Button>

            <Button
              onClick={exportToExcel}
              variant="outline"
              className="w-full justify-start gap-2 h-auto py-3"
            >
              <FileSpreadsheet className="h-5 w-5 text-blue-600" />
              <div className="text-left">
                <div className="font-medium">Excel Workbook</div>
                <div className="text-xs text-slate-500">Multi-sheet format</div>
              </div>
            </Button>
          </div>
        </div>

        {/* Preview Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-sm text-blue-800">
            <strong>Note:</strong> PDF and Excel exports require backend services. CSV export works offline.
          </div>
        </div>
      </CardContent>
    </Card>
  )
}







