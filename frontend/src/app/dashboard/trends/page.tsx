export default function TrendsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trend Scout</h1>
          <p className="text-muted-foreground">
            Discover trending topics relevant to your niche
          </p>
        </div>
        <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          Refresh Trends
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select className="rounded-md border bg-background px-3 py-2 text-sm">
          <option>All Sources</option>
          <option>Google Trends</option>
          <option>Reddit</option>
          <option>YouTube</option>
          <option>News</option>
        </select>
        <select className="rounded-md border bg-background px-3 py-2 text-sm">
          <option>All Velocities</option>
          <option>Emerging</option>
          <option>Peaking</option>
          <option>Declining</option>
        </select>
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-lg font-medium text-muted-foreground">No trends yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Click &quot;Refresh Trends&quot; to scan for trending topics in your niche
        </p>
      </div>
    </div>
  );
}
