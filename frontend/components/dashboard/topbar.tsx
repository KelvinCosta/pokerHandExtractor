"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Bell, Calendar, Search, SlidersHorizontal } from "lucide-react"

export function Topbar({ 
  title, 
  subtitle,
  searchQuery,
  onSearchChange
}: { 
  title: string
  subtitle: string
  searchQuery?: string
  onSearchChange?: (q: string | undefined) => void
}) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-md md:px-6">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-sm font-semibold tracking-tight md:text-base">{title}</h1>
          <span className="hidden items-center gap-1.5 rounded-full border border-border px-2 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline-flex">
            <span className="size-1.5 rounded-full bg-primary animate-pulse" />
            LIVE
          </span>
        </div>
        <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
      </div>

      <div className="hidden items-center gap-2 md:flex">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            placeholder="Filter hands, villains…"
            value={searchQuery ?? ""}
            onChange={(e) => onSearchChange?.(e.target.value || undefined)}
            className="h-8 w-56 rounded-md border border-input bg-card pl-8 pr-3 text-xs outline-none placeholder:text-muted-foreground focus:border-ring"
          />
        </div>

        <Select defaultValue="all">
          <SelectTrigger size="sm" className="h-8 w-[130px] text-xs">
            <span className="text-muted-foreground">Stake:</span>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="nl100">NL100</SelectItem>
            <SelectItem value="nl500">NL500</SelectItem>
            <SelectItem value="nl1000">NL1000+</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
          <Calendar className="size-3.5" />
          Last 90 days
        </Button>
      </div>

      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="size-8 md:hidden">
          <Search className="size-4" />
        </Button>
        <Button variant="ghost" size="icon" className="size-8">
          <SlidersHorizontal className="size-4" />
        </Button>
        <Button variant="ghost" size="icon" className="relative size-8">
          <Bell className="size-4" />
          <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-loss" />
        </Button>
        <Avatar className="ml-1 size-8">
          <AvatarFallback className="bg-secondary text-xs font-medium">HR</AvatarFallback>
        </Avatar>
      </div>
    </header>
  )
}
