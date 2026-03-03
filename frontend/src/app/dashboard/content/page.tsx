export default function ContentPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Content Pipeline</h1>
        <p className="text-muted-foreground">
          Track your content from idea to published
        </p>
      </div>

      {/* Kanban Columns */}
      <div className="grid grid-cols-5 gap-4">
        {["Idea", "Draft", "Review", "Optimized", "Published"].map((stage) => (
          <div key={stage} className="rounded-lg border bg-card">
            <div className="border-b p-3">
              <h3 className="text-sm font-semibold">{stage}</h3>
              <p className="text-xs text-muted-foreground">0 items</p>
            </div>
            <div className="min-h-[200px] p-3">
              <div className="flex flex-col items-center justify-center py-8">
                <p className="text-xs text-muted-foreground">No content</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
