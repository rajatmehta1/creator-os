export default function SEOPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">SEO Optimizer</h1>
        <p className="text-muted-foreground">
          Algorithm-optimized metadata for maximum visibility
        </p>
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-lg font-medium text-muted-foreground">No SEO packages yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Generate a script first, then optimize it for search
        </p>
      </div>
    </div>
  );
}
