'use client';

export default function ChatMessage({ message, timestamp = 'T-00:01' }) {
  if (!message) return null;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="font-label-sm uppercase tracking-wider text-on-surface-variant font-medium">
          Submitted Inquiry
        </span>
        <span className="text-outline-variant font-label-sm">/</span>
        <span className="font-label-sm text-outline">{timestamp}</span>
      </div>
      <div className="p-5 bg-surface-container-lowest border border-surface-container-highest rounded text-on-surface font-body-md leading-relaxed">
        <p>{message}</p>
      </div>
    </div>
  );
}
