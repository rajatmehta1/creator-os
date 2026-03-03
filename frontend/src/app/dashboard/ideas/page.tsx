export default function IdeasPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Idea Generator</h1>
          <p className="text-muted-foreground">
            AI-generated content ideas ranked by potential
          </p>
        </div>
        <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          Generate Ideas
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-secondary p-1">
        {["All", "Approved", "Generated", "Rejected"].map((tab) => (
          <button
            key={tab}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-lg font-medium text-muted-foreground">No ideas yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Generate ideas from current trends or your content gaps
        </p>
      </div>
    </div>
  );
}
