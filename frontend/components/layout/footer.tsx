export function Footer() {
  return (
    <footer className="border-t border-border/50 bg-card/50 mt-auto">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Local Demo - All data processed locally for optimal performance
          </p>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>Version 1.0.0</span>
            <span>•</span>
            <span>FastAPI Backend</span>
            <span>•</span>
            <span>15+ AI Agents</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
