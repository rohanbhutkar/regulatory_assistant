"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Bot, ChevronDown, Check } from "lucide-react"
import type { Agent } from "@/lib/types/chat-types"
import { AVAILABLE_AGENTS } from "@/lib/data/agents"

interface AgentSelectorProps {
  selectedAgents: string[]
  onAgentsChange: (agentIds: string[]) => void
  agents?: Agent[]
}

export function AgentSelector({ selectedAgents, onAgentsChange, agents: agentsProp }: AgentSelectorProps) {
  const agents = agentsProp ?? AVAILABLE_AGENTS
  const [open, setOpen] = useState(false)

  const toggleAgent = (agentId: string) => {
    if (selectedAgents.includes(agentId)) {
      onAgentsChange(selectedAgents.filter((id) => id !== agentId))
    } else {
      onAgentsChange([...selectedAgents, agentId])
    }
  }

  const selectedCount = selectedAgents.length

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="gap-2 bg-transparent">
          <Bot className="h-4 w-4" />
          <span>
            {selectedCount === 0 ? "All Agents" : selectedCount === 1 ? "1 Agent" : `${selectedCount} Agents`}
          </span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <div className="p-4 border-b border-border">
          <h4 className="font-semibold text-sm text-foreground">Select AI Agents</h4>
          <p className="text-xs text-muted-foreground mt-1">Choose which agents to use for your query</p>
        </div>
        <ScrollArea className="h-[400px]">
          <div className="p-2 space-y-1">
            {agents.map((agent) => {
              const isSelected = selectedAgents.includes(agent.id)
              return (
                <button
                  key={agent.id}
                  onClick={() => toggleAgent(agent.id)}
                  className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-secondary/50 transition-colors text-left"
                >
                  <div
                    className={`flex-shrink-0 h-5 w-5 rounded border-2 flex items-center justify-center mt-0.5 ${
                      isSelected ? "bg-primary border-primary" : "border-border"
                    }`}
                  >
                    {isSelected && <Check className="h-3 w-3 text-white" />}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">{agent.name}</span>
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          agent.status === "available"
                            ? "border-success/50 text-success"
                            : "border-muted-foreground/50 text-muted-foreground"
                        }`}
                      >
                        {agent.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{agent.description}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {agent.capabilities.slice(0, 3).map((cap) => (
                        <Badge key={cap} variant="secondary" className="text-xs">
                          {cap.replace("_", " ")}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </ScrollArea>
        <div className="p-3 border-t border-border flex justify-between">
          <Button variant="ghost" size="sm" onClick={() => onAgentsChange([])}>
            Clear All
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onAgentsChange(agents.map((a) => a.id))}>
            Select All
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
