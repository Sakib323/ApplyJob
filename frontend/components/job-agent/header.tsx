"use client"

import { Sparkles, Github } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface HeaderProps {
  demoMode: boolean
  onDemoModeChange: (value: boolean) => void
}

export function Header({ demoMode, onDemoModeChange }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 w-full border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/15 text-primary">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium tracking-tight">apply-agent</span>
            <Badge
              variant="secondary"
              className="hidden h-5 rounded-sm px-1.5 font-mono text-[10px] uppercase tracking-wider sm:inline-flex"
            >
              beta
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-5">
          <div className="flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5">
            <Switch
              id="demo-mode"
              checked={demoMode}
              onCheckedChange={onDemoModeChange}
              className="data-[state=checked]:bg-primary"
            />
            <Label htmlFor="demo-mode" className="cursor-pointer text-xs font-medium text-muted-foreground">
              Demo mode
            </Label>
          </div>
          <Button variant="ghost" size="sm" className="hidden h-8 gap-1.5 text-muted-foreground sm:inline-flex" asChild>
            <a href="https://github.com" target="_blank" rel="noreferrer">
              <Github className="h-3.5 w-3.5" />
              <span className="text-xs">Docs</span>
            </a>
          </Button>
        </div>
      </div>
    </header>
  )
}
