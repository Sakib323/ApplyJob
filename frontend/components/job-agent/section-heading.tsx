interface SectionHeadingProps {
  step: number
  id?: string
  title: string
  description: string
  trailing?: React.ReactNode
}

export function SectionHeading({ step, id, title, description, trailing }: SectionHeadingProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-border bg-card font-mono text-[11px] text-muted-foreground">
          {String(step).padStart(2, "0")}
        </div>
        <div>
          <h2 id={id} className="text-base font-semibold tracking-tight text-balance">
            {title}
          </h2>
          <p className="mt-0.5 text-sm text-muted-foreground text-pretty">{description}</p>
        </div>
      </div>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </div>
  )
}
