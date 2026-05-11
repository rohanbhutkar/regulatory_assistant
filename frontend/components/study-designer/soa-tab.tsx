"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Sparkles, Save, Plus, Download, Loader2 } from "lucide-react"
import { useProtocolGeneration } from "@/lib/hooks/use-protocol-generation"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { extractReferenceInfoFromTrials } from "@/lib/utils/trial-context-utils"
import { toast } from "sonner"

interface Visit {
  id: string
  name: string
  week: string
  window?: string  // Visit window (e.g., "± 3 days", "± 7 days")
}

interface Activity {
  id: string
  category: string
  name: string
  visits: Record<string, boolean>
}

interface SoATabProps {
  trials?: any[]
  referenceInfo?: string
}

export function SoATab({ trials: propsTrials, referenceInfo: propsReferenceInfo }: SoATabProps = {}) {
  // Use context data with props as fallback
  const {
    protocolSections,
    updateProtocolSection,
    selectedTrials,
    studyContext,
    soaVisits,
    setSoaVisits,
    soaActivities,
    setSoaActivities
  } = useStudyDesigner()
  
  // Extract indication and phase from studyContext
  const indication = studyContext?.indication || ''
  const phase = studyContext?.phase || ''
  const studyDesign = studyContext?.studyDesign || ''
  
  // Protocol generation hook
  const { generateSoA, isGenerating, error } = useProtocolGeneration()
  
  // Use context data if available, otherwise use props
  const trials = propsTrials !== undefined ? propsTrials : selectedTrials
  
  // Extract reference info from the actual selected trials, not global context
  const referenceInfo = propsReferenceInfo !== undefined 
    ? propsReferenceInfo 
    : extractReferenceInfoFromTrials(trials, { indication, phase })
  
  // Get protocol SoA section from context (protocolSections is an object, not array)
  const soaSection = protocolSections?.soa || ''
  
  console.log("🔍 SoA Tab:", {
    soaSection: soaSection ? `${soaSection.substring(0, 100)}...` : 'none',
    usingContext: propsTrials === undefined,
    indication,
    phase,
    studyDesign,
    selectedTrials: trials.length
  })

  // Use context state instead of local state
  const visits = soaVisits as Visit[]
  const setVisits = setSoaVisits
  const activities = soaActivities as Activity[]
  const setActivities = setSoaActivities

  // Load from context when component mounts or when soaSection changes
  useEffect(() => {
    if (soaSection) {
      try {
        const soaData = JSON.parse(soaSection)
        if (soaData.visits && soaData.activities) {
          setVisits(soaData.visits)
          setActivities(soaData.activities)
          console.log("✅ Loaded SoA from context:", soaData)
        }
      } catch (e) {
        // If parsing fails, set default values
        console.log("ℹ️ Setting default SoA values")
        setVisits([
          { id: "1", name: "Screening", week: "-2", window: "± 3 days" },
          { id: "2", name: "Baseline", week: "0", window: "Day 1" },
          { id: "3", name: "Week 4", week: "4", window: "± 3 days" },
          { id: "4", name: "Week 12", week: "12", window: "± 7 days" },
          { id: "5", name: "Week 24", week: "24", window: "± 7 days" },
        ])
        setActivities([
          {
            id: "1",
            category: "Screening",
            name: "Informed Consent",
            visits: { "1": true, "2": false, "3": false, "4": false, "5": false },
          },
          {
            id: "2",
            category: "Screening",
            name: "Medical History",
            visits: { "1": true, "2": false, "3": false, "4": false, "5": false },
          },
          {
            id: "3",
            category: "Assessments",
            name: "Vital Signs",
            visits: { "1": true, "2": true, "3": true, "4": true, "5": true },
          },
          {
            id: "4",
            category: "Assessments",
            name: "Laboratory Tests",
            visits: { "1": true, "2": true, "3": false, "4": true, "5": true },
          },
          {
            id: "5",
            category: "Treatment",
            name: "Study Drug Administration",
            visits: { "1": false, "2": true, "3": true, "4": true, "5": true },
          },
        ])
      }
    } else {
      // Set default values if no saved data
      setVisits([
        { id: "1", name: "Screening", week: "-2", window: "± 3 days" },
        { id: "2", name: "Baseline", week: "0", window: "Day 1" },
        { id: "3", name: "Week 4", week: "4", window: "± 3 days" },
        { id: "4", name: "Week 12", week: "12", window: "± 7 days" },
        { id: "5", name: "Week 24", week: "24", window: "± 7 days" },
      ])
      setActivities([
        {
          id: "1",
          category: "Screening",
          name: "Informed Consent",
          visits: { "1": true, "2": false, "3": false, "4": false, "5": false },
        },
        {
          id: "2",
          category: "Screening",
          name: "Medical History",
          visits: { "1": true, "2": false, "3": false, "4": false, "5": false },
        },
        {
          id: "3",
          category: "Assessments",
          name: "Vital Signs",
          visits: { "1": true, "2": true, "3": true, "4": true, "5": true },
        },
        {
          id: "4",
          category: "Assessments",
          name: "Laboratory Tests",
          visits: { "1": true, "2": true, "3": false, "4": true, "5": true },
        },
        {
          id: "5",
          category: "Treatment",
          name: "Study Drug Administration",
          visits: { "1": false, "2": true, "3": true, "4": true, "5": true },
        },
      ])
    }
  }, [soaSection])

  // Calculate appropriate visit window based on week number and study phase
  const calculateVisitWindow = (week: number, totalWeeks: number): string => {
    // Screening and baseline: tight windows
    if (week <= 0) return "± 3 days"
    
    // Early visits (first 25% of study): ± 3-5 days
    if (week <= totalWeeks * 0.25) return "± 3 days"
    
    // Mid study (25-50%): ± 5-7 days
    if (week <= totalWeeks * 0.5) return "± 5 days"
    
    // Later visits (50-75%): ± 7 days
    if (week <= totalWeeks * 0.75) return "± 7 days"
    
    // Late study (>75%): ± 7-14 days
    return "± 14 days"
  }

  // Generate visits based on study duration from context
  const generateVisitsFromDuration = (): Visit[] => {
    const durationWeeks = studyContext.duration_weeks
    const durationMonths = studyContext.duration_months
    
    // If we have duration info, generate appropriate visits
    if (durationWeeks && durationWeeks > 0) {
      const generatedVisits: Visit[] = [
        { id: "1", name: "Screening", week: "-2", window: "± 3 days" },
        { id: "2", name: "Baseline", week: "0", window: "Day 1" }
      ]
      
      // Add visits based on duration
      if (durationWeeks <= 12) {
        // Short study (≤12 weeks): visits every 2-4 weeks
        for (let week = 2; week <= durationWeeks; week += 2) {
          generatedVisits.push({ 
            id: (generatedVisits.length + 1).toString(), 
            name: `Week ${week}`, 
            week: week.toString(),
            window: calculateVisitWindow(week, durationWeeks)
          })
        }
      } else if (durationWeeks <= 26) {
        // Medium study (≤26 weeks): visits every 4 weeks
        for (let week = 4; week <= durationWeeks; week += 4) {
          generatedVisits.push({ 
            id: (generatedVisits.length + 1).toString(), 
            name: `Week ${week}`, 
            week: week.toString(),
            window: calculateVisitWindow(week, durationWeeks)
          })
        }
      } else {
        // Long study (>26 weeks): visits every 4-8 weeks
        for (let week = 4; week <= durationWeeks; week += 8) {
          generatedVisits.push({ 
            id: (generatedVisits.length + 1).toString(), 
            name: `Week ${week}`, 
            week: week.toString(),
            window: calculateVisitWindow(week, durationWeeks)
          })
        }
      }
      
      // Add end of treatment
      generatedVisits.push({ 
        id: (generatedVisits.length + 1).toString(), 
        name: "End of Treatment", 
        week: "EOT",
        window: "± 7 days"
      })
      
      console.log(`📅 Generated ${generatedVisits.length} visits with windows based on ${durationWeeks} weeks duration`)
      return generatedVisits
    }
    
    // Default visits if no duration info
    return [
      { id: "1", name: "Screening", week: "-2", window: "± 3 days" },
      { id: "2", name: "Baseline", week: "0", window: "Day 1" },
      { id: "3", name: "Week 4", week: "4", window: "± 3 days" },
      { id: "4", name: "Week 12", week: "12", window: "± 7 days" },
      { id: "5", name: "Week 24", week: "24", window: "± 7 days" },
    ]
  }

  // Update visits when duration changes
  useEffect(() => {
    // Only auto-generate if we don't have saved data and we have duration info
    if (!soaSection && (studyContext.duration_weeks || studyContext.duration_months)) {
      const generatedVisits = generateVisitsFromDuration()
      setVisits(generatedVisits)
      console.log("✅ Auto-generated visits based on study duration:", studyContext.duration_text)
    }
  }, [studyContext.duration_weeks, studyContext.duration_months, soaSection])

  const handleSave = () => {
    // Always save current SOA to context
    const soaData = {
      visits,
      activities
    }
    const soaJson = JSON.stringify(soaData)
    console.log('💾 Saving SoA to context:', {
      visits: visits.length,
      activities: activities.length,
      jsonLength: soaJson.length
    })
    updateProtocolSection('soa', soaJson)
    console.log('✅ SoA saved to context via updateProtocolSection')
    toast.success('Schedule of Activities saved successfully!')
  }

  const handleAIGenerate = async () => {
    console.log("🔍 Generating Schedule of Activities with AI...")

    // Validation - check if required fields are present
    if (!indication || !phase) {
      toast.error('Please fill in Basic Info (indication and phase) before generating SoA')
      return
    }

    if (trials.length === 0) {
      toast.error('Please select at least one reference trial before generating SoA')
      return
    }

    try {
      const response = await generateSoA({
        trials: trials,
        reference_info: referenceInfo
      })

      console.log("✅ SoA API Response:", { 
        success: response?.success, 
        contentLength: response?.content?.length || 0,
        contentPreview: response?.content?.substring(0, 200) || 'none'
      })

      if (response && response.content) {
        const content = response.content
        
        // Parse the content to extract visits and activities
        const { visits: parsedVisits, activities: parsedActivities } = parseSOAContent(content)
        
        if (parsedVisits.length === 0) {
          console.warn("⚠️ No visits parsed from content, using defaults")
          // Fallback to default visits
          parsedVisits.push(
            { id: "1", name: "Screening", week: "-2" },
            { id: "2", name: "Baseline", week: "0" },
            { id: "3", name: "Week 4", week: "4" },
            { id: "4", name: "Week 8", week: "8" },
            { id: "5", name: "Week 12", week: "12" },
            { id: "6", name: "End of Treatment", week: "EOT" }
          )
        }
        
        if (parsedActivities.length === 0) {
          console.warn("⚠️ No activities parsed from content, extracting from text")
          // Try to extract activities from plain text
          const lines = content.split('\n').filter(line => line.trim())
          lines.forEach((line, index) => {
            // Look for lines that look like activities (not headers)
            if (line.match(/^[-•]\s*(.+)/) || line.match(/^\d+\.\s*(.+)/)) {
              const match = line.match(/^[-•]\s*(.+)/) || line.match(/^\d+\.\s*(.+)/)
              if (match) {
                const activityName = match[1].trim()
                if (activityName.length > 3 && activityName.length < 100) {
                  // Determine category based on keywords
                  let category = "Other"
                  if (activityName.toLowerCase().includes('consent') || activityName.toLowerCase().includes('demographic')) {
                    category = "Administrative"
                  } else if (activityName.toLowerCase().includes('lab') || activityName.toLowerCase().includes('blood')) {
                    category = "Laboratory"
                  } else if (activityName.toLowerCase().includes('ecg') || activityName.toLowerCase().includes('vital')) {
                    category = "Safety"
                  } else if (activityName.toLowerCase().includes('scan') || activityName.toLowerCase().includes('image')) {
                    category = "Disease Assessment"
                  }
                  
                  // Create visits mapping (all enabled by default)
                  const visitMapping: Record<string, boolean> = {}
                  parsedVisits.forEach(v => { visitMapping[v.id] = true })
                  
                  parsedActivities.push({
                    id: String(parsedActivities.length + 1),
                    category: category,
                    name: activityName,
                    visits: visitMapping
                  })
                }
              }
            }
          })
        }
        
        console.log("📊 Parsed SoA:", { 
          visitsCount: parsedVisits.length, 
          activitiesCount: parsedActivities.length 
        })
        
        setVisits(parsedVisits)
        setActivities(parsedActivities)
        
        // Save to context if available
        if (propsTrials === undefined) {
          const soaData = {
            visits: parsedVisits,
            activities: parsedActivities
          }
          updateProtocolSection('soa', JSON.stringify(soaData))
        }
        
        toast.success(`Schedule of Activities generated with ${parsedActivities.length} activities across ${parsedVisits.length} visits!`)
      } else {
        toast.error('Failed to generate Schedule of Activities. Please try again.')
      }
    } catch (err: any) {
      // Silently ignore cancelled requests
      if (err?.code === 'REQUEST_CANCELLED' || err?.message?.includes('cancelled')) {
        console.log('SoA generation request cancelled')
        return
      }
      
      console.error('Error generating SOA:', err)
      toast.error('Error generating Schedule of Activities. Please try again.')
    }
  }

  // Helper function to parse SOA content from markdown table format
  const parseSOAContent = (content: string): { visits: Visit[], activities: Activity[] } => {
    const visits: Visit[] = []
    const activities: Activity[] = []
    
    const lines = content.split('\n').map(l => l.trim()).filter(l => l)
    
    // Look for table headers (visit columns)
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      
      // Check if this is a table header line
      if (line.includes('|') && (line.toLowerCase().includes('screening') || line.toLowerCase().includes('baseline') || line.toLowerCase().includes('week'))) {
        const columns = line.split('|').map(c => c.trim()).filter(c => c)
        
        // First column is usually "Procedure/Assessment" or similar
        for (let j = 1; j < columns.length; j++) {
          const col = columns[j]
          
          // Extract visit name and week
          let visitName = col
          let week = String(j - 1)
          
          // Try to parse week number from column name
          const weekMatch = col.match(/Week\s+(\d+)/i)
          if (weekMatch) {
            week = weekMatch[1]
            visitName = `Week ${week}`
          } else if (col.toLowerCase().includes('screening')) {
            week = "-2"
            visitName = "Screening"
          } else if (col.toLowerCase().includes('baseline') || col.toLowerCase().includes('day 1')) {
            week = "0"
            visitName = "Baseline"
          } else if (col.toLowerCase().includes('end of treatment') || col.toLowerCase().includes('eot')) {
            week = "EOT"
            visitName = "End of Treatment"
          } else if (col.toLowerCase().includes('follow-up') || col.toLowerCase().includes('follow up')) {
            week = "F/U"
            visitName = "Follow-up"
          }
          
          visits.push({
            id: String(visits.length + 1),
            name: visitName,
            week: week
          })
        }
        
        // Skip separator line if present
        if (i + 1 < lines.length && lines[i + 1].includes('---')) {
          i++
        }
        
        // Parse activity rows
        for (let j = i + 1; j < lines.length; j++) {
          const activityLine = lines[j]
          
          if (!activityLine.includes('|')) break // End of table
          
          const cells = activityLine.split('|').map(c => c.trim()).filter(c => c)
          
          if (cells.length > 0) {
            const activityName = cells[0]
            
            // Skip if it looks like a header or category
            if (activityName.startsWith('**') || activityName.length < 3) continue
            
            // Determine category
            let category = "Other"
            if (activityName.toLowerCase().includes('consent') || activityName.toLowerCase().includes('demographic') || activityName.toLowerCase().includes('history')) {
              category = "Administrative"
            } else if (activityName.toLowerCase().includes('lab') || activityName.toLowerCase().includes('blood') || activityName.toLowerCase().includes('chemistry')) {
              category = "Laboratory"
            } else if (activityName.toLowerCase().includes('ecg') || activityName.toLowerCase().includes('vital') || activityName.toLowerCase().includes('adverse')) {
              category = "Safety"
            } else if (activityName.toLowerCase().includes('scan') || activityName.toLowerCase().includes('image') || activityName.toLowerCase().includes('tumor') || activityName.toLowerCase().includes('disease')) {
              category = "Disease Assessment"
            } else if (activityName.toLowerCase().includes('pk') || activityName.toLowerCase().includes('pharmacokinetic') || activityName.toLowerCase().includes('pd')) {
              category = "Pharmacokinetics"
            }
            
            // Map visit checkmarks
            const visitMapping: Record<string, boolean> = {}
            for (let k = 1; k < cells.length && k <= visits.length; k++) {
              const cell = cells[k].toLowerCase()
              // Check for X, ✓, •, or any non-empty content
              visitMapping[visits[k - 1].id] = cell.includes('x') || cell.includes('✓') || cell.includes('•') || (cell.length > 0 && cell !== '-')
            }
            
            activities.push({
              id: String(activities.length + 1),
              category: category,
              name: activityName.replace(/\*\*/g, '').trim(),
              visits: visitMapping
            })
          }
        }
        
        break // Only parse first table found
      }
    }
    
    return { visits, activities }
  }

  const toggleActivity = (activityId: string, visitId: string) => {
    setActivities(
      activities.map((activity) =>
        activity.id === activityId
          ? { ...activity, visits: { ...activity.visits, [visitId]: !activity.visits[visitId] } }
          : activity,
      ),
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Schedule of Activities</h2>
          <p className="text-sm text-muted-foreground mt-1">Define study procedures and visit schedule</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleAIGenerate} disabled={isGenerating} className="gap-2 bg-primary hover:bg-primary/90">
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate with AI
              </>
            )}
          </Button>
          <Button variant="outline" className="gap-2 bg-transparent">
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" className="gap-2 bg-transparent" onClick={handleSave}>
            <Save className="h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      <div className="border border-border/50 rounded-lg overflow-hidden bg-card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-secondary/50 border-b border-border/50">
                <th className="text-left p-4 font-semibold text-foreground sticky left-0 bg-secondary/50 min-w-[200px]">
                  Activity
                </th>
                <th className="text-left p-4 font-semibold text-foreground min-w-[100px]">Category</th>
                {visits.map((visit) => (
                  <th key={visit.id} className="text-center p-4 font-semibold text-foreground min-w-[120px]">
                    <div>{visit.name}</div>
                    <div className="text-xs text-muted-foreground font-normal">Week {visit.week}</div>
                    {visit.window && (
                      <div className="text-xs text-muted-foreground/70 font-normal mt-0.5">{visit.window}</div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {activities.map((activity, index) => (
                <tr
                  key={activity.id}
                  className={`border-b border-border/50 hover:bg-secondary/20 ${
                    index % 2 === 0 ? "bg-card" : "bg-secondary/10"
                  }`}
                >
                  <td className="p-4 font-medium text-foreground sticky left-0 bg-inherit">{activity.name}</td>
                  <td className="p-4 text-sm text-muted-foreground">{activity.category}</td>
                  {visits.map((visit) => (
                    <td key={visit.id} className="p-4 text-center">
                      <div className="flex justify-center">
                        <Checkbox
                          checked={activity.visits[visit.id]}
                          onCheckedChange={() => toggleActivity(activity.id, visit.id)}
                        />
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="gap-2 bg-transparent">
          <Plus className="h-4 w-4" />
          Add Activity
        </Button>
        <Button variant="outline" size="sm" className="gap-2 bg-transparent">
          <Plus className="h-4 w-4" />
          Add Visit
        </Button>
      </div>
    </div>
  )
}
