'use client';

import ChatMessage from './ChatMessage';
import AnalysisResponse from './AnalysisResponse';
import LoadingState from '../ui/LoadingState';

export default function ChatContainer({
  userMessage,
  timestamp,
  analysis,
  audio,
  spokenSummary,
  isLoading,
  error,
  onDismissError,
}) {
  return (
    <div className="p-8 sm:p-10 lg:p-12 flex flex-col max-w-3xl">
      {/* Section Header */}
      <div className="pb-6 border-b border-surface-container-highest mb-8 flex items-center justify-between">
        <div>
          <h2 className="font-headline-md text-on-surface font-medium">AI Analysis</h2>
          <p className="font-label-sm uppercase tracking-wider text-secondary mt-1">
            Algorithmic Triage &amp; Assessment
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-surface-container rounded border border-surface-container-highest">
          <span className={`w-1.5 h-1.5 rounded-full ${isLoading ? 'bg-secondary animate-ping' : 'bg-primary-container'}`}></span>
          <span className="font-label-sm uppercase tracking-wider text-on-surface-variant">
            {isLoading ? 'Analyzing Telemetry' : 'Model Synchronized'}
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 bg-error-container border border-error rounded flex items-start justify-between gap-3 text-on-error-container">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[20px] text-error mt-0.5">error</span>
            <div className="flex flex-col">
              <span className="font-label-sm uppercase font-semibold text-error">Analysis Error</span>
              <p className="font-body-sm text-on-surface">{error}</p>
            </div>
          </div>
          {onDismissError && (
            <button
              onClick={onDismissError}
              className="text-on-error-container hover:text-error text-sm font-semibold select-none p-1"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Chat-Style Flow */}
      <div className="flex flex-col gap-8">
        {/* User Submission Message */}
        {userMessage && (
          <ChatMessage message={userMessage} timestamp={timestamp} />
        )}

        {/* Vertical Separation */}
        {(userMessage || analysis || isLoading) && (
          <div className="w-full border-t border-surface-container-highest"></div>
        )}

        {/* Loading State or AI Analysis */}
        {isLoading ? (
          <LoadingState />
        ) : analysis ? (
          <AnalysisResponse
            analysis={analysis}
            audio={audio}
            spokenSummary={spokenSummary}
          />
        ) : (
          <div className="p-8 sm:p-12 text-center bg-surface-container-lowest border border-dashed border-outline-variant rounded flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-secondary">
              <span className="material-symbols-outlined text-[22px]">clinical_notes</span>
            </div>
            <div className="flex flex-col gap-1 max-w-md">
              <span className="font-label-md uppercase tracking-wider text-on-surface font-medium">
                Awaiting Clinical Description
              </span>
              <p className="font-body-sm text-on-surface-variant leading-relaxed">
                Describe your skin concern in the consultation panel on the left and select <strong className="text-primary font-medium">Analyze</strong> to generate an AI diagnostic evaluation, possible contributing factors, and recommendations.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
