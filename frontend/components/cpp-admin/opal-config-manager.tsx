/**
 * OPAL Hours Configuration Manager
 * View and manage overhead staffing hour distributions
 */

"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Calculator, Users, TrendingUp, Info } from 'lucide-react'

interface StaffRole {
  role: string
  abbreviation: string
  typical_hours: Record<string, number>
  color: string
}

interface VisitType {
  visit_name: string
  typical_duration: number
  roles_required: string[]
}

export function OPALConfigManager() {
  const staffRoles: StaffRole[] = [
    {
      role: 'Principal Investigator',
      abbreviation: 'PI',
      typical_hours: {
        'Screening Baseline': 2.0,
        'Treatment Period (Site Visit)': 1.5,
        'End of Treatment': 2.0,
        'Follow-up': 1.0
      },
      color: 'bg-blue-500'
    },
    {
      role: 'Nurse',
      abbreviation: 'RN',
      typical_hours: {
        'Screening Baseline': 3.0,
        'Treatment Period (Site Visit)': 2.5,
        'End of Treatment': 3.0,
        'Follow-up': 2.0
      },
      color: 'bg-green-500'
    },
    {
      role: 'Study Coordinator',
      abbreviation: 'CRC',
      typical_hours: {
        'Screening Baseline': 4.0,
        'Treatment Period (Site Visit)': 3.0,
        'End of Treatment': 4.0,
        'Follow-up': 2.5
      },
      color: 'bg-purple-500'
    },
    {
      role: 'Clinical Research Associate',
      abbreviation: 'CRA',
      typical_hours: {
        'Screening Baseline': 2.5,
        'Treatment Period (Site Visit)': 2.0,
        'End of Treatment': 2.5,
        'Follow-up': 1.5
      },
      color: 'bg-orange-500'
    }
  ]

  const visitTypes: VisitType[] = [
    {
      visit_name: 'Screening Baseline',
      typical_duration: 240,
      roles_required: ['PI', 'RN', 'CRC', 'CRA']
    },
    {
      visit_name: 'Treatment Period (Site Visit)',
      typical_duration: 180,
      roles_required: ['PI', 'RN', 'CRC', 'CRA']
    },
    {
      visit_name: 'End of Treatment',
      typical_duration: 240,
      roles_required: ['PI', 'RN', 'CRC', 'CRA']
    },
    {
      visit_name: 'Follow-up',
      typical_duration: 120,
      roles_required: ['PI', 'RN', 'CRC', 'CRA']
    }
  ]

  const complexityModifiers = [
    {
      name: 'Tissue Biopsy',
      modifier: 10.0,
      description: 'Adds 10 hours for specialized tissue collection and handling'
    },
    {
      name: 'PK Draws',
      modifier: 8.0,
      description: 'Adds 8 hours for pharmacokinetic sampling procedures'
    },
    {
      name: 'Specialized Procedures',
      modifier: 12.0,
      description: 'Adds 12 hours for complex or specialized clinical procedures'
    },
    {
      name: 'Complex Assessments',
      modifier: 6.0,
      description: 'Adds 6 hours for detailed clinical assessments or questionnaires'
    },
    {
      name: 'Early Termination',
      modifier: 15.0,
      description: 'Adds 15 hours for additional documentation and closeout'
    },
    {
      name: 'Oncology Study',
      modifier: 8.0,
      description: 'Adds 8 hours for oncology-specific procedures and monitoring'
    }
  ]

  const getTotalHoursForVisit = (visitName: string) => {
    return staffRoles.reduce((sum, role) => {
      return sum + (role.typical_hours[visitName] || 0)
    }, 0)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Calculator className="h-8 w-8" />
          OPAL Hours Configuration
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure overhead staffing hour distributions by role and visit type
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{staffRoles.length}</div>
            <p className="text-sm text-muted-foreground">Staff Roles</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{visitTypes.length}</div>
            <p className="text-sm text-muted-foreground">Visit Types</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {complexityModifiers.length}
            </div>
            <p className="text-sm text-muted-foreground">Modifiers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">
              {getTotalHoursForVisit('Treatment Period (Site Visit)').toFixed(1)}h
            </div>
            <p className="text-sm text-muted-foreground">Avg Visit Hours</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="hours" className="w-full">
        <TabsList>
          <TabsTrigger value="hours">Staff Hours Matrix</TabsTrigger>
          <TabsTrigger value="modifiers">Complexity Modifiers</TabsTrigger>
          <TabsTrigger value="roles">Role Definitions</TabsTrigger>
        </TabsList>

        {/* Staff Hours Matrix */}
        <TabsContent value="hours">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Staff Hours by Visit Type
              </CardTitle>
              <CardDescription>
                Typical hours required for each staff role per visit type
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Visit Type</TableHead>
                    <TableHead>Duration</TableHead>
                    {staffRoles.map(role => (
                      <TableHead key={role.abbreviation} className="text-center">
                        <div>{role.abbreviation}</div>
                        <div className="text-xs font-normal text-muted-foreground">
                          {role.role}
                        </div>
                      </TableHead>
                    ))}
                    <TableHead className="text-center font-semibold">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visitTypes.map(visit => (
                    <TableRow key={visit.visit_name}>
                      <TableCell className="font-medium">{visit.visit_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{visit.typical_duration} min</Badge>
                      </TableCell>
                      {staffRoles.map(role => (
                        <TableCell key={role.abbreviation} className="text-center">
                          <div className="inline-flex items-center gap-1">
                            <div className={`w-2 h-2 rounded-full ${role.color}`} />
                            <span className="font-semibold">
                              {role.typical_hours[visit.visit_name]?.toFixed(1) || '—'}h
                            </span>
                          </div>
                        </TableCell>
                      ))}
                      <TableCell className="text-center">
                        <Badge className="bg-gray-700">
                          {getTotalHoursForVisit(visit.visit_name).toFixed(1)}h
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Visual Legend */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start gap-2">
                  <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-blue-900">How OPAL Hours Work</p>
                    <p className="text-sm text-blue-800 mt-1">
                      These baseline hours are multiplied by study-specific factors (phase, number of arms,
                      special procedures) to calculate the total overhead staffing requirement. The final
                      OPAL score determines the total hours needed across the study.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Complexity Modifiers */}
        <TabsContent value="modifiers">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Complexity Modifiers
              </CardTitle>
              <CardDescription>
                Additional hours added based on study complexity characteristics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {complexityModifiers.map((modifier, idx) => (
                  <div key={idx} className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{modifier.name}</h3>
                          <Badge className="bg-purple-500">+{modifier.modifier} hours</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {modifier.description}
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Edit
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Example Calculation */}
              <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
                <h4 className="font-semibold text-green-900 mb-2">Example Calculation</h4>
                <div className="space-y-2 text-sm text-green-800">
                  <p>Phase III Study (Base Score: 50.0)</p>
                  <p>+ 2 Arms (Modifier: ×1.1) = 55.0</p>
                  <p>+ Tissue Biopsy (+10.0 hours) = 65.0</p>
                  <p>+ PK Draws (+8.0 hours) = 73.0</p>
                  <p className="font-semibold pt-2 border-t border-green-300">
                    Total OPAL Score: 73.0 hours
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Role Definitions */}
        <TabsContent value="roles">
          <Card>
            <CardHeader>
              <CardTitle>Staff Role Definitions</CardTitle>
              <CardDescription>
                Description and responsibilities for each staff role
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {staffRoles.map((role) => (
                  <div key={role.abbreviation} className="p-4 border rounded-lg">
                    <div className="flex items-start gap-4">
                      <div className={`w-12 h-12 rounded-lg ${role.color} flex items-center justify-center text-white font-bold`}>
                        {role.abbreviation}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg">{role.role}</h3>
                        <div className="grid grid-cols-2 gap-2 mt-2">
                          <div>
                            <p className="text-sm text-muted-foreground">Average Hours/Visit</p>
                            <p className="font-semibold">
                              {(Object.values(role.typical_hours).reduce((a, b) => a + b, 0) / 
                                Object.values(role.typical_hours).length).toFixed(1)}h
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Visit Types</p>
                            <p className="font-semibold">
                              {Object.keys(role.typical_hours).length}
                            </p>
                          </div>
                        </div>
                        <div className="mt-3 flex gap-2">
                          {Object.entries(role.typical_hours).map(([visit, hours]) => (
                            <Badge key={visit} variant="outline" className="text-xs">
                              {visit.split(' ')[0]}: {hours}h
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <Button variant="outline" size="sm">
                        Edit
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}







