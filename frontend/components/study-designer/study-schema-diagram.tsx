"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Calendar, Users, Activity, CheckCircle2 } from "lucide-react"

interface StudyPhase {
  name: string
  duration: string
  visits: number
  assessments: string[]
}

interface StudySchemaDigramProps {
  studyDuration?: string
  numberOfArms?: number
  studyType?: string
  totalParticipants?: number
}

export function StudySchemaDigram({ 
  studyDuration, 
  numberOfArms, 
  studyType,
  totalParticipants 
}: StudySchemaDigramProps = {}) {
  // Calculate phases based on study duration
  const calculatePhases = (): StudyPhase[] => {
    if (!studyDuration) {
      // Default phases
      return [
        {
          name: "Screening",
          duration: "4 weeks",
          visits: 2,
          assessments: ["Eligibility", "Informed Consent", "Baseline Labs"],
        },
        {
          name: "Treatment Period",
          duration: "24 weeks",
          visits: 8,
          assessments: ["Drug Administration", "Safety Monitoring", "Efficacy Assessment"],
        },
        {
          name: "Follow-up",
          duration: "12 weeks",
          visits: 3,
          assessments: ["Safety Follow-up", "Final Assessment", "AE Monitoring"],
        },
      ]
    }
    
    // Parse duration
    const durationText = studyDuration.toLowerCase()
    let totalWeeks = 24 // default
    
    const weeksMatch = durationText.match(/(\d+)\s*weeks?/)
    if (weeksMatch) {
      totalWeeks = parseInt(weeksMatch[1])
    }
    
    const monthsMatch = durationText.match(/(\d+)\s*months?/)
    if (monthsMatch) {
      totalWeeks = Math.round(parseInt(monthsMatch[1]) * 4.33)
    }
    
    const yearsMatch = durationText.match(/(\d+)\s*years?/)
    if (yearsMatch) {
      totalWeeks = parseInt(yearsMatch[1]) * 52
    }
    
    // Calculate phase durations
    const screeningWeeks = Math.min(4, Math.floor(totalWeeks * 0.1))
    const followupWeeks = Math.min(12, Math.floor(totalWeeks * 0.2))
    const treatmentWeeks = totalWeeks - screeningWeeks - followupWeeks
    
    const treatmentVisits = Math.max(2, Math.floor(treatmentWeeks / 4))
    
    return [
      {
        name: "Screening",
        duration: `${screeningWeeks} ${screeningWeeks === 1 ? 'week' : 'weeks'}`,
        visits: Math.max(1, Math.floor(screeningWeeks / 2)),
        assessments: ["Eligibility", "Informed Consent", "Baseline Labs"],
      },
      {
        name: "Treatment Period",
        duration: `${treatmentWeeks} ${treatmentWeeks === 1 ? 'week' : 'weeks'}`,
        visits: treatmentVisits,
        assessments: ["Drug Administration", "Safety Monitoring", "Efficacy Assessment"],
      },
      {
        name: "Follow-up",
        duration: `${followupWeeks} ${followupWeeks === 1 ? 'week' : 'weeks'}`,
        visits: Math.max(1, Math.floor(followupWeeks / 4)),
        assessments: ["Safety Follow-up", "Final Assessment", "AE Monitoring"],
      },
    ]
  }
  
  const phases = calculatePhases()

  return (
    <Card className="p-6 bg-card">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-foreground mb-2">Study Flow Diagram</h3>
        <p className="text-sm text-muted-foreground">Visual representation of study phases and assessments</p>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Horizontal timeline line */}
        <div className="absolute top-12 left-0 right-0 h-0.5 bg-border" />

        {/* Phases */}
        <div className="grid grid-cols-3 gap-8 relative">
          {phases.map((phase, index) => (
            <div key={index} className="relative">
              {/* Phase marker */}
              <div className="flex flex-col items-center mb-4">
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-semibold text-sm mb-2 relative z-10 border-4 border-background">
                  {index + 1}
                </div>
                <div className="text-center">
                  <div className="font-semibold text-foreground">{phase.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center justify-center gap-1 mt-1">
                    <Calendar className="h-3 w-3" />
                    {phase.duration}
                  </div>
                </div>
              </div>

              {/* Phase details card */}
              <Card className="p-4 bg-muted/30 border-border/50 mt-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Users className="h-4 w-4 text-primary" />
                    <span className="text-muted-foreground">Visits:</span>
                    <Badge variant="secondary" className="ml-auto">
                      {phase.visits}
                    </Badge>
                  </div>

                  <div className="border-t border-border pt-3">
                    <div className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1">
                      <Activity className="h-3 w-3" />
                      Key Assessments
                    </div>
                    <div className="space-y-1.5">
                      {phase.assessments.map((assessment, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                          <CheckCircle2 className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                          <span>{assessment}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Arrow to next phase */}
              {index < phases.length - 1 && (
                <div className="absolute top-12 -right-4 transform -translate-y-1/2 z-20">
                  <svg width="32" height="16" viewBox="0 0 32 16" fill="none">
                    <path
                      d="M0 8H30M30 8L24 2M30 8L24 14"
                      stroke="hsl(var(--border))"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Study Summary */}
      <div className="mt-8 pt-6 border-t border-border">
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-foreground">40 weeks</div>
            <div className="text-xs text-muted-foreground mt-1">Total Duration</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-foreground">13 visits</div>
            <div className="text-xs text-muted-foreground mt-1">Total Visits</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-foreground">3 phases</div>
            <div className="text-xs text-muted-foreground mt-1">Study Phases</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-foreground">300</div>
            <div className="text-xs text-muted-foreground mt-1">Target Enrollment</div>
          </div>
        </div>
      </div>
    </Card>
  )
}
