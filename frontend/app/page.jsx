'use client';

import { useState } from 'react';
import SplitLayout from '../components/layout/SplitLayout';
import ChatInput from '../components/chat/ChatInput';
import ChatContainer from '../components/chat/ChatContainer';
import { analyzeSkinConcern, sendVoiceMessage } from '../lib/api';

const EMPTY_RESULT = {
  id: 0,
  userMessage: '',
  via: null, // 'text' | 'voice'
  transcriptionSource: null,
  analysis: null,
  audio: null,
  audioError: null,
  spokenSummary: null,
};

export default function Home() {
  const [result, setResult] = useState(EMPTY_RESULT);
  const [pendingMessage, setPendingMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = async (pendingText, task) => {
    setIsLoading(true);
    setError(null);
    setPendingMessage(pendingText);
    try {
      const next = await task();
      setResult((prev) => ({ ...EMPTY_RESULT, ...next, id: prev.id + 1 }));
      // On stacked (mobile) layouts the result renders below the form; bring it into view.
      if (window.matchMedia('(max-width: 1023px)').matches) {
        requestAnimationFrame(() => document.getElementById('analysis')?.scrollIntoView({ block: 'start' }));
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
      setPendingMessage('');
    }
  };

  const handleAnalyze = (message) =>
    run(message, async () => {
      const analysis = await analyzeSkinConcern(message);
      return { userMessage: message, via: 'text', analysis };
    });

  const handleVoiceSubmit = (audioBlob, filename, transcriptHint = '') =>
    run(transcriptHint || 'Transcribing your recording…', async () => {
      const data = await sendVoiceMessage(audioBlob, filename, transcriptHint);
      return {
        userMessage: data.transcription,
        via: 'voice',
        transcriptionSource: data.transcription_source || null,
        analysis: data.analysis,
        audio: data.audio || null,
        audioError: data.audio_error || null,
        spokenSummary: data.spoken_summary || null,
      };
    });

  return (
    <SplitLayout
      leftPanel={<ChatInput onSubmit={handleAnalyze} onVoiceSubmit={handleVoiceSubmit} isLoading={isLoading} />}
      rightPanel={
        <ChatContainer
          result={result}
          pendingMessage={pendingMessage}
          isLoading={isLoading}
          error={error}
          onDismissError={() => setError(null)}
        />
      }
    />
  );
}
