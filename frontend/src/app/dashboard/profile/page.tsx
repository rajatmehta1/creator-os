export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Creator DNA Profile</h1>
          <p className="text-muted-foreground">
            Your unique voice fingerprint powers all AI-generated content
          </p>
        </div>
        <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          Build DNA Fingerprint
        </button>
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-lg font-medium text-muted-foreground">DNA not yet analyzed</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Click &quot;Build DNA Fingerprint&quot; to analyze your content style from your last 50 videos
        </p>
      </div>
    </div>
  );
}
