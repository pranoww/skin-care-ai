'use client';

import { useState } from 'react';
import SplitLayout from '../components/layout/SplitLayout';
import ChatInput from '../components/chat/ChatInput';
import ChatContainer from '../components/chat/ChatContainer';
import { analyzeSkinConcern, sendVoiceMessage } from '../lib/api';

export default function Home() {
  const [userMessage, setUserMessage] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [audio, setAudio] = useState(null);
  const [spokenSummary, setSpokenSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latency, setLatency] = useState(null);

  // Text analysis submission
  const handleAnalyze = async (message) => {
    setIsLoading(true);
    setError(null);
    setAudio(null);
    setSpokenSummary(null);
    setUserMessage(message);
    const startTime = Date.now();

    try {
      const result = await analyzeSkinConcern(message);
      const elapsed = Date.now() - startTime;
      setLatency(elapsed);
      setAnalysis(result);
    } catch (err) {
      setError(err.message || 'Failed to analyze skin concern. Please check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  // Voice analysis submission
  const handleVoiceSubmit = async (audioBlob, filename, transcriptHint = '') => {
    setIsLoading(true);
    setError(null);
    setAudio(null);
    setSpokenSummary(null);
    setUserMessage(transcriptHint || 'Transcribing audio recording...');
    const startTime = Date.now();

    try {
      const result = await sendVoiceMessage(audioBlob, filename, transcriptHint);
      const elapsed = Date.now() - startTime;
      setLatency(elapsed);

      // Display transcribed text in user message box
      setUserMessage(result.transcription || 'Voice message transcribed');
      setAnalysis(result.analysis);
      setAudio(result.audio || null);
      setSpokenSummary(result.spoken_summary || null);
    } catch (err) {
      setError(err.message || 'Failed to transcribe or analyze voice recording.');
      setUserMessage('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SplitLayout
      leftPanel={
        <ChatInput
          onSubmit={handleAnalyze}
          onVoiceSubmit={handleVoiceSubmit}
          isLoading={isLoading}
          latency={latency}
        />
      }
      rightPanel={
        <ChatContainer
          userMessage={userMessage}
          timestamp="T-00:01"
          analysis={analysis}
          audio={audio}
          spokenSummary={spokenSummary}
          isLoading={isLoading}
          error={error}
          onDismissError={() => setError(null)}
        />
      }
    />
  );
}
