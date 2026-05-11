"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { SensitivityResult } from "@/lib/types/commercial-types"
import { TrendingUp, TrendingDown } from "lucide-react"

interface SensitivityAnalysisProps {
  results: SensitivityResult[]
}

export function SensitivityAnalysis({ results }: SensitivityAnalysisProps) {
  const formatValue = (value: number, parameter: string) => {
    if (parameter.includes("Price")) {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        notation: "compact",
      }).format(value)
    }
    return `${value}%`
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-lg">Sensitivity Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="bg-secondary/50 hover:bg-secondary/50">
              <TableHead>Parameter</TableHead>
              <TableHead className="text-right">Low Case</TableHead>
              <TableHead className="text-right">Base Case</TableHead>
              <TableHead className="text-right">High Case</TableHead>
              <TableHead className="text-right">Revenue Impact</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((result) => (
              <TableRow key={result.parameter}>
                <TableCell className="font-medium text-foreground">{result.parameter}</TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {formatValue(result.lowCase, result.parameter)}
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">
                  {formatValue(result.baseCase, result.parameter)}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {formatValue(result.highCase, result.parameter)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    {result.impact > 0 ? (
                      <TrendingUp className="h-4 w-4 text-success" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-destructive" />
                    )}
                    <span className="font-semibold">{Math.abs(result.impact)}%</span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
