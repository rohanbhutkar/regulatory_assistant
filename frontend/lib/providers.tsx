"use client"

import { ActivityProvider } from './contexts/activity-context'
import { GlobalActivityPanel } from '@/components/activity/global-activity-panel'
import { LogsViewer } from '@/components/activity/logs-viewer'
import { Toaster } from "sonner"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ActivityProvider>
      {children}
      <GlobalActivityPanel />
      <LogsViewer />
      <Toaster richColors position="top-right" />
    </ActivityProvider>
  )
}
