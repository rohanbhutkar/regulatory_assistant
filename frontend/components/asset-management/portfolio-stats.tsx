"use client"

import { Card, CardContent } from "@/components/ui/card"
import type { PortfolioStats } from "@/lib/types/asset-types"
import { TrendingUp, Beaker, DollarSign, AlertTriangle } from "lucide-react"

interface PortfolioStatsProps {
  stats: PortfolioStats
}

export function PortfolioStatsCards({ stats }: PortfolioStatsProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)
  }

  const statCards = [
    {
      title: "Total Portfolio Investment",
      value: formatCurrency(stats.totalInvestment),
      icon: DollarSign,
      iconColor: "text-blue-600 dark:text-blue-400",
      iconBg: "bg-blue-50 dark:bg-blue-950/30",
      change: "+12.5%",
      changeType: "positive" as const,
    },
    {
      title: "Projected Revenue",
      value: formatCurrency(stats.projectedRevenue),
      icon: TrendingUp,
      iconColor: "text-emerald-600 dark:text-emerald-400",
      iconBg: "bg-emerald-50 dark:bg-emerald-950/30",
      change: "+18.2%",
      changeType: "positive" as const,
    },
    {
      title: "Active Trials",
      value: stats.activeTrials.toString(),
      icon: Beaker,
      iconColor: "text-cyan-600 dark:text-cyan-400",
      iconBg: "bg-cyan-50 dark:bg-cyan-950/30",
      change: "+3 this quarter",
      changeType: "neutral" as const,
    },
    {
      title: "High Risk Assets",
      value: stats.highRiskAssets.toString(),
      icon: AlertTriangle,
      iconColor: "text-orange-600 dark:text-orange-400",
      iconBg: "bg-orange-50 dark:bg-orange-950/30",
      change: "Requires attention",
      changeType: "warning" as const,
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((stat) => {
        const Icon = stat.icon
        return (
          <Card key={stat.title} className="border-border/40 bg-card hover:border-border transition-colors">
            <CardContent className="p-6">
              <div className="flex items-start justify-between mb-6">
                <div className={`p-2.5 rounded-lg ${stat.iconBg}`}>
                  <Icon className={`h-5 w-5 ${stat.iconColor}`} />
                </div>
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                <p className="text-3xl font-semibold tracking-tight text-foreground" suppressHydrationWarning>
                  {stat.value}
                </p>
                <p
                  className={`text-sm ${
                    stat.changeType === "positive"
                      ? "text-emerald-600 dark:text-emerald-400"
                      : stat.changeType === "warning"
                        ? "text-orange-600 dark:text-orange-400"
                        : "text-muted-foreground"
                  }`}
                >
                  {stat.change}
                </p>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
