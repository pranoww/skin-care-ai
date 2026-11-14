'use client';

import { useEffect, useRef, useState } from 'react';
import { Pause, Stethoscope, Volume2 } from 'lucide-react';

const SEVERITY = {
  low: {
    label: 'Low',
    detail: 'Sounds mild. Gentle home care is usually a reasonable first step.',
    tone: 'bg-accent-50 text-accent-800 border-accent-100',
  },
  medium: {
    label: 'Moderate',
    detail: 'Worth watching closely. See a professional if it lasts or gets worse.',
    tone: 'bg-caution-50 text-caution-700 border-caution-700/30',
  },
  high: {
    label: 'High',
    detail: 'Please get this looked at by a dermatologist or doctor soon.',
    tone: 'bg-danger-50 text-danger-700 border-danger-600/40',
  },
  unknown: {
    label: 'Unclear',
    detail: 'The description doesn’t give enough detail to judge how serious this is.',
    tone: 'bg-panel text-ink-muted border-line-strong',
  },
};

function confidenceWording(confidence) {
  if (confidence >= 0.8) return 'fairly confident';
  if (confidence >= 0.6) return 'moderately confident';
  return 'not very confident';
}

/** Plays server audio when present, otherwise reads the summary with the browser's free voice. */
function ListenControl({ audio, audioError, spokenSummary }) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [canSpeak] = useState(() => typeof window !== 'undefined' && 'speechSynthesis' in window);

  useEffect(() => {
    const element = audioRef.current;
    return () => {
      if (element) element.pause();
      if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  const useBrowserVoice = !audio && canSpeak && Boolean(spokenSummary);
  if (!audio && !useBrowserVoice) return null;

  const toggle = () => {
    if (audio) {
      const element = audioRef.current;
      if (!element) return;
      if (isPlaying) element.pause();
      else element.play().catch(() => setIsPlaying(false));
      return;
    }
    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(spokenSummary);
    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  };

  return (
    <div className="panel-muted p-4 flex flex-col sm:flex-row sm:items-center gap-3">
      <button type="button" onClick={toggle} className="btn btn-secondary self-start" aria-pressed={isPlaying}>
        {isPlaying ? <Pause className="size-4" aria-hidden="true" /> : <Volume2 className="size-4" aria-hidden="true" />}
        {isPlaying ? 'Pause' : 'Listen to summary'}
      </button>
      <p className="text-meta">
        {audio
          ? 'A short spoken version of this analysis.'
          : `Using your browser's built-in voice${audioError ? ` because server audio isn't available (${audioError})` : ''}.`}
      </p>
      {audio && (
        <audio
          ref={audioRef}
          src={audio}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          onError={() => setIsPlaying(false)}
          className="hidden"
        />
      )}
    </div>
  );
}

function ListCard({ title, items, empty }) {
  return (
    <div className="panel p-5 sm:p-6">
      <h4 className="heading-card mb-3">{title}</h4>
      {items.length > 0 ? (
        <ul className="bullet-list">
          {items.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="text-meta">{empty}</p>
      )}
    </div>
  );
}

export default function AnalysisResponse({ analysis, audio, audioError, spokenSummary }) {
  const {
    skin_concern: concern = 'Unclear concern',
    summary = '',
    possible_factors: factors = [],
    recommendations = [],
    severity = 'unknown',
    confidence = 0,
    professional_advice: seeProfessional = false,
  } = analysis;

  const severityInfo = SEVERITY[String(severity).toLowerCase()] || SEVERITY.unknown;
  const confidencePercent = Math.round(Number(confidence) * 100);

  return (
    <article className="flex flex-col gap-5">
      <ListenControl audio={audio} audioError={audioError} spokenSummary={spokenSummary} />

      <div className="panel p-5 sm:p-6 flex flex-col gap-3">
        <p className="text-meta">Possible concern</p>
        <h3 className="heading-section">{concern}</h3>
        {summary && <p className="text-ink-muted">{summary}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <ListCard title="What might be contributing" items={factors} empty="No specific factors stood out." />
        <ListCard
          title="Gentle care to try"
          items={recommendations}
          empty="Keep to a simple routine: mild cleanser, fragrance-free moisturizer, daily sunscreen."
        />
      </div>

      <div className="panel p-5 sm:p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div className="flex flex-col gap-2">
          <p className="text-meta">How serious it sounds</p>
          <span className={`self-start px-2.5 py-1 rounded-[var(--radius-ui)] border text-sm font-semibold ${severityInfo.tone}`}>
            {severityInfo.label}
          </span>
          <p className="text-ink-muted text-[0.9375rem]">{severityInfo.detail}</p>
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-meta">How sure the AI is</p>
          <p className="text-2xl font-semibold tabular-nums text-ink">{confidencePercent}%</p>
          <p className="text-ink-muted text-[0.9375rem]">
            The AI is {confidenceWording(Number(confidence))}, based only on your description.
          </p>
        </div>
      </div>

      <div
        className={`p-5 sm:p-6 rounded-[var(--radius-ui)] border flex items-start gap-3 ${
          seeProfessional ? 'bg-danger-50 border-danger-600/40' : 'bg-panel border-line'
        }`}
      >
        <Stethoscope
          className={`size-5 shrink-0 mt-0.5 ${seeProfessional ? 'text-danger-600' : 'text-accent-700'}`}
          aria-hidden="true"
        />
        <div>
          <p className={`font-semibold ${seeProfessional ? 'text-danger-700' : 'text-ink'}`}>
            {seeProfessional ? 'See a dermatologist or doctor' : 'When to see a professional'}
          </p>
          <p className="text-ink-muted mt-1">
            {seeProfessional
              ? 'Based on what you described, an in-person check is recommended. Text alone can’t confirm what’s going on.'
              : 'If this lasts beyond one to two weeks of gentle care, gets worse, or becomes painful, swollen or infected-looking, book a visit with a dermatologist.'}
          </p>
        </div>
      </div>
    </article>
  );
}
