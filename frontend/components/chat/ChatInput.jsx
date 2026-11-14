'use client';

import { useState } from 'react';
import Button from '../ui/Button';
import VoiceRecorder from './VoiceRecorder';
import { MAX_MESSAGE_CHARS } from '../../lib/api';

const EXAMPLE_TEXT =
  'Red, rough, dry patches on both cheeks and around my nose for about 3 weeks. They sting a little, and it got worse after I switched to a foaming cleanser.';

export default function ChatInput({ onSubmit, onVoiceSubmit, isLoading }) {
  const [inputVal, setInputVal] = useState('');
  const [isListening, setIsListening] = useState(false);

  const trimmed = inputVal.trim();
  const overLimit = inputVal.length > MAX_MESSAGE_CHARS;

  const submit = () => {
    if (!trimmed || isLoading || overLimit) return;
    onSubmit(trimmed);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      submit();
    }
  };

  const handleAudioReady = (blob, filename, capturedText) => {
    const finalText = (capturedText || '').slice(0, MAX_MESSAGE_CHARS);
    if (finalText) setInputVal(finalText);
    onVoiceSubmit(blob, filename, finalText);
  };

  return (
    <div className="flex flex-col gap-8 max-w-xl">
      <div className="flex flex-col gap-3">
        <h1 className="heading-display">What is your skin doing?</h1>
        <p className="text-ink-muted">
          Type or record a description. You&apos;ll get possible causes and gentle care ideas, not a diagnosis.
        </p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        <div className="flex flex-col gap-2">
          <div className="flex items-end justify-between gap-3">
            <label htmlFor="skin-concern" className="heading-card">
              Your description
            </label>
            {!inputVal && !isListening && (
              <button type="button" onClick={() => setInputVal(EXAMPLE_TEXT)} className="btn btn-text -mr-2 text-sm">
                Use an example
              </button>
            )}
          </div>
          <textarea
            id="skin-concern"
            name="concern"
            rows={7}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            aria-describedby="skin-concern-help"
            placeholder="Where is it, how long has it been there, what does it feel like, and what makes it better or worse?"
            className="field resize-y"
          />
          <div id="skin-concern-help" className="flex items-center justify-between gap-3 text-meta">
            <span>
              {isListening ? (
                'Listening. Your words appear above as you speak.'
              ) : (
                <span className="hidden sm:inline">Ctrl + Enter to analyze</span>
              )}
            </span>
            <span className={`tabular-nums ${overLimit ? 'text-danger-600 font-semibold' : ''}`}>
              {inputVal.length} / {MAX_MESSAGE_CHARS}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={isLoading || !trimmed || overLimit}>
            {isLoading ? 'Analyzing…' : 'Analyze'}
          </Button>
          <VoiceRecorder
            onAudioReady={handleAudioReady}
            onTranscriptChange={(liveText) => liveText && setInputVal(liveText)}
            onRecordingStateChange={setIsListening}
            disabled={isLoading}
          />
        </div>
      </form>
    </div>
  );
}
