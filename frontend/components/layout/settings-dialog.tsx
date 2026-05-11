"use client"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { useTheme } from "@/lib/hooks/use-theme"
import { Settings, Moon, Sun } from "lucide-react"
import { useState } from "react"

export function SettingsDialog() {
  const { theme, toggleTheme, mounted } = useTheme()
  const [open, setOpen] = useState(false)

  const handleOpenChange = (newOpen: boolean) => {
    console.log("[v0] Settings dialog open state:", newOpen)
    setOpen(newOpen)
  }

  const handleThemeToggle = () => {
    console.log("[v0] Theme toggle clicked, current theme:", theme)
    toggleTheme()
  }

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className="hover:bg-secondary/80 transition-colors">
        <Settings className="h-[18px] w-[18px]" />
      </Button>
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="hover:bg-secondary/80 transition-colors"
          onClick={() => console.log("[v0] Settings button clicked")}
        >
          <Settings className="h-[18px] w-[18px]" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Customize your experience with the Clinical Knowledge Agent platform.</DialogDescription>
        </DialogHeader>
        <div className="space-y-6 py-4">
          {/* Theme Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="theme-toggle" className="text-base">
                Theme
              </Label>
              <p className="text-sm text-muted-foreground">
                {theme === "dark" ? "Dark mode is enabled" : "Light mode is enabled"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {theme === "dark" ? (
                <Moon className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Sun className="h-4 w-4 text-muted-foreground" />
              )}
              <Switch id="theme-toggle" checked={theme === "dark"} onCheckedChange={handleThemeToggle} />
            </div>
          </div>

          {/* Notifications Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="notifications-toggle" className="text-base">
                Notifications
              </Label>
              <p className="text-sm text-muted-foreground">Receive updates about your research</p>
            </div>
            <Switch id="notifications-toggle" defaultChecked />
          </div>

          {/* Auto-save Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="autosave-toggle" className="text-base">
                Auto-save
              </Label>
              <p className="text-sm text-muted-foreground">Automatically save your work</p>
            </div>
            <Switch id="autosave-toggle" defaultChecked />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
