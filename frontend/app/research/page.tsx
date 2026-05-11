"use client"

import { ResearchAgentChat } from "@/components/chat/research-agent-chat"
import { Header } from "@/components/layout/header"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import { useRouter } from "next/navigation"

export default function ResearchPage() {
  const router = useRouter()

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Back Button */}
        <div className="p-4 border-b border-border/50 shrink-0">
          <Button variant="ghost" onClick={() => router.push("/")} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Personas
          </Button>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <ResearchAgentChat />
        </div>
      </div>
    </div>
  )
}
