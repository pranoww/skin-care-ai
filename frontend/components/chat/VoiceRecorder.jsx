'use client';

import { useState, useRef, useEffect } from 'react';

/**
 * Detects browser-supported audio mime type for MediaRecorder.
 */
function getSupportedMimeType() {
  if (typeof window === 'undefined' || !window.MediaRecorder) {
    return { mimeType: '', extension: 'webm' };
  }
  const candidateTypes = [
    { type: 'audio/webm;codecs=opus', ext: 'webm' },
    { type: 'audio/webm', ext: 'webm' },
    { type: 'audio/mp4', ext: 'mp4' },
    { type: 'audio/ogg;codecs=opus', ext: 'ogg' },
    { type: 'audio/wav', ext: 'wav' },
  ];

  for (const candidate of candidateTypes) {
    if (MediaRecorder.isTypeSupported(candidate.type)) {
      return { mimeType: candidate.type, extension: candidate.ext };
    }
  }
  return { mimeType: '', extension: 'webm' };
}

export default function VoiceRecorder({
  onAudioReady,
  onTranscriptChange,
  onRecordingStateChange,
  disabled = false,
  isProcessing = false,
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [permissionError, setPermissionError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const mimeTypeInfoRef = useRef({ mimeType: '', extension: 'webm' });
  const speechRecognitionRef = useRef(null);
  const transcriptRef = useRef('');
  const isRecordingRef = useRef(false);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
      if (speechRecognitionRef.current) {
        try { speechRecognitionRef.current.stop(); } catch {}
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startRecording = async () => {
    setPermissionError(null);
    audioChunksRef.current = [];
    transcriptRef.current = '';
    setLiveTranscript('');
    setDuration(0);

    // 1. Initialize real-time SpeechRecognition FIRST so microphone permissions and dictation start immediately
    const SpeechRecognitionClass = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null;

    if (SpeechRecognitionClass) {
      try {
        const recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.lang = (typeof navigator !== 'undefined' && navigator.language) || 'en-US';

        recognition.onstart = () => {
          console.log('[VoiceRecorder] SpeechRecognition active.');
        };

        recognition.onresult = (event) => {
          let interimTranscript = '';
          let finalTranscript = '';

          for (let i = 0; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript + ' ';
            } else {
              interimTranscript += transcript;
            }
          }

          const combined = (finalTranscript + interimTranscript).trim();
          if (combined) {
            transcriptRef.current = combined;
            setLiveTranscript(combined);
            // Write live spoken words directly into Clinical Description
            if (onTranscriptChange) {
              onTranscriptChange(combined);
            }
          }
        };

        recognition.onerror = (event) => {
          // Ignore non-fatal events like 'no-speech'
          if (event.error !== 'no-speech') {
            console.warn('[VoiceRecorder] SpeechRecognition event:', event.error);
          }
          if (event.error === 'not-allowed') {
            setPermissionError('Microphone permission for live dictation was denied.');
          }
        };

        recognition.onend = () => {
          // Restart recognition if user is still actively speaking/recording
          if (isRecordingRef.current) {
            setTimeout(() => {
              if (isRecordingRef.current && speechRecognitionRef.current) {
                try {
                  speechRecognitionRef.current.start();
                } catch (e) {
                  console.warn('[VoiceRecorder] Restart recognition:', e);
                }
              }
            }, 100);
          }
        };

        recognition.start();
        speechRecognitionRef.current = recognition;
      } catch (recErr) {
        console.warn('[VoiceRecorder] SpeechRecognition initialization error:', recErr);
      }
    }

    // 2. Start MediaRecorder in parallel to capture the audio blob for backend upload
    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setPermissionError('Microphone recording is not supported in this browser environment.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const { mimeType, extension } = getSupportedMimeType();
      mimeTypeInfoRef.current = { mimeType, extension };

      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const recordedBlob = new Blob(audioChunksRef.current, {
          type: mimeType || 'audio/webm',
        });
        audioChunksRef.current = [];

        // Stop all audio tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        const capturedTranscript = transcriptRef.current;
        if (recordedBlob.size > 0 && onAudioReady) {
          const filename = `voice_recording.${mimeTypeInfoRef.current.extension}`;
          onAudioReady(recordedBlob, filename, capturedTranscript);
        }
      };

      mediaRecorder.start(200);
      isRecordingRef.current = true;
      setIsRecording(true);
      if (onRecordingStateChange) onRecordingStateChange(true);

      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('[VoiceRecorder] Microphone access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setPermissionError('Microphone permission was denied. Please allow microphone access in your browser.');
      } else {
        setPermissionError('Unable to access microphone: ' + (err.message || 'Unknown error'));
      }
      isRecordingRef.current = false;
      setIsRecording(false);
      if (onRecordingStateChange) onRecordingStateChange(false);
      if (speechRecognitionRef.current) {
        try { speechRecognitionRef.current.stop(); } catch {}
      }
    }
  };

  const stopRecording = () => {
    isRecordingRef.current = false;
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (speechRecognitionRef.current) {
      try { speechRecognitionRef.current.stop(); } catch {}
    }

    // Allow in-flight audio buffer to flush cleanly
    setTimeout(() => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
      if (onRecordingStateChange) onRecordingStateChange(false);
    }, 150);
  };

  const cancelRecording = () => {
    isRecordingRef.current = false;
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (speechRecognitionRef.current) {
      try { speechRecognitionRef.current.abort(); } catch {}
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      audioChunksRef.current = [];
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
    if (onRecordingStateChange) onRecordingStateChange(false);
    setLiveTranscript('');
    setDuration(0);
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col gap-2">
      {/* Microphone / Recording Controls */}
      <div className="flex items-center gap-3">
        {!isRecording ? (
          <button
            type="button"
            id="voice-record-btn"
            onClick={startRecording}
            disabled={disabled || isProcessing}
            aria-label="Start voice recording"
            className="flex items-center gap-2 px-4 py-3 bg-surface-container hover:bg-surface-container-high border border-outline-variant hover:border-primary-container text-on-surface font-label-md uppercase tracking-wider rounded transition-colors duration-150 select-none disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px] text-primary">mic</span>
            <span>{isProcessing ? 'Processing Voice...' : 'Voice Record'}</span>
          </button>
        ) : (
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 w-full sm:w-auto">
            <div className="flex items-center gap-2">
              {/* Live recording indicator */}
              <div className="flex items-center gap-2 px-3 py-2 bg-error-container/30 border border-error/50 rounded text-error">
                <span className="w-2.5 h-2.5 rounded-full bg-error animate-pulse"></span>
                <span className="font-label-sm font-mono tracking-wider font-semibold">
                  LIVE REC {formatDuration(duration)}
                </span>
              </div>

              {/* Stop and Submit Button */}
              <button
                type="button"
                id="voice-stop-btn"
                onClick={stopRecording}
                className="flex items-center gap-2 px-4 py-2.5 bg-primary-container text-on-primary font-label-md uppercase tracking-wider rounded hover:bg-primary transition-colors select-none font-medium shadow-sm cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">stop</span>
                <span>Stop &amp; Analyze</span>
              </button>

              {/* Cancel Button */}
              <button
                type="button"
                id="voice-cancel-btn"
                onClick={cancelRecording}
                className="text-on-surface-variant hover:text-on-surface font-label-sm uppercase tracking-wider px-2 py-1 transition-colors select-none cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Permission or Access Error */}
      {permissionError && (
        <div className="p-3 bg-error-container border border-error/40 rounded text-on-error-container text-xs flex items-center justify-between gap-2 mt-1">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px] text-error">mic_off</span>
            <span>{permissionError}</span>
          </div>
          <button
            type="button"
            onClick={() => setPermissionError(null)}
            className="text-error font-bold px-1"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
