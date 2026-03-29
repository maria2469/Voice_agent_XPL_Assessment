"use client";

import { useState, useRef, useCallback } from "react";

export type ModelResponse = {
  model: string;
  text: string;
  audioUrl: string;
  sources: any[];
  error?: string;
  transcript?: string;
};

type VoiceRecorderProps = {
  onData: (data: ModelResponse) => void;
  onStart?: () => void;
  onDone?: () => void;
};

export default function VoiceRecorder({ onData, onStart, onDone }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioDataRef = useRef<Float32Array[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      audioDataRef.current = [];
      processor.onaudioprocess = (e) => {
        audioDataRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };
      source.connect(processor);
      processor.connect(audioContext.destination);
      setRecording(true);
      onStart?.();
    } catch (err) {
      console.error("Mic access error:", err);
    }
  }, [onStart]);

  const stopRecording = useCallback(async () => {
    setRecording(false);
    setProcessing(true);
    processorRef.current?.disconnect();
    await audioContextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    const wavBlob = encodeWAV(audioDataRef.current);
    await streamToBackend(wavBlob);
    setProcessing(false);
    onDone?.();
  }, [onDone]);

  const streamToBackend = useCallback(async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "voice.wav");
      const res = await fetch("http://localhost:8000/api/query-stream", {
        method: "POST",
        body: formData,
      });
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        for (const part of parts.slice(0, -1)) {
          if (part.startsWith("data: ")) {
            const jsonStr = part.slice(6).trim();
            if (!jsonStr || jsonStr === "{}") continue;
            try {
              const parsed: ModelResponse = JSON.parse(jsonStr);
              if (typeof onData === "function") onData(parsed);
            } catch (err) {
              console.error("SSE parse error:", jsonStr, err);
            }
          }
        }
        buffer = parts[parts.length - 1];
      }
    } catch (err) {
      console.error("Stream error:", err);
    }
  }, [onData]);

  // WAV helpers
  const encodeWAV = (audioData: Float32Array[]): Blob => {
    const sampleRate = 16000;
    const samples = mergeBuffers(audioData);
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, "WAVE");
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);
    floatTo16BitPCM(view, 44, samples);
    return new Blob([view], { type: "audio/wav" });
  };
  const mergeBuffers = (buffers: Float32Array[]): Float32Array => {
    const len = buffers.reduce((a, b) => a + b.length, 0);
    const out = new Float32Array(len);
    let offset = 0;
    buffers.forEach((b) => { out.set(b, offset); offset += b.length; });
    return out;
  };
  const floatTo16BitPCM = (view: DataView, offset: number, input: Float32Array) => {
    for (let i = 0; i < input.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
  };
  const writeString = (view: DataView, offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };

  const isIdle = !recording && !processing;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
      <button
        onClick={recording ? stopRecording : startRecording}
        disabled={processing}
        style={{
          width: "72px",
          height: "72px",
          borderRadius: "50%",
          border: "none",
          cursor: processing ? "not-allowed" : "pointer",
          background: processing
            ? "#475569"
            : recording
              ? "linear-gradient(135deg, #ef4444, #dc2626)"
              : "linear-gradient(135deg, #3b82f6, #2563eb)",
          color: "white",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: recording
            ? "0 0 0 8px rgba(239,68,68,0.2), 0 0 0 16px rgba(239,68,68,0.08)"
            : isIdle
              ? "0 0 0 6px rgba(59,130,246,0.15)"
              : "none",
          transition: "all 0.25s ease",
          animation: recording ? "recPulse 1.5s ease-in-out infinite" : "none",
        }}
        title={recording ? "Stop recording" : "Start recording"}
      >
        {processing ? (
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <circle cx="11" cy="11" r="9" stroke="white" strokeWidth="2" strokeDasharray="28 14" strokeLinecap="round">
              <animateTransform attributeName="transform" type="rotate" from="0 11 11" to="360 11 11" dur="0.8s" repeatCount="indefinite" />
            </circle>
          </svg>
        ) : recording ? (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <rect x="3" y="3" width="12" height="12" rx="2" fill="white" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <rect x="8" y="2" width="6" height="13" rx="3" fill="white" />
            <path d="M4 11c0 3.87 3.13 7 7 7s7-3.13 7-7" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
            <line x1="11" y1="18" x2="11" y2="21" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        )}
      </button>

      <span style={{
        fontSize: "12px", fontWeight: 500,
        color: recording ? "#ef4444" : processing ? "#94a3b8" : "#64748b",
        letterSpacing: "0.02em",
      }}>
        {processing ? "Processing…" : recording ? "● Recording — tap to stop" : "Tap to record"}
      </span>

      <style>{`
        @keyframes recPulse {
          0%, 100% { box-shadow: 0 0 0 8px rgba(239,68,68,0.2), 0 0 0 16px rgba(239,68,68,0.08); }
          50% { box-shadow: 0 0 0 12px rgba(239,68,68,0.15), 0 0 0 22px rgba(239,68,68,0.04); }
        }
      `}</style>
    </div>
  );
}