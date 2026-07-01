export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-gray-500 py-16 justify-center">
      <span className="h-4 w-4 rounded-full border-2 border-f1-red border-t-transparent animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-900/50 bg-red-950/30 text-red-300 text-sm px-4 py-3">
      Failed to load data: {message}. Run <code className="text-red-200">f1dataset demo</code> from the repo root to
      generate the dashboard dataset.
    </div>
  )
}
