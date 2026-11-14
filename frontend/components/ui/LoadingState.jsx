function Bar({ className }) {
  return <div className={`h-3 rounded bg-line ${className}`} />;
}

export default function LoadingState() {
  return (
    <div className="flex flex-col gap-4" role="status">
      <p className="text-meta">Analyzing your description…</p>
      <div className="flex flex-col gap-4 motion-safe:animate-pulse" aria-hidden="true">
        <div className="panel p-6 flex flex-col gap-3">
          <Bar className="w-28" />
          <Bar className="h-6 w-3/4" />
          <Bar className="w-full" />
          <Bar className="w-5/6" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map((i) => (
            <div key={i} className="panel p-6 flex flex-col gap-3">
              <Bar className="w-32" />
              <Bar className="w-full" />
              <Bar className="w-5/6" />
              <Bar className="w-4/6" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
