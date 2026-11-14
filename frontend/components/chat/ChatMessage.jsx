export default function ChatMessage({ message, via, transcriptionSource }) {
  if (!message) return null;

  let label = 'You described';
  if (via === 'voice') {
    label = transcriptionSource === 'client' ? 'You said (transcribed by your browser)' : 'You said';
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-meta">{label}</p>
      <blockquote className="panel p-5 text-ink whitespace-pre-wrap break-words">{message}</blockquote>
    </div>
  );
}
