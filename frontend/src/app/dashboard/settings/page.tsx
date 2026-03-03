export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure your Creator OS experience
        </p>
      </div>

      {/* Account */}
      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold">Account</h2>
        <div className="mt-4 space-y-4">
          <div>
            <label className="text-sm font-medium">YouTube Channel</label>
            <p className="text-sm text-muted-foreground">Not connected</p>
          </div>
        </div>
      </div>

      {/* Agent Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold">Agent Configuration</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Configure human-in-the-loop gates for each agent
        </p>
        <div className="mt-4 space-y-3">
          {[
            "Trend Scout",
            "Idea Generator",
            "Script Architect",
            "SEO Optimizer",
            "Performance Analyst",
            "Media Kit Generator",
          ].map((agent) => (
            <div key={agent} className="flex items-center justify-between rounded-lg border p-3">
              <span className="text-sm font-medium">{agent}</span>
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" />
                <span className="text-xs text-muted-foreground">Require approval</span>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* Appearance */}
      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold">Appearance</h2>
        <div className="mt-4">
          <label className="text-sm font-medium">Theme</label>
          <select className="mt-1 block w-48 rounded-md border bg-background px-3 py-2 text-sm">
            <option>System</option>
            <option>Light</option>
            <option>Dark</option>
          </select>
        </div>
      </div>
    </div>
  );
}
