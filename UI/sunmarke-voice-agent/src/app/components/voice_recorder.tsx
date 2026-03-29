"use client";

import { useState, useRef } from "react";

type VoiceRecorderProps = {
  onRecordingComplete: (audioBlob: Blob) => void;
};

export default function VoiceRecorder({ onRecordingComplete }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioDataRef = useRef<Float32Array[]>([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaStreamRef.current = stream;

    const audioContext = new AudioContext({ sampleRate: 16000 });
    audioContextRef.current = audioContext;

    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    audioDataRef.current = [];

    processor.onaudioprocess = (e) => {
      const channelData = e.inputBuffer.getChannelData(0);
      audioDataRef.current.push(new Float32Array(channelData));
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    setRecording(true);
  };

  const stopRecording = () => {
    setRecording(false);

    processorRef.current?.disconnect();
    audioContextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());

    const wavBlob = encodeWAV(audioDataRef.current);
    onRecordingComplete(wavBlob);
  };

  // 🔥 WAV encoder
  const encodeWAV = (audioData: Float32Array[]) => {
    const sampleRate = 16000;
    const samples = mergeBuffers(audioData);
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, "WAVE");

    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true); // PCM
    view.setUint16(20, 1, true); // format
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);

    writeString(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);

    floatTo16BitPCM(view, 44, samples);

    return new Blob([view], { type: "audio/wav" });
  };

  const mergeBuffers = (buffers: Float32Array[]) => {
    let length = 0;
    buffers.forEach((b) => (length += b.length));

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
      let s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
  };

  const writeString = (view: DataView, offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  return (
    <div>
      <button
        onClick={recording ? stopRecording : startRecording}
        style={{
          padding: "10px 20px",
          backgroundColor: recording ? "#ff4d4d" : "#4caf50",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
        }}
      >
        {recording ? "Stop Recording" : "Start Recording"}
      </button>
    </div>
  );
}