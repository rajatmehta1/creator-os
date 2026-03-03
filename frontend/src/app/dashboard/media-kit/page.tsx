export default function MediaKitPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Media Kit</h1>
          <p className="text-muted-foreground">
            Auto-generated professional media kit for brand partnerships
          </p>
        </div>
        <div className="flex gap-2">
          <button className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent">
            Download PDF
          </button>
          <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            Generate Media Kit
          </button>
        </div>
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-lg font-medium text-muted-foreground">No media kit yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Connect your YouTube channel and generate your first media kit
        </p>
      </div>
    </div>
  );
}
