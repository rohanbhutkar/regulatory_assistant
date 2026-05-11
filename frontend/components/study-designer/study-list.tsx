"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { StudyDesign } from "@/lib/types/study-types"
import { Search, Plus, FileText, Clock, Trash2 } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface StudyListProps {
  studies: StudyDesign[]
  onSelectStudy: (study: StudyDesign) => void
  onCreateNew: () => void
  onDeleteStudy?: (studyId: string) => void
}

export function StudyList({ studies, onSelectStudy, onCreateNew, onDeleteStudy }: StudyListProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [studyToDelete, setStudyToDelete] = useState<StudyDesign | null>(null)

  const filteredStudies = studies.filter(
    (study) =>
      study.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      study.therapeuticArea.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const handleDeleteClick = (e: React.MouseEvent, study: StudyDesign) => {
    e.stopPropagation() // Prevent row click
    setStudyToDelete(study)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = () => {
    if (studyToDelete && onDeleteStudy) {
      onDeleteStudy(studyToDelete.id)
    }
    setDeleteDialogOpen(false)
    setStudyToDelete(null)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "design":
        return "bg-info-subtle text-info border-info-subtle"
      case "active":
        return "bg-success-subtle text-success border-success-subtle"
      case "paused":
        return "bg-warning-subtle text-warning border-warning-subtle"
      case "completed":
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
            placeholder="Search studies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-card border-border/50"
          />
        </div>
        <Button onClick={onCreateNew} className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500">
          <Plus className="h-4 w-4" />
          New Study Design
        </Button>
      </div>

      {/* Table */}
      <div className="border border-border/50 rounded-lg overflow-hidden bg-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-secondary/50 hover:bg-secondary/50">
              <TableHead>Study Title</TableHead>
              <TableHead>Therapeutic Area</TableHead>
              <TableHead>Phase</TableHead>
              <TableHead>Molecule</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Recent Activity</TableHead>
              <TableHead>Last Modified</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredStudies.map((study) => (
              <TableRow
                key={study.id}
                className="cursor-pointer hover:bg-secondary/30 transition-colors"
                onClick={() => onSelectStudy(study)}
              >
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <span className="font-medium text-foreground">{study.title}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {study.therapeuticArea}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">
                    {study.phase}
                  </Badge>
                </TableCell>
                <TableCell>
                  {study.molecule ? (
                    <span className="text-sm text-foreground font-medium">{study.molecule}</span>
                  ) : (
                    <span className="text-sm text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={`text-xs ${getStatusColor(study.status)}`}>
                    {study.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Clock className="h-3 w-3" />
                    {study.recentActivity}
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <div>
                    <div>{study.lastModified.toLocaleDateString()}</div>
                    <div className="text-xs">by {study.modifiedBy}</div>
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); onSelectStudy(study); }}>
                      Open
                    </Button>
                    {onDeleteStudy && (
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={(e) => handleDeleteClick(e, study)}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Study?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{studyToDelete?.title}"? This action cannot be undone.
              All study data, including reference trials, protocol sections, and simulation results will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
