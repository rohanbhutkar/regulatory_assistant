"use client"

import { Button } from "@/components/ui/button"
import { Bell, FlaskConical, User } from "lucide-react"
import Link from "next/link"
import { SettingsDialog } from "./settings-dialog"

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="h-10 w-10 rounded-xl !bg-white flex items-center justify-center shadow-md group-hover:shadow-lg transition-all duration-300 group-hover:scale-105 border border-border/20">
            <FlaskConical
              className="h-7 w-7 text-primary"
              strokeWidth={2}
              aria-hidden
            />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold text-foreground group-hover:text-primary transition-colors duration-200 tracking-tight">
              Clinical Knowledge Agent
            </span>
            <span className="text-[11px] text-muted-foreground font-medium tracking-wide">
              AI-Powered Research Platform
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="relative hover:bg-secondary/80 transition-colors">
            <Bell className="h-[18px] w-[18px]" />
            <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-accent shadow-sm shadow-accent/50" />
          </Button>
          <SettingsDialog />
          <Button variant="ghost" size="icon" className="hover:bg-secondary/80 transition-colors">
            <User className="h-[18px] w-[18px]" />
          </Button>
        </div>
      </div>
    </header>
  )
}
