"use client"

import { Button } from "@/components/ui/button"
import { FileJson, Loader2 } from "lucide-react"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { toast } from "sonner"

export function USDMExportButton() {
  const router = useRouter()
  const {
    studyContext,
    studyDesign,
    objectives,
    endpoints,
    inclusionCriteria,
    exclusionCriteria,
    selectedSites,
    selectedTrials,
    protocolSections,
  } = useStudyDesigner()
  
  const [isExporting, setIsExporting] = useState(false)
  
  const handleExport = async () => {
    try {
      setIsExporting(true)
      
      console.log('📤 Exporting to USDM...')
      console.log('Study Context:', studyContext)
      console.log('Study Design:', studyDesign)
      console.log('Objectives:', objectives)
      console.log('Endpoints:', endpoints)
      
      // Prepare request payload
      const exportRequest = {
        studyContext,
        studyDesign,
        objectives,
        endpoints,
        inclusionCriteria,
        exclusionCriteria,
        selectedSites,
        selectedTrials,
        protocolSections
      }
      
      // Call backend API
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/protocol/export-usdm`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(exportRequest)
        }
      )
      
      if (!response.ok) {
        const errorData = await response.text()
        throw new Error(`Export failed: ${response.statusText}. ${errorData}`)
      }
      
      const data = await response.json()
      
      console.log('✅ USDM export response:', data)
      
      if (data.success && data.usdm) {
        // Store data in sessionStorage for the new page
        sessionStorage.setItem('usdm_export_data', JSON.stringify(data.usdm))
        if (data.validation) {
          sessionStorage.setItem('usdm_export_validation', JSON.stringify(data.validation))
        }
        
        toast.success('USDM export successful!')
        
        // Navigate to USDM export page
        router.push('/usdm-export')
      } else {
        throw new Error(data.message || 'Export failed')
      }
      
    } catch (error) {
      console.error('❌ USDM export error:', error)
      toast.error(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsExporting(false)
    }
  }
  
  return (
    <Button 
      onClick={handleExport}
      disabled={isExporting}
      variant="outline"
      className="gap-2 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border-purple-500/50 hover:border-purple-500"
    >
      {isExporting ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Exporting to USDM...
        </>
      ) : (
        <>
          <FileJson className="h-4 w-4" />
          Export to USDM
        </>
      )}
    </Button>
  )
}








