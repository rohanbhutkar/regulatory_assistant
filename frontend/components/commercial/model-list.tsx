"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { CommercialModel } from "@/lib/types/commercial-types"
import { Search, Plus, BarChart3, Clock } from "lucide-react"

interface ModelListProps {
  models: CommercialModel[]
  onSelectModel: (model: CommercialModel) => void
  onCreateNew: () => void
}

export function ModelList({ models, onSelectModel, onCreateNew }: ModelListProps) {
  const [searchTerm, setSearchTerm] = useState("")

  const filteredModels = models.filter(
    (model) =>
      model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      model.assetName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      model.indication.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const getStatusColor = (status: string) => {
    switch (status) {
      case "draft":
        return "bg-info-subtle text-info border-info-subtle"
      case "active":
        return "bg-success-subtle text-success border-success-subtle"
      case "archived":
        return "bg-muted text-muted-foreground border-border"
      default:
        return ""
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search models..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-card border-border/50"
          />
        </div>
        <Button onClick={onCreateNew} className="gap-2">
          <Plus className="h-4 w-4" />
          New Commercial Model
        </Button>
      </div>

      {/* Table */}
      <div className="border border-border/50 rounded-lg overflow-hidden bg-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-secondary/50 hover:bg-secondary/50">
              <TableHead>Model Name</TableHead>
              <TableHead>Asset</TableHead>
              <TableHead>Indication</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Recent Activity</TableHead>
              <TableHead>Last Modified</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredModels.map((model) => (
              <TableRow
                key={model.id}
                className="cursor-pointer hover:bg-secondary/30 transition-colors"
                onClick={() => onSelectModel(model)}
              >
                <TableCell>
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <span className="font-medium text-foreground">{model.name}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {model.assetName}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">
                    {model.indication}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={`text-xs ${getStatusColor(model.status)}`}>
                    {model.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Clock className="h-3 w-3" />
                    {model.recentActivity}
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <div>
                    <div>{model.lastModified.toLocaleDateString()}</div>
                    <div className="text-xs">by {model.modifiedBy}</div>
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" onClick={() => onSelectModel(model)}>
                    Open
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
