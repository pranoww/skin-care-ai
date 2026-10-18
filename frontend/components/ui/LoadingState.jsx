'use client';

export default function LoadingState() {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-label-sm uppercase tracking-wider text-primary font-medium">
            Diagnostic Assessment
          </span>
          <span className="text-outline-variant font-label-sm">/</span>
          <span className="font-label-sm text-secondary">Processing Telemetry</span>
        </div>
        <span className="font-label-sm text-on-surface-variant flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-secondary animate-ping"></span>
          ANALYZING INQUIRY...
        </span>
      </div>

      {/* Primary Diagnosis Box Skeleton */}
      <div className="p-6 bg-surface-container-lowest border border-outline-variant rounded flex flex-col gap-3">
        <div className="h-3 w-32 bg-surface-container-highest rounded"></div>
        <div className="h-7 w-3/4 bg-surface-container-highest rounded"></div>
        <div className="h-4 w-full bg-surface-container-highest rounded"></div>
        <div className="h-4 w-5/6 bg-surface-container-highest rounded"></div>
      </div>

      {/* 2-Column Grid Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-surface-container-lowest border border-surface-container-highest rounded flex flex-col gap-3">
          <div className="h-4 w-28 bg-surface-container-highest rounded pb-2"></div>
          <div className="h-3 w-full bg-surface-container-highest rounded"></div>
          <div className="h-3 w-5/6 bg-surface-container-highest rounded"></div>
          <div className="h-3 w-4/6 bg-surface-container-highest rounded"></div>
        </div>
        <div className="p-6 bg-surface-container-lowest border border-surface-container-highest rounded flex flex-col gap-3">
          <div className="h-4 w-32 bg-surface-container-highest rounded pb-2"></div>
          <div className="h-3 w-full bg-surface-container-highest rounded"></div>
          <div className="h-3 w-5/6 bg-surface-container-highest rounded"></div>
          <div className="h-3 w-4/6 bg-surface-container-highest rounded"></div>
        </div>
      </div>

      {/* Severity & Confidence Summary Skeleton */}
      <div className="p-5 bg-surface-container-lowest border border-surface-container-highest rounded flex justify-between gap-4">
        <div className="h-8 w-1/3 bg-surface-container-highest rounded"></div>
        <div className="h-8 w-1/3 bg-surface-container-highest rounded"></div>
      </div>
    </div>
  );
}
