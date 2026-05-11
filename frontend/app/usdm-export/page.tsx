"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  ArrowLeft, 
  Download, 
  CheckCircle, 
  AlertCircle, 
  AlertTriangle,
  Copy,
  FileJson
} from "lucide-react"
import { toast } from "sonner"

interface ValidationIssue {
  level: 'error' | 'warning' | 'info'
  category: string
  path?: string
  message: string
  suggestion?: string
}

interface ValidationReport {
  valid: boolean
  errors: number
  warnings: number
  info: number
  issues: ValidationIssue[]
}

interface USDMData {
  study: any
  usdmVersion: string
  systemName: string
  systemVersion: string
  generatedDate: string
}

export default function USDMExportPage() {
  const router = useRouter()
  
  const [usdmData, setUsdmData] = useState<USDMData | null>(null)
  const [validation, setValidation] = useState<ValidationReport | null>(null)
  const [activeTab, setActiveTab] = useState<'json' | 'validation'>('json')
  const [copied, setCopied] = useState(false)
  
  useEffect(() => {
    // Get data from sessionStorage (passed from export button)
    const storedData = sessionStorage.getItem('usdm_export_data')
    const storedValidation = sessionStorage.getItem('usdm_export_validation')
    
    if (storedData) {
      try {
        setUsdmData(JSON.parse(storedData))
      } catch (e) {
        console.error('Error parsing USDM data:', e)
        toast.error('Failed to load USDM data')
      }
    }
    
    if (storedValidation) {
      try {
        setValidation(JSON.parse(storedValidation))
      } catch (e) {
        console.error('Error parsing validation:', e)
      }
    }
    
    // If no data, redirect back
    if (!storedData) {
      toast.error('No USDM data found')
      router.push('/study-designer')
    }
  }, [router])
  
  const handleDownload = () => {
    if (!usdmData) return
    
    const studyName = usdmData.study?.name || 'study'
    const filename = `${studyName.replace(/\s+/g, '_')}_usdm_${new Date().toISOString().split('T')[0]}.json`
    
    const blob = new Blob([JSON.stringify(usdmData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    
    toast.success(`Downloaded: ${filename}`)
  }
  
  const handleCopy = () => {
    if (!usdmData) return
    
    navigator.clipboard.writeText(JSON.stringify(usdmData, null, 2))
    setCopied(true)
    toast.success('USDM JSON copied to clipboard')
    
    setTimeout(() => setCopied(false), 2000)
  }
  
  const getIssueIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />
      case 'info':
        return <CheckCircle className="h-4 w-4 text-blue-500" />
      default:
        return null
    }
  }
  
  const getIssueBadgeVariant = (level: string) => {
    switch (level) {
      case 'error':
        return 'destructive'
      case 'warning':
        return 'default'
      case 'info':
        return 'secondary'
      default:
        return 'default'
    }
  }
  
  if (!usdmData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-muted-foreground">Loading USDM data...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="w-full px-4 sm:px-6 py-4 max-w-full">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/study-designer')}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Study Designer
              </Button>
              
              <div className="h-8 w-px bg-border" />
              
              <div>
                <h1 className="text-2xl font-bold flex items-center gap-2">
                  <FileJson className="h-6 w-6 text-purple-500" />
                  USDM Export
                </h1>
                <p className="text-sm text-muted-foreground">
                  {usdmData.study?.name || 'Untitled Study'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="gap-2"
              >
                <Copy className="h-4 w-4" />
                {copied ? 'Copied!' : 'Copy JSON'}
              </Button>
              
              <Button
                onClick={handleDownload}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Download JSON
              </Button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="w-full px-4 sm:px-6 py-6 max-w-full overflow-hidden">
        <div className="grid gap-6 max-w-7xl mx-auto">
          {/* Validation Summary */}
          {validation && (
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Validation Summary</h2>
                {validation.valid ? (
                  <Badge variant="default" className="gap-1 bg-green-500">
                    <CheckCircle className="h-3 w-3" />
                    Valid
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Has Errors
                  </Badge>
                )}
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="flex items-center gap-3 p-3 border border-destructive/50 rounded-lg bg-destructive/5">
                  <AlertCircle className="h-5 w-5 text-destructive" />
                  <div>
                    <div className="text-2xl font-bold">{validation.errors}</div>
                    <div className="text-xs text-muted-foreground">Errors</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-3 border border-amber-500/50 rounded-lg bg-amber-500/5">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  <div>
                    <div className="text-2xl font-bold">{validation.warnings}</div>
                    <div className="text-xs text-muted-foreground">Warnings</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-3 border border-blue-500/50 rounded-lg bg-blue-500/5">
                  <CheckCircle className="h-5 w-5 text-blue-500" />
                  <div>
                    <div className="text-2xl font-bold">{validation.info}</div>
                    <div className="text-xs text-muted-foreground">Info</div>
                  </div>
                </div>
              </div>
            </Card>
          )}
          
          {/* Tabs */}
          <div className="flex gap-2 border-b border-border">
            <button
              onClick={() => setActiveTab('json')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'json'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              USDM JSON
            </button>
            <button
              onClick={() => setActiveTab('validation')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'validation'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              Validation Details ({validation?.issues?.length || 0})
            </button>
          </div>
          
          {/* Content Area */}
          {activeTab === 'json' ? (
            <Card className="p-0 overflow-hidden">
              <ScrollArea className="h-[70vh] max-h-[600px]">
                <pre className="p-6 text-sm font-mono whitespace-pre-wrap break-words overflow-x-auto">
                  {JSON.stringify(usdmData, null, 2)}
                </pre>
              </ScrollArea>
            </Card>
          ) : (
            <Card className="p-6 overflow-hidden">
              <ScrollArea className="h-[70vh] max-h-[600px]">
                {validation && validation.issues.length > 0 ? (
                  <div className="space-y-3">
                    {validation.issues.map((issue, idx) => (
                      <div
                        key={idx}
                        className={`p-4 border rounded-lg ${
                          issue.level === 'error' ? 'border-destructive/50 bg-destructive/5' :
                          issue.level === 'warning' ? 'border-amber-500/50 bg-amber-500/5' :
                          'border-blue-500/50 bg-blue-500/5'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {getIssueIcon(issue.level)}
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant={getIssueBadgeVariant(issue.level)} className="text-xs">
                                {issue.level.toUpperCase()}
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {issue.category}
                              </Badge>
                            </div>
                            
                            {issue.path && (
                              <div className="text-xs text-muted-foreground mb-2">
                                Path: <code className="bg-muted px-1 py-0.5 rounded">{issue.path}</code>
                              </div>
                            )}
                            
                            <div className="text-sm text-foreground mb-2">
                              {issue.message}
                            </div>
                            
                            {issue.suggestion && (
                              <div className="text-xs text-muted-foreground italic">
                                💡 {issue.suggestion}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                    <p className="text-lg font-medium">No validation issues found!</p>
                    <p className="text-sm">Your USDM export is valid and ready to use.</p>
                  </div>
                )}
              </ScrollArea>
            </Card>
          )}
          
          {/* Metadata */}
          <Card className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground mb-1">USDM Version</div>
                <div className="font-medium">{usdmData.usdmVersion}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">System</div>
                <div className="font-medium">{usdmData.systemName} v{usdmData.systemVersion}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Generated</div>
                <div className="font-medium">
                  {new Date(usdmData.generatedDate).toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Study Phase</div>
                <div className="font-medium">
                  {usdmData.study?.versions?.[0]?.studyPhase?.standardCode?.decode || 'N/A'}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

