"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Combobox, stringOptionsToCombobox } from "@/components/ui/combobox"
import { Textarea } from "@/components/ui/textarea"
import { useStudyDesigner } from "@/lib/contexts/study-designer-context"
import { Info } from "lucide-react"

export function BasicInfoTab() {
  const { studyContext, updateBasicInfo } = useStudyDesigner()

  const handleChange = (field: string, value: any) => {
    updateBasicInfo({
      [field]: value,
    })
  }

  // Normalize phase value for the select (remove "Phase" prefix if present)
  const normalizePhase = (phase: string | undefined) => {
    if (!phase) return ""
    return phase.replace(/^Phase\s+/i, "").trim()
  }

  // Get the normalized phase value for the select
  const normalizedPhase = normalizePhase(studyContext.phase)

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      

      {/* Study Identity */}
      <Card>
        <CardHeader>
          <CardTitle>Study Identity</CardTitle>
          <CardDescription>Basic identification and categorization</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="indication">Indication *</Label>
              <Input
                id="indication"
                placeholder="e.g., Non-Small Cell Lung Cancer"
                value={studyContext.indication || ""}
                onChange={(e) => handleChange("indication", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="therapeuticArea">Therapeutic Area *</Label>
              <Combobox
                options={stringOptionsToCombobox([
                  "Oncology",
                  "Cardiology",
                  "Neurology",
                  "Immunology",
                  "Infectious Disease",
                  "Metabolic",
                  "Respiratory",
                  "Rare Disease",
                  "Dermatology",
                  "Endocrinology",
                  "Gastroenterology",
                  "Hematology",
                  "Nephrology",
                  "Ophthalmology",
                  "Orthopedics",
                  "Psychiatry",
                  "Rheumatology",
                  "Urology",
                  "Other"
                ])}
                value={studyContext.therapeuticArea || ""}
                onChange={(value) => handleChange("therapeuticArea", value)}
                placeholder="Select therapeutic area"
                searchPlaceholder="Search therapeutic areas..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phase">Phase *</Label>
              <Combobox
                options={stringOptionsToCombobox([
                  "I",
                  "I/II",
                  "II",
                  "II/III",
                  "III",
                  "III/IV",
                  "IV"
                ])}
                value={normalizedPhase}
                onChange={(value) => handleChange("phase", `Phase ${value}`)}
                placeholder="Select phase"
                searchPlaceholder="Search phases..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="drugName">Drug/Molecule Name *</Label>
              <Input
                id="drugName"
                placeholder="e.g., ABC-123"
                value={studyContext.drugName || ""}
                onChange={(e) => handleChange("drugName", e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="studyTitle">Study Title (Optional)</Label>
            <Input
              id="studyTitle"
              placeholder="Full study title (leave blank for auto-generation)"
              value={studyContext.studyTitle || ""}
              onChange={(e) => handleChange("studyTitle", e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              If left blank, will auto-generate from Phase, Indication, and Drug Name
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Study Design Parameters */}
      <Card>
        <CardHeader>
          <CardTitle>Study Design Parameters</CardTitle>
          <CardDescription>Key metrics for planning and analysis</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="patientCount">Target Patient Count *</Label>
              <Input
                id="patientCount"
                type="number"
                min="1"
                placeholder="e.g., 300"
                value={studyContext.patient_count || ""}
                onChange={(e) => handleChange("patient_count", parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="durationMonths">Study Duration (Months) *</Label>
              <Input
                id="durationMonths"
                type="number"
                min="1"
                placeholder="e.g., 24"
                value={studyContext.duration_months || ""}
                onChange={(e) => handleChange("duration_months", parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="siteCount">Target Site Count</Label>
              <Input
                id="siteCount"
                type="number"
                min="1"
                placeholder="e.g., 50"
                value={studyContext.site_count || ""}
                onChange={(e) => handleChange("site_count", parseInt(e.target.value) || 0)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="studyDesign">Study Design</Label>
              <Select
                value={studyContext.studyDesign || ""}
                onValueChange={(value) => handleChange("studyDesign", value)}
              >
                <SelectTrigger id="studyDesign">
                  <SelectValue placeholder="Select study design" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Randomized Controlled Trial">Randomized Controlled Trial</SelectItem>
                  <SelectItem value="Open-Label">Open-Label</SelectItem>
                  <SelectItem value="Double-Blind">Double-Blind</SelectItem>
                  <SelectItem value="Single-Blind">Single-Blind</SelectItem>
                  <SelectItem value="Crossover">Crossover</SelectItem>
                  <SelectItem value="Parallel">Parallel</SelectItem>
                  <SelectItem value="Adaptive">Adaptive</SelectItem>
                  <SelectItem value="Basket">Basket Trial</SelectItem>
                  <SelectItem value="Umbrella">Umbrella Trial</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="primaryEndpoint">Primary Endpoint</Label>
              <Input
                id="primaryEndpoint"
                placeholder="e.g., Overall Survival"
                value={studyContext.primaryEndpoint || ""}
                onChange={(e) => handleChange("primaryEndpoint", e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Details */}
      <Card>
        <CardHeader>
          <CardTitle>Additional Details</CardTitle>
          <CardDescription>Optional information to enhance study context</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="objectives">Study Objectives</Label>
            <Textarea
              id="objectives"
              placeholder="Describe the primary and secondary objectives of this study..."
              rows={4}
              value={studyContext.objectives || ""}
              onChange={(e) => handleChange("objectives", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="background">Background / Rationale</Label>
            <Textarea
              id="background"
              placeholder="Provide background information and rationale for this study..."
              rows={4}
              value={studyContext.background || ""}
              onChange={(e) => handleChange("background", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

