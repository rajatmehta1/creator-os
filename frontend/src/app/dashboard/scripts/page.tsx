export default function ScriptsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Script Architect</h1>
          <p className="text-muted-foreground">
            Production-ready scripts in your authentic voice
          </p>
        </div>
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-lg font-medium text-muted-foreground">No scripts yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Approve an idea to generate a script with the Script Architect
        </p>
      </div>
    </div>
  );
}
