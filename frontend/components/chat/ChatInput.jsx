'use client';

import { useState } from 'react';
import Button from '../ui/Button';
import VoiceRecorder from './VoiceRecorder';

const SAMPLE_TEXT =
  'Persistent redness, mild stinging, and rough dry patches across both cheeks and around the nasal folds for the past 3 weeks, aggravated after using a foaming cleanser.';

export default function ChatInput({ onSubmit, onVoiceSubmit, isLoading, latency }) {
  const [inputVal, setInputVal] = useState('');
  const [isLiveListening, setIsLiveListening] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputVal.trim() || isLoading) return;
    onSubmit(inputVal.trim());
  };

  const handleKeyDown = (e) => {
    // Submit on Ctrl+Enter or Cmd+Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit(e);
    }
  };

  const handleUseSample = () => {
    setInputVal(SAMPLE_TEXT);
  };

  const handleAudioReady = (blob, filename, capturedText) => {
    const finalQuery = capturedText || inputVal;
    if (finalQuery) {
      setInputVal(finalQuery);
    }
    if (onVoiceSubmit) {
      onVoiceSubmit(blob, filename, finalQuery);
    }
  };

  return (
    <>
      <div className="flex flex-col max-w-xl">
        <div className="mb-8">
          <span className="font-label-sm uppercase tracking-wider text-secondary block mb-2 font-medium">
            Diagnostic Consultation
          </span>
          <h1 className="font-headline-lg text-on-surface font-medium tracking-tight">
            Skin Care AI
          </h1>
          <p className="font-body-md text-on-surface-variant mt-2 max-w-md">
            Describe your skin concern or speak into your microphone to analyze symptoms.
          </p>
        </div>

        <form className="flex flex-col gap-5" id="skin-query-form" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <label
                  className="font-label-md uppercase tracking-wider text-on-surface-variant font-medium"
                  htmlFor="skin-inquiry-input"
                >
                  Clinical Description
                </label>
                {isLiveListening && (
                  <span className="flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-mono uppercase tracking-wider bg-error/15 text-error border border-error/30 rounded-full font-semibold animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                    Live Dictation
                  </span>
                )}
              </div>
              {!inputVal && !isLiveListening && (
                <button
                  type="button"
                  onClick={handleUseSample}
                  className="font-label-sm text-secondary hover:text-primary transition-colors cursor-pointer select-none underline-offset-2 hover:underline"
                >
                  Use sample text
                </button>
              )}
            </div>
            <textarea
              id="skin-inquiry-input"
              name="concern"
              rows={8}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Speak using 'Voice Record' or type here: e.g. Persistent redness, mild stinging, and rough dry patches across both cheeks..."
              className={`w-full bg-surface-container-lowest text-on-surface font-body-md p-4 rounded border transition-all duration-150 resize-y placeholder:text-outline/50 placeholder:italic leading-relaxed disabled:opacity-60 ${
                isLiveListening
                  ? 'border-primary ring-2 ring-primary/20 bg-surface-container/30'
                  : 'border-outline-variant focus:border-primary-container focus:outline-none'
              }`}
            />
          </div>

          <div className="pt-1 flex flex-wrap items-center gap-3">
            <Button
              type="submit"
              disabled={isLoading || !inputVal.trim()}
              id="submit-btn"
            >
              {isLoading ? 'Analyzing...' : 'Analyze'}
            </Button>
            <VoiceRecorder
              onAudioReady={handleAudioReady}
              onTranscriptChange={(liveText) => {
                if (liveText) {
                  setInputVal(liveText);
                }
              }}
              onRecordingStateChange={setIsLiveListening}
              disabled={isLoading}
              isProcessing={isLoading}
            />
          </div>
        </form>
      </div>

      <div className="mt-12 pt-6 border-t border-surface-container-highest flex items-center justify-between text-on-surface-variant font-label-sm">
        <span>SESSION PROTOCOL: DERM-8492</span>
        <span>LATENCY: {latency ? `${latency}MS` : 'STANDBY'}</span>
      </div>
    </>
  );
}
