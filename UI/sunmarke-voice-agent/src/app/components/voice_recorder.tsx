"use client";

import { useState, useRef, useCallback } from "react";

// -----------------------------
// Types
// -----------------------------
export type ModelResponse = {
  model: string;
  text: string;
  audioUrl: string;
  sources: any[];
  error?: string;
};

type VoiceRecorderProps = {
  onData: (data: ModelResponse) => void;
  onStart?: () => void;
  onDone?: () => void;
};

// -----------------------------
// VoiceRecorder Component
// -----------------------------
export default function VoiceRecorder({ onData, onStart, onDone }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioDataRef = useRef<Float32Array[]>([]);

  // -----------------------------
  // Start Recording
  // -----------------------------
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
        audioDataRef.current.push(
          new Float32Array(e.inputBuffer.getChannelData(0))
        );
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setRecording(true);
      onStart?.();
    } catch (err) {
      console.error("Error starting recording:", err);
    }
  }, [onStart]);

  // -----------------------------
  // Stop Recording
  // -----------------------------
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

  // -----------------------------
  // Stream audio to backend
  // -----------------------------
  const streamToBackend = useCallback(
    async (audioBlob: Blob) => {
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
              const jsonStr = part.slice(6).trim(); // remove "data: "
              if (!jsonStr || jsonStr === "{}") continue;
              try {
                const parsed: ModelResponse = JSON.parse(jsonStr);
                if (typeof onData === "function") {
                  onData(parsed);
                }
                // Play audio if available
                if (parsed.audioUrl) {
                  const audio = new Audio(parsed.audioUrl);
                  audio.play().catch(() => { });
                }
              } catch (err) {
                console.error("JSON parse error on chunk:", jsonStr, err);
              }
            }
          }

          buffer = parts[parts.length - 1];
        }
      } catch (err) {
        console.error("Error streaming to backend:", err);
      }
    },
    [onData]
  );

  // -----------------------------
  // WAV encoding helpers
  // -----------------------------
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
    const length = buffers.reduce((acc, b) => acc + b.length, 0);
    const result = new Float32Array(length);
    let offset = 0;
    buffers.forEach((b) => {
      result.set(b, offset);
      offset += b.length;
    });
    return result;
  };

  const floatTo16BitPCM = (view: DataView, offset: number, input: Float32Array) => {
    for (let i = 0; i < input.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
  };

  const writeString = (view: DataView, offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  // -----------------------------
  // UI
  // -----------------------------
  return (
    <button
      onClick={recording ? stopRecording : startRecording}
      disabled={processing}
      style={{
        padding: "12px 28px",
        backgroundColor: processing ? "#888" : recording ? "#ff4d4d" : "#4caf50",
        color: "white",
        border: "none",
        borderRadius: "6px",
        cursor: processing ? "not-allowed" : "pointer",
        fontSize: "16px",
        fontWeight: 600,
        transition: "background-color 0.2s",
      }}
    >
      {processing ? "Processing…" : recording ? "⏹ Stop Recording" : "🎤 Start Recording"}
    </button>
  );
}