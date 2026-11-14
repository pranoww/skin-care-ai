'use client';

import { useEffect, useRef, useState } from 'react';
import { Mic, MicOff, Square, X } from 'lucide-react';

// Long recordings exceed the backend's 2000-character limit anyway.
const MAX_RECORDING_SECONDS = 120;

function getSupportedMimeType() {
  if (typeof window === 'undefined' || !window.MediaRecorder) {
    return { mimeType: '', extension: 'webm' };
  }
  const candidates = [
    { type: 'audio/webm;codecs=opus', ext: 'webm' },
    { type: 'audio/webm', ext: 'webm' },
    { type: 'audio/mp4', ext: 'mp4' },
    { type: 'audio/ogg;codecs=opus', ext: 'ogg' },
    { type: 'audio/wav', ext: 'wav' },
  ];
  for (const candidate of candidates) {
    if (MediaRecorder.isTypeSupported(candidate.type)) {
      return { mimeType: candidate.type, extension: candidate.ext };
    }
  }
  return { mimeType: '', extension: 'webm' };
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function VoiceRecorder({ onAudioReady, onTranscriptChange, onRecordingStateChange, disabled = false }) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [permissionError, setPermissionError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const transcriptRef = useRef('');
  const isRecordingRef = useRef(false);
  // Set on cancel so the recorder's final onstop does not submit the audio.
  const cancelledRef = useRef(false);
  const secondsRef = useRef(0);

  const setRecording = (value) => {
    isRecordingRef.current = value;
    setIsRecording(value);
    if (onRecordingStateChange) onRecordingStateChange(value);
  };

  const stopTracks = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      cancelledRef.current = true;
      clearTimer();
      try {
        speechRecognitionRef.current?.abort();
      } catch {}
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      stopTracks();
    };
  }, []);

  const startSpeechRecognition = () => {
    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionClass) return;
    try {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = navigator.language || 'en-US';

      recognition.onresult = (event) => {
        let finalText = '';
        let interimText = '';
        for (let i = 0; i < event.results.length; ++i) {
          const text = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalText += `${text} `;
          else interimText += text;
        }
        const combined = (finalText + interimText).trim();
        if (combined) {
          transcriptRef.current = combined;
          if (onTranscriptChange) onTranscriptChange(combined);
        }
      };
      recognition.onerror = (event) => {
        if (event.error === 'not-allowed') {
          setPermissionError('Microphone permission for live transcription was denied.');
        }
      };
      // Browsers end recognition after silence; restart while still recording.
      recognition.onend = () => {
        if (isRecordingRef.current) {
          setTimeout(() => {
            if (isRecordingRef.current) {
              try {
                recognition.start();
              } catch {}
            }
          }, 100);
        }
      };
      recognition.start();
      speechRecognitionRef.current = recognition;
    } catch {
      // Live transcription is optional; the server can transcribe the audio instead.
    }
  };

  const startRecording = async () => {
    setPermissionError(null);
    audioChunksRef.current = [];
    transcriptRef.current = '';
    cancelledRef.current = false;
    secondsRef.current = 0;
    setDuration(0);

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setPermissionError('Recording isn’t supported in this browser. Please type your description instead.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const { mimeType, extension } = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' });
        audioChunksRef.current = [];
        stopTracks();
        if (cancelledRef.current) return;
        if (blob.size > 0 && onAudioReady) {
          onAudioReady(blob, `voice_recording.${extension}`, transcriptRef.current);
        }
      };

      startSpeechRecognition();
      recorder.start(200);
      setRecording(true);

      timerRef.current = setInterval(() => {
        secondsRef.current += 1;
        setDuration(secondsRef.current);
        if (secondsRef.current >= MAX_RECORDING_SECONDS) stopRecording();
      }, 1000);
    } catch (err) {
      setPermissionError(
        err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
          ? 'Microphone access was blocked. Allow it in your browser settings, or type instead.'
          : `Couldn’t start the microphone: ${err.message || 'unknown error'}`,
      );
      stopTracks();
      setRecording(false);
    }
  };

  const stopRecording = () => {
    if (!isRecordingRef.current) return;
    clearTimer();
    setRecording(false);
    try {
      speechRecognitionRef.current?.stop();
    } catch {}
    // Give the recorder a moment to flush the last audio chunk.
    setTimeout(() => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    }, 150);
  };

  const cancelRecording = () => {
    cancelledRef.current = true;
    clearTimer();
    setRecording(false);
    try {
      speechRecognitionRef.current?.abort();
    } catch {}
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    stopTracks();
    setDuration(0);
  };

  return (
    <div className="flex flex-col gap-2">
      {!isRecording ? (
        <button type="button" onClick={startRecording} disabled={disabled} className="btn btn-secondary">
          <Mic className="size-4 text-accent-700" aria-hidden="true" />
          Record instead
        </button>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 text-danger-700 font-semibold tabular-nums" aria-live="polite">
            <span className="size-2.5 rounded-full bg-danger-600 motion-safe:animate-pulse" aria-hidden="true" />
            Recording {formatDuration(duration)} / {formatDuration(MAX_RECORDING_SECONDS)}
          </span>
          <button type="button" onClick={stopRecording} className="btn btn-danger">
            <Square className="size-3.5 fill-current" aria-hidden="true" />
            Stop and analyze
          </button>
          <button type="button" onClick={cancelRecording} className="btn btn-text text-ink-muted">
            <X className="size-4" aria-hidden="true" />
            Cancel
          </button>
        </div>
      )}

      {permissionError && (
        <p role="alert" className="flex items-start gap-2 text-sm text-danger-700">
          <MicOff className="size-4 shrink-0 mt-0.5" aria-hidden="true" />
          {permissionError}
        </p>
      )}
    </div>
  );
}
