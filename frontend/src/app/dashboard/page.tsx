export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to Creator OS. Your AI-powered content command center.
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <OverviewCard title="Trending Topics" value="--" subtitle="Refresh to discover" />
        <OverviewCard title="Ideas Generated" value="0" subtitle="Generate your first ideas" />
        <OverviewCard title="Scripts Ready" value="0" subtitle="Start creating" />
        <OverviewCard title="Content Published" value="0" subtitle="Connect YouTube first" />
      </div>

      {/* Agent Status */}
      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold">Agent Status</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          {[
            "Trend Scout",
            "Idea Generator",
            "Script Architect",
            "SEO Optimizer",
            "Performance Analyst",
            "Media Kit",
          ].map((agent) => (
            <div key={agent} className="rounded-lg border p-3">
              <p className="text-sm font-medium">{agent}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-gray-400" />
                <span className="text-xs text-muted-foreground">Idle</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold">Quick Actions</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <QuickAction label="Scan Trends" description="Run Trend Scout" />
          <QuickAction label="Generate Ideas" description="Run Idea Generator" />
          <QuickAction label="Full Pipeline" description="Trend to SEO-optimized script" />
          <QuickAction label="Build DNA" description="Analyze your content style" />
        </div>
      </div>
    </div>
  );
}

function OverviewCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string;
  subtitle: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
    </div>
  );
}

function QuickAction({
  label,
  description,
}: {
  label: string;
  description: string;
}) {
  return (
    <button className="flex flex-col items-start rounded-lg border bg-background p-4 text-left transition-colors hover:bg-accent">
      <span className="text-sm font-medium">{label}</span>
      <span className="text-xs text-muted-foreground">{description}</span>
    </button>
  );
}
