"use client"

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { useStudyDesigner, type Insight } from '@/lib/contexts/study-designer-context'
import { 
  Sparkles, 
  ChevronRight, 
  ChevronLeft, 
  RefreshCw, 
  Download,
  ChevronDown,
  ChevronUp,
  Info,
  Loader2
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'

const INSIGHT_TYPES = {
  benchmark: {
    icon: "📊",
    bgGradient: "from-blue-50 to-blue-100",
    borderColor: "border-blue-300",
    badge: "BENCHMARK"
  },
  warning: {
    icon: "⚠️",
    bgGradient: "from-amber-50 to-amber-100",
    borderColor: "border-amber-300",
    badge: "WARNING"
  },
  optimization: {
    icon: "💡",
    bgGradient: "from-green-50 to-green-100", 
    borderColor: "border-green-300",
    badge: "OPTIMIZATION"
  },
  opportunity: {
    icon: "🎯",
    bgGradient: "from-purple-50 to-purple-100",
    borderColor: "border-purple-300", 
    badge: "OPPORTUNITY"
  },
  risk: {
    icon: "🚨",
    bgGradient: "from-red-50 to-red-100",
    borderColor: "border-red-300",
    badge: "RISK"
  },
  bestPractice: {
    icon: "✅",
    bgGradient: "from-emerald-50 to-emerald-100",
    borderColor: "border-emerald-300",
    badge: "BEST PRACTICE"
  }
}

interface AIInsightsPanelProps {
  tab: string
}

export function AIInsightsPanel({ tab }: AIInsightsPanelProps) {
  const {
    insights,
    insightsLoading,
    generateInsights,
    agentActions,
    updateBasicInfo
  } = useStudyDesigner()
  
  const [isOpen, setIsOpen] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  
  const tabInsights = insights[tab] || []
  
  useEffect(() => {
    if (tabInsights.length > 0) {
      setLastUpdated(new Date())
    }
  }, [tabInsights])
  
  const handleGenerate = async () => {
    await generateInsights(tab)
  }
  
  const handleInsightAction = (insightId: string, action: any) => {
    console.log('🎬 Insight action:', insightId, action)
    
    switch (action.action) {
      case 'view_reference_trials':
        agentActions.switchToTab('reference-trials')
        break
        
      case 'adjust_patient_count':
      case 'adjust_duration':
        agentActions.switchToTab('basic-info')
        break
        
      case 'update_site_count':
        if (action.value) {
          updateBasicInfo({ site_count: action.value })
          toast.success(`Updated site count to ${action.value}`)
        }
        break
        
      case 'optimize_patient_count':
        if (action.value) {
          updateBasicInfo({ patient_count: action.value })
          toast.success(`Updated patient count to ${action.value}`)
        }
        break
        
      case 'run_power_analysis':
        toast.info('Power analysis feature coming soon')
        break
        
      case 'simulate_site_reduction':
        agentActions.switchToTab('simulation')
        break
        
      case 'change_endpoint':
        agentActions.switchToTab('endpoints')
        break
        
      case 'filter_trials_by_endpoint':
        agentActions.switchToTab('reference-trials')
        break
        
      case 'search_adjacent_phases':
        agentActions.switchToTab('reference-trials')
        toast.info('Tip: Search for adjacent phase trials to broaden your analysis')
        break
        
      case 'highlight_outlier_trials':
      case 'remove_outlier_trials':
        agentActions.switchToTab('reference-trials')
        toast.info('Review outlier trials in the Reference Trials tab')
        break
        
      default:
        console.warn(`Unhandled action: ${action.action}`)
        toast.info('This action will be available in a future update')
    }
  }
  
  const handleExport = () => {
    const dataStr = JSON.stringify(tabInsights, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    const exportFileDefaultName = `insights-${tab}-${new Date().toISOString().split('T')[0]}.json`
    
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }
  
  return (
    <>
    <motion.div
      initial={{ x: 400 }}
      animate={{ x: isOpen ? 0 : 400 }}
      transition={{ type: "spring", damping: 20, stiffness: 100 }}
      className="fixed right-0 top-20 h-[calc(100vh-80px)] w-96 bg-white border-l shadow-2xl z-40 overflow-hidden dark:bg-gray-900 dark:border-gray-700"
    >
      <div className="p-4 border-b bg-primary/5 dark:bg-gray-800 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold flex items-center gap-2">
            <span className="text-2xl">🔮</span>
            AI Insights
          </h3>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
        
        {tabInsights.length > 0 && (
          <div className="flex gap-2 mt-2 flex-wrap">
            <Badge variant="secondary" className="text-xs">
              📊 {tabInsights.filter(i => i.type === 'benchmark').length}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              ⚠️ {tabInsights.filter(i => i.type === 'warning').length}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              💡 {tabInsights.filter(i => i.type === 'optimization').length}
            </Badge>
          </div>
        )}
      </div>

      {tabInsights.length === 0 && !insightsLoading && (
        <div className="p-4">
          <Button
            onClick={handleGenerate}
            className="w-full"
            size="lg"
          >
            <Sparkles className="mr-2 h-4 w-4" />
            Generate Insights
          </Button>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Analyze {tab} with AI
          </p>
        </div>
      )}

      {insightsLoading && (
        <div className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="animate-spin h-4 w-4" />
            <span className="text-sm text-muted-foreground">
              Analyzing {tab}...
            </span>
          </div>
          <Progress value={undefined} className="h-2" />
          <p className="text-xs text-muted-foreground mt-2">
            Benchmarking against reference trials...
          </p>
        </div>
      )}

      <ScrollArea className="h-[calc(100%-180px)]">
        <div className="p-4 space-y-3">
          <AnimatePresence>
            {tabInsights.map((insight, index) => (
              <motion.div
                key={insight.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ 
                  delay: index * 0.1,
                  duration: 0.3,
                  ease: "easeOut"
                }}
              >
                <InsightCard
                  insight={insight}
                  onAction={handleInsightAction}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>

      {tabInsights.length > 0 && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t bg-secondary/5 dark:bg-gray-800 dark:border-gray-700">
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerate}
              className="flex-1"
              disabled={insightsLoading}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleExport}
              className="flex-1"
            >
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
          {lastUpdated && (
            <p className="text-xs text-muted-foreground mt-2 text-center">
              Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
            </p>
          )}
        </div>
      )}
    </motion.div>
    
    {/* Collapsed State Button - Outside motion.div so it stays visible */}
    {!isOpen && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-50"
      >
        <Button
          size="sm"
          variant="default"
          onClick={() => setIsOpen(true)}
          className="rounded-l-lg rounded-r-none shadow-lg"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </motion.div>
    )}
    </>
  )
}

function InsightCard({ insight, onAction }: { insight: Insight, onAction: (id: string, action: any) => void }) {
  const [expanded, setExpanded] = useState(false)
  const config = INSIGHT_TYPES[insight.type as keyof typeof INSIGHT_TYPES]

  return (
    <Card className={cn(
      "relative overflow-hidden transition-all duration-300 border-l-4",
      config.borderColor,
      expanded && "shadow-lg"
    )}>
      <div className={cn(
        "absolute inset-0 opacity-30",
        `bg-gradient-to-br ${config.bgGradient}`
      )} />
      
      <CardContent className="relative p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xl">{config.icon}</span>
            <Badge variant="secondary" className="text-xs">
              {config.badge}
            </Badge>
          </div>
          <Badge variant="outline" className="text-xs">
            {Math.round(insight.confidence * 100)}%
          </Badge>
        </div>

        <p className="font-medium text-sm mb-2">
          {insight.title}
        </p>
        <p className="text-sm text-muted-foreground mb-3">
          {insight.message}
        </p>

        {insight.detail && (
          <Collapsible open={expanded} onOpenChange={setExpanded}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full">
                {expanded ? (
                  <>
                    <ChevronUp className="mr-2 h-4 w-4" />
                    Show Less
                  </>
                ) : (
                  <>
                    <ChevronDown className="mr-2 h-4 w-4" />
                    Show Full Analysis
                  </>
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pt-3 text-sm text-muted-foreground space-y-2">
                {insight.detail.split('\n\n').map((paragraph, idx) => (
                  <p key={idx} className={idx === 0 ? 'font-medium text-foreground' : ''}>
                    {paragraph}
                  </p>
                ))}
              </div>
              {insight.data?.llm_analysis && (
                <div className="mt-3 p-2 bg-primary/5 border-l-2 border-primary rounded">
                  <div className="flex items-center gap-1 mb-1">
                    <Sparkles className="h-3 w-3 text-primary" />
                    <span className="text-xs font-semibold text-primary">AI Analysis</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {insight.data.llm_analysis}
                  </p>
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        )}

        {insight.actions && insight.actions.length > 0 && (
          <div className="flex gap-2 mt-3 flex-wrap">
            {insight.actions.map((action, idx) => (
              <Button
                key={idx}
                size="sm"
                variant={idx === 0 ? "default" : "outline"}
                onClick={() => onAction(insight.id, action)}
                className="text-xs"
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}

        <p className="text-xs text-muted-foreground mt-3 flex items-center gap-1">
          <Info className="h-3 w-3" />
          {insight.source}
        </p>
      </CardContent>
    </Card>
  )
}

