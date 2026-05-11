"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ResearchAgentChat } from "@/components/chat/research-agent-chat"
import { ReferenceTrialsTab } from "./reference-trials-tab"
import { ProtocolSectionEditor } from "./protocol-section-editor"
import { IECriteriaTab } from "./ie-criteria-tab"
import { SiteSelectionTab } from "./site-selection-tab"
import { SimulationTab } from "./simulation-tab"
import { BudgetTab } from "./budget-tab"
import { CollaborativeEditor } from "./collaborative-editor"
import type { StudyDesign } from "@/lib/types/study-types"
import { Users, MapPin, PlayCircle, DollarSign } from "lucide-react"

interface CollaborativeWorkspaceProps {
  study: StudyDesign
  onStudyChange: (study: StudyDesign) => void
}

export function CollaborativeWorkspace({ study, onStudyChange }: CollaborativeWorkspaceProps) {
  const [activeTab, setActiveTab] = useState("base-info")

  const updateStudy = (updates: Partial<StudyDesign>) => {
    onStudyChange({ ...study, ...updates })
  }

  return (
    <div className="h-full flex min-h-0">
      {/* Chat Panel - Left Side */}
      <div className="w-96 border-r border-border/50 flex flex-col min-h-0 bg-card/30">
        <div className="p-4 border-b border-border/50 shrink-0">
          <h3 className="font-semibold text-foreground">Study Design Assistant</h3>
          <p className="text-xs text-muted-foreground">AI-powered research and planning</p>
        </div>
        <div className="flex-1 min-h-0 overflow-hidden">
          <ResearchAgentChat />
        </div>
      </div>

      {/* Canvas Panel - Right Side */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Tab Navigation */}
        <div className="border-b border-border/50 bg-card/30">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="px-4 overflow-x-auto">
              <TabsList className="inline-flex">
                <TabsTrigger value="base-info">Base Info</TabsTrigger>
                <TabsTrigger value="reference-trials" className="gap-2">
                  <Users className="h-4 w-4" />
                  Reference Trials
                </TabsTrigger>
                <TabsTrigger value="protocol-title">Protocol Title</TabsTrigger>
                <TabsTrigger value="rationale">Rationale</TabsTrigger>
                <TabsTrigger value="objectives">Objectives</TabsTrigger>
                <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
                <TabsTrigger value="ie-criteria">IE Criteria</TabsTrigger>
                <TabsTrigger value="overall-design">Overall Design</TabsTrigger>
                <TabsTrigger value="schema">Schema</TabsTrigger>
                <TabsTrigger value="soa">Schedule of Activities</TabsTrigger>
                <TabsTrigger value="site-selection" className="gap-2">
                  <MapPin className="h-4 w-4" />
                  Site Selection
                </TabsTrigger>
                <TabsTrigger value="simulation" className="gap-2">
                  <PlayCircle className="h-4 w-4" />
                  Simulation
                </TabsTrigger>
                <TabsTrigger value="budget" className="gap-2">
                  <DollarSign className="h-4 w-4" />
                  Budget
                </TabsTrigger>
              </TabsList>
            </div>
          </Tabs>
        </div>

        {/* Canvas Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === "base-info" && (
            <Card className="p-6 max-w-4xl mx-auto">
              <h2 className="text-2xl font-bold mb-6 text-foreground">Base Study Information</h2>
              <div className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="asset">Asset</Label>
                  <Input
                    id="asset"
                    placeholder="e.g., BMS-986012"
                    value={study.title}
                    onChange={(e) => updateStudy({ title: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="phase">Phase</Label>
                    <Select value={study.phase} onValueChange={(phase) => updateStudy({ phase })}>
                      <SelectTrigger id="phase">
                        <SelectValue placeholder="Select phase" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Phase I">Phase I</SelectItem>
                        <SelectItem value="Phase II">Phase II</SelectItem>
                        <SelectItem value="Phase III">Phase III</SelectItem>
                        <SelectItem value="Phase IV">Phase IV</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="ta">Therapeutic Area</Label>
                    <Input
                      id="ta"
                      placeholder="e.g., Oncology"
                      value={study.therapeuticArea}
                      onChange={(e) => updateStudy({ therapeuticArea: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="indication">Indication</Label>
                  <Input
                    id="indication"
                    placeholder="e.g., Advanced Non-Small Cell Lung Cancer"
                    value={study.indication}
                    onChange={(e) => updateStudy({ indication: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Countries & Population</Label>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <Input placeholder="Country" defaultValue="United States" />
                      <Input placeholder="Population" type="number" defaultValue="250" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <Input placeholder="Country" defaultValue="Germany" />
                      <Input placeholder="Population" type="number" defaultValue="100" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <Input placeholder="Country" defaultValue="Japan" />
                      <Input placeholder="Population" type="number" defaultValue="75" />
                    </div>
                    <Button variant="outline" size="sm" className="w-full bg-transparent">
                      + Add Country
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "reference-trials" && (
            <ReferenceTrialsTab
              trials={study.referenceTrials}
              onTrialsChange={(trials) => updateStudy({ referenceTrials: trials })}
            />
          )}

          {activeTab === "protocol-title" && (
            <CollaborativeEditor
              title="Protocol Title"
              content={study.protocolSections.find((s) => s.type === "title")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "title")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "title",
                    title: "Protocol Title",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
              changes={study.protocolSections.find((s) => s.type === "title")?.changes || []}
              comments={study.protocolSections.find((s) => s.type === "title")?.comments || []}
              onChangesUpdate={(changes) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "title")
                if (index >= 0) {
                  sections[index].changes = changes
                  updateStudy({ protocolSections: sections })
                }
              }}
              onCommentsUpdate={(comments) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "title")
                if (index >= 0) {
                  sections[index].comments = comments
                  updateStudy({ protocolSections: sections })
                }
              }}
            />
          )}

          {activeTab === "rationale" && (
            <CollaborativeEditor
              title="Rationale"
              content={study.protocolSections.find((s) => s.type === "rationale")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "rationale")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "rationale",
                    title: "Rationale",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
              changes={study.protocolSections.find((s) => s.type === "rationale")?.changes || []}
              comments={study.protocolSections.find((s) => s.type === "rationale")?.comments || []}
              onChangesUpdate={(changes) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "rationale")
                if (index >= 0) {
                  sections[index].changes = changes
                  updateStudy({ protocolSections: sections })
                }
              }}
              onCommentsUpdate={(comments) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "rationale")
                if (index >= 0) {
                  sections[index].comments = comments
                  updateStudy({ protocolSections: sections })
                }
              }}
            />
          )}

          {activeTab === "objectives" && (
            <CollaborativeEditor
              title="Primary and Secondary Objectives"
              content={study.protocolSections.find((s) => s.type === "objectives")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "objectives")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "objectives",
                    title: "Objectives",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
              changes={study.protocolSections.find((s) => s.type === "objectives")?.changes || []}
              comments={study.protocolSections.find((s) => s.type === "objectives")?.comments || []}
              onChangesUpdate={(changes) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "objectives")
                if (index >= 0) {
                  sections[index].changes = changes
                  updateStudy({ protocolSections: sections })
                }
              }}
              onCommentsUpdate={(comments) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "objectives")
                if (index >= 0) {
                  sections[index].comments = comments
                  updateStudy({ protocolSections: sections })
                }
              }}
            />
          )}

          {activeTab === "endpoints" && (
            <CollaborativeEditor
              title="Primary and Secondary Endpoints and Estimands"
              content={study.protocolSections.find((s) => s.type === "endpoints")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "endpoints")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "endpoints",
                    title: "Endpoints",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
              changes={study.protocolSections.find((s) => s.type === "endpoints")?.changes || []}
              comments={study.protocolSections.find((s) => s.type === "endpoints")?.comments || []}
              onChangesUpdate={(changes) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "endpoints")
                if (index >= 0) {
                  sections[index].changes = changes
                  updateStudy({ protocolSections: sections })
                }
              }}
              onCommentsUpdate={(comments) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "endpoints")
                if (index >= 0) {
                  sections[index].comments = comments
                  updateStudy({ protocolSections: sections })
                }
              }}
            />
          )}

          {activeTab === "ie-criteria" && (
            <IECriteriaTab
              criteria={study.ieCriteria}
              onCriteriaChange={(criteria) => updateStudy({ ieCriteria: criteria })}
            />
          )}

          {activeTab === "overall-design" && (
            <CollaborativeEditor
              title="Overall Design"
              content={study.protocolSections.find((s) => s.type === "overall-design")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "overall-design")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "overall-design",
                    title: "Overall Design",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
              changes={study.protocolSections.find((s) => s.type === "overall-design")?.changes || []}
              comments={study.protocolSections.find((s) => s.type === "overall-design")?.comments || []}
              onChangesUpdate={(changes) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "overall-design")
                if (index >= 0) {
                  sections[index].changes = changes
                  updateStudy({ protocolSections: sections })
                }
              }}
              onCommentsUpdate={(comments) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "overall-design")
                if (index >= 0) {
                  sections[index].comments = comments
                  updateStudy({ protocolSections: sections })
                }
              }}
            />
          )}

          {activeTab === "schema" && (
            <ProtocolSectionEditor
              title="Schema"
              content={study.protocolSections.find((s) => s.type === "schema")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "schema")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "schema",
                    title: "Schema",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
            />
          )}

          {activeTab === "soa" && (
            <ProtocolSectionEditor
              title="Schedule of Activities"
              content={study.protocolSections.find((s) => s.type === "soa")?.content || ""}
              onContentChange={(content) => {
                const sections = [...study.protocolSections]
                const index = sections.findIndex((s) => s.type === "soa")
                if (index >= 0) {
                  sections[index].content = content
                } else {
                  sections.push({
                    id: `section-${Date.now()}`,
                    type: "soa",
                    title: "Schedule of Activities",
                    content,
                    status: "draft",
                    lastModified: new Date(),
                    comments: [],
                  })
                }
                updateStudy({ protocolSections: sections })
              }}
            />
          )}

          {activeTab === "site-selection" && (
            <SiteSelectionTab sites={study.sites} onSitesChange={(sites) => updateStudy({ sites })} />
          )}

          {activeTab === "simulation" && (
            <SimulationTab
              simulation={study.simulation}
              onSimulationChange={(simulation) => updateStudy({ simulation })}
            />
          )}

          {activeTab === "budget" && <BudgetTab studyId={study.id} />}
        </div>
      </div>
    </div>
  )
}
