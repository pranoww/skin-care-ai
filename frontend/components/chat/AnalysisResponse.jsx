'use client';

import { useState, useRef, useEffect } from 'react';

export default function AnalysisResponse({ analysis, audio: propAudio, spokenSummary }) {
  if (!analysis) return null;

  const {
    skin_concern = 'Undetermined Skin Concern',
    summary = 'No clinical summary available.',
    possible_factors = [],
    recommendations = [],
    severity = 'low',
    confidence = 0.75,
    professional_advice = false,
  } = analysis;

  const audio = propAudio || analysis.audio;
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  // Stop playback if analysis or audio changes or component unmounts
  useEffect(() => {
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, [analysis, audio]);

  const toggleAudio = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => {
          setIsPlaying(true);
        })
        .catch((e) => {
          console.error('[AnalysisResponse] Gemini audio playback error:', e);
          setIsPlaying(false);
        });
    }
  };

  // Format confidence percentage
  const confidencePercent = Math.round(confidence * 100);
  const confidenceLabel =
    confidence >= 0.8 ? `HIGH (${confidencePercent}%)` :
    confidence >= 0.6 ? `MODERATE (${confidencePercent}%)` :
    `LOW (${confidencePercent}%)`;

  // Format severity
  const severityDisplay = {
    low: 'Low (Mild Epidermal Disturbance)',
    medium: 'Moderate (Noticeable Cutaneous Irritation)',
    high: 'High (Severe or Inflammatory Presentation)',
    unknown: 'Unspecified / Observation Advised',
  }[severity.toLowerCase()] || severity;

  const certaintyDisplay = `${confidencePercent}% (Based on reported symptom clustering)`;

  // Professional advice text
  const adviceText = professional_advice
    ? 'Based on the reported symptoms, an in-person clinical evaluation by a board-certified dermatologist or qualified healthcare provider is strongly recommended.'
    : 'If symptoms persist, worsen beyond 7–10 days of conservative barrier care, or if unusual pain, swelling, or infection develops, consult a board-certified dermatologist.';

  return (
    <div className="flex flex-col gap-6" id="ai-response-container">
      {/* Response Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-label-sm uppercase tracking-wider text-primary font-medium">
            Diagnostic Assessment
          </span>
          <span className="text-outline-variant font-label-sm">/</span>
          <span className="font-label-sm text-secondary">Verified Evaluation</span>
        </div>
        <span className="font-label-sm text-on-surface-variant">
          CLINICAL CONFIDENCE: {confidenceLabel}
        </span>
      </div>

      {/* Gemini TTS Audio Player Bar */}
      {audio && (
        <div className={`p-4 rounded border transition-colors ${isPlaying ? 'bg-surface-container-high border-primary' : 'bg-surface-container border-outline-variant'} flex flex-col sm:flex-row sm:items-center justify-between gap-4`}>
          <div className="flex items-center gap-3">
            <button
              type="button"
              id="voice-playback-btn"
              onClick={toggleAudio}
              className={`w-11 h-11 rounded-full flex items-center justify-center transition-all cursor-pointer select-none shrink-0 shadow-sm ${
                isPlaying
                  ? 'bg-primary text-on-primary ring-4 ring-primary/20'
                  : 'bg-primary-container text-on-primary hover:bg-primary'
              }`}
              aria-label={isPlaying ? 'Pause voice response' : 'Play voice response'}
            >
              <span className="material-symbols-outlined text-[22px]">
                {isPlaying ? 'pause' : 'volume_up'}
              </span>
            </button>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-label-sm uppercase tracking-wider text-secondary font-medium">
                  AI Voice Consultation (Gemini TTS)
                </span>
                {isPlaying && (
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-3 bg-primary rounded-full animate-pulse"></span>
                    <span className="w-1.5 h-4 bg-primary rounded-full animate-pulse delay-75"></span>
                    <span className="w-1.5 h-2 bg-primary rounded-full animate-pulse delay-150"></span>
                  </span>
                )}
              </div>
              <span className="font-body-sm text-on-surface">
                {isPlaying ? 'Playing spoken assessment...' : 'Click to listen to AI spoken assessment'}
              </span>
            </div>
          </div>
          <audio
            ref={audioRef}
            src={audio}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            onError={(e) => {
              console.error('Audio element error:', e);
              setIsPlaying(false);
            }}
            className="hidden"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleAudio}
              className={`px-4 py-2 text-xs font-semibold font-label-sm uppercase tracking-wider rounded transition-colors select-none cursor-pointer ${
                isPlaying
                  ? 'bg-primary text-on-primary'
                  : 'border border-primary/40 text-primary hover:bg-primary-container/20'
              }`}
            >
              {isPlaying ? 'Pause' : 'Play Audio'}
            </button>
          </div>
        </div>
      )}

      {/* Primary Diagnosis Box */}
      <div className="p-6 bg-surface-container-lowest border border-outline-variant rounded flex flex-col gap-3">
        <span className="font-label-sm uppercase tracking-wider text-secondary font-medium">
          Identified Condition
        </span>
        <h3 className="font-headline-md text-on-surface font-medium leading-snug">
          {skin_concern}
        </h3>
        <p className="font-body-md text-on-surface-variant leading-relaxed">
          {summary}
        </p>
      </div>

      {/* 2-Column Factors & Recommendations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Possible Contributing Factors */}
        <div className="p-6 bg-surface-container-lowest border border-surface-container-highest rounded flex flex-col justify-between">
          <div>
            <h4 className="font-label-md uppercase tracking-wider text-on-surface font-medium mb-4 pb-2 border-b border-surface-container-highest">
              Possible Factors
            </h4>
            {possible_factors.length > 0 ? (
              <ul className="flex flex-col gap-3 font-body-sm text-on-surface-variant leading-relaxed">
                {possible_factors.map((factor, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-secondary select-none font-medium">•</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="font-body-sm text-outline italic">No specific factors identified.</p>
            )}
          </div>
        </div>

        {/* Actionable Recommendations */}
        <div className="p-6 bg-surface-container-lowest border border-surface-container-highest rounded flex flex-col justify-between">
          <div>
            <h4 className="font-label-md uppercase tracking-wider text-on-surface font-medium mb-4 pb-2 border-b border-surface-container-highest">
              Recommendations
            </h4>
            {recommendations.length > 0 ? (
              <ul className="flex flex-col gap-3 font-body-sm text-on-surface-variant leading-relaxed">
                {recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-secondary select-none font-medium">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="font-body-sm text-outline italic">Standard gentle barrier care recommended.</p>
            )}
          </div>
        </div>
      </div>

      {/* Severity & Diagnostic Certainty Bar */}
      <div className="p-5 bg-surface-container-lowest border border-surface-container-highest rounded flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="font-label-sm uppercase tracking-wider text-secondary">
            Severity Grading
          </span>
          <span className="font-body-md text-on-surface font-medium">
            {severityDisplay}
          </span>
        </div>
        <div className="h-8 w-px bg-surface-container-highest hidden sm:block"></div>
        <div className="flex flex-col gap-1 sm:text-right">
          <span className="font-label-sm uppercase tracking-wider text-secondary">
            Diagnostic Certainty
          </span>
          <span className="font-body-md text-on-surface font-medium">
            {certaintyDisplay}
          </span>
        </div>
      </div>

      {/* Professional Advice Callout */}
      <div className={`p-6 bg-surface-container rounded border-l-2 ${professional_advice ? 'border-error' : 'border-primary-container'} flex flex-col gap-2`}>
        <span className={`font-label-sm uppercase tracking-wider ${professional_advice ? 'text-error font-semibold' : 'text-primary font-medium'}`}>
          {professional_advice ? 'Professional Medical Evaluation Recommended' : 'Professional Consultation Protocol'}
        </span>
        <p className="font-body-md text-on-surface-variant leading-relaxed">
          {adviceText}
        </p>
      </div>
    </div>
  );
}
