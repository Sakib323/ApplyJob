"use client"

import { useEffect, useRef } from "react"
import { X, Maximize2, Minimize2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface TerminalProps {
  logs: string[]
  isOpen: boolean
  onClose: () => void
  isActive?: boolean
  title?: string
}

export function Terminal({ logs, isOpen, onClose, isActive = false, title = "Process Log" }: TerminalProps) {
  const contentRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight
    }
  }, [logs])

  if (!isOpen) return null

  return (
    <div
      ref={containerRef}
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center transition-all duration-200",
        isOpen ? "opacity-100" : "pointer-events-none opacity-0",
      )}
      onClick={(e) => {
        if (e.target === containerRef.current) onClose()
      }}
    >
      {/* Glow backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Terminal Container */}
      <div
        className={cn(
          "relative w-[90vw] max-w-4xl rounded-lg border shadow-2xl",
          "bg-gradient-to-b from-[#0a1a1a] to-[#051010]",
          "border-[#1a4d4d]/60",
          "overflow-hidden",
          isActive && "ring-2 ring-[#4ade80]/50",
        )}
      >
        {/* CRT scanlines effect */}
        <div
          className="pointer-events-none absolute inset-0 opacity-10"
          style={{
            backgroundImage: `repeating-linear-gradient(
              0deg,
              transparent,
              transparent 2px,
              rgba(255, 255, 255, 0.05) 2px,
              rgba(255, 255, 255, 0.05) 4px
            )`,
            zIndex: 10,
          }}
        />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1a4d4d]/60 bg-[#0a1a1a] px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-[#ef4444]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[#eab308]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[#4ade80]" />
            </div>
            <span className="font-mono text-sm text-[#4ade80] text-opacity-80">{title}</span>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 hover:bg-[#1a4d4d]/40 transition-colors text-[#4ade80] text-opacity-70 hover:text-opacity-100"
            aria-label="Close terminal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Terminal Content */}
        <div
          ref={contentRef}
          className={cn(
            "h-[60vh] max-h-[70vh] overflow-y-auto overflow-x-hidden",
            "bg-[#0a1a1a] px-4 py-3",
            "font-mono text-sm text-[#4ade80]",
            "space-y-0.5",
            "[&::-webkit-scrollbar]:w-2",
            "[&::-webkit-scrollbar-track]:bg-[#051010]",
            "[&::-webkit-scrollbar-thumb]:bg-[#1a4d4d]",
            "[&::-webkit-scrollbar-thumb]:rounded-full",
            "[&::-webkit-scrollbar-thumb]:hover:bg-[#2a6d6d]",
          )}
        >
          {logs.length === 0 ? (
            <div className="text-[#4ade80] text-opacity-50 py-8 text-center">
              <div className="animate-pulse">▌ Waiting for process to start...</div>
            </div>
          ) : (
            logs.map((log, idx) => (
              <div
                key={idx}
                className={cn(
                  "break-words text-[#4ade80]",
                  // Highlight different log types
                  log.includes("ERROR") && "text-[#ef4444] font-semibold",
                  log.includes("WARNING") && "text-[#eab308]",
                  log.includes("SUCCESS") && "text-[#4ade80] font-semibold",
                  log.includes("→") && "text-[#4ade80] text-opacity-75",
                )}
              >
                {log}
              </div>
            ))
          )}

          {/* Cursor */}
          {logs.length > 0 && (
            <div className="animate-pulse">
              <span className="text-[#4ade80]">▌</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[#1a4d4d]/60 bg-[#0a1a1a] px-4 py-2 text-xs text-[#4ade80] text-opacity-60">
          {logs.length > 0 ? `${logs.length} lines` : "Ready"}
        </div>
      </div>

      {/* Glow effect */}
      <div
        className="pointer-events-none absolute inset-0 -z-10 rounded-lg blur-2xl opacity-30"
        style={{
          background: "radial-gradient(ellipse at center, #4ade80 0%, transparent 70%)",
        }}
      />
    </div>
  )
}
