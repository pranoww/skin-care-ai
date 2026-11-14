import { CircleAlert, X } from 'lucide-react';
import ChatMessage from './ChatMessage';
import AnalysisResponse from './AnalysisResponse';
import LoadingState from '../ui/LoadingState';

export default function ChatContainer({ result, pendingMessage, isLoading, error, onDismissError }) {
  const shownMessage = isLoading ? pendingMessage : result.userMessage;

  return (
    <div className="flex flex-col gap-8 max-w-3xl" aria-live="polite" aria-busy={isLoading}>
      <h2 id="analysis" className="heading-section scroll-mt-4">Analysis</h2>

      {error && (
        <div role="alert" className="flex items-start justify-between gap-3 p-4 rounded-[var(--radius-ui)] border border-danger-600 bg-danger-50">
          <div className="flex items-start gap-3">
            <CircleAlert className="size-5 shrink-0 mt-0.5 text-danger-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-danger-700">That didn&apos;t work</p>
              <p className="text-ink">{error}</p>
            </div>
          </div>
          <button type="button" onClick={onDismissError} className="btn btn-text text-ink-muted" aria-label="Dismiss error">
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      )}

      {shownMessage && (
        <ChatMessage
          message={shownMessage}
          via={isLoading ? null : result.via}
          transcriptionSource={isLoading ? null : result.transcriptionSource}
        />
      )}

      {isLoading ? (
        <LoadingState />
      ) : result.analysis ? (
        <AnalysisResponse
          key={result.id}
          analysis={result.analysis}
          audio={result.audio}
          audioError={result.audioError}
          spokenSummary={result.spokenSummary}
        />
      ) : (
        <div className="panel-muted p-6 sm:p-8">
          <p className="heading-card">Your analysis will appear here</p>
          <p className="mt-2 text-ink-muted">
            Describe what you&apos;re noticing: where it is, how long it has lasted, what it feels like and
            anything that seems to trigger it. You&apos;ll get possible causes, gentle care suggestions and a
            note on whether to see a dermatologist.
          </p>
        </div>
      )}
    </div>
  );
}
