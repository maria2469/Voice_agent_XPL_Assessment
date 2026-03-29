"use client";

import { useState, useCallback } from "react";
import VoiceRecorder, { ModelResponse } from "./components/voice_recorder";
import ModelResponseCard from "./components/model_response_card";

type ModelState = {
  text: string;
  audioUrl: string;
  loading: boolean;
  error?: string;
};

export default function HomePage() {
  const [transcript, setTranscript] = useState<string>("");
  const [responses, setResponses] = useState<Record<string, ModelState>>({});
  const [isRecording, setIsRecording] = useState(false);

  const handleStart = useCallback(() => {
    setIsRecording(true);
    setTranscript("");
    setResponses({});
  }, []);

  const handleData = useCallback((data: ModelResponse & { transcript?: string }) => {
    if (data.transcript) setTranscript(data.transcript);

    const modelKey = data.model ?? "unknown";

    setResponses((prev) => ({
      ...prev,
      [modelKey]: {
        text: data.text ?? "",
        audioUrl: data.audioUrl ?? "",
        loading: false,
        error: data.error,
      },
    }));
  }, []);

  const handleDone = useCallback(() => {
    setIsRecording(false);
  }, []);

  const modelKeys = Object.keys(responses);

  return (
    <main style={{
      minHeight: "100vh",
      background: "#f8fafc",
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    }}>
      {/* Nav */}
      <div style={{
        borderBottom: "1px solid #e2e8f0",
        background: "#fff",
        padding: "0 32px",
        display: "flex",
        alignItems: "center",
        height: "56px",
        gap: "12px",
      }}>
        <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
          <rect width="26" height="26" rx="7" fill="url(#ng)" />
          <defs>
            <linearGradient id="ng" x1="0" y1="0" x2="26" y2="26">
              <stop stopColor="#667eea" /><stop offset="1" stopColor="#764ba2" />
            </linearGradient>
          </defs>
          <circle cx="13" cy="13" r="5" stroke="white" strokeWidth="1.5" />
          <circle cx="13" cy="13" r="2" fill="white" />
        </svg>
        <span style={{ fontWeight: 700, fontSize: "15px", color: "#0f172a" }}>Voice Agent</span>
        <span style={{ color: "#94a3b8", fontSize: "13px" }}>Multi-model</span>
      </div>

      <div style={{ maxWidth: "1120px", margin: "0 auto", padding: "40px 24px" }}>

        {/* Record card */}
        <div style={{
          background: "#fff",
          borderRadius: "16px",
          border: "1px solid #e2e8f0",
          padding: "36px 32px",
          marginBottom: "32px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "20px",
          textAlign: "center",
        }}>
          <div>
            <h1 style={{ margin: "0 0 6px", fontSize: "22px", fontWeight: 700, color: "#0f172a" }}>
              Ask a question
            </h1>
            <p style={{ margin: 0, fontSize: "14px", color: "#64748b" }}>
              Record your voice — DeepSeek, Kimi, and Gemini answer simultaneously
            </p>
          </div>

          <VoiceRecorder onData={handleData} onStart={handleStart} onDone={handleDone} />

          {transcript && (
            <div style={{
              padding: "12px 18px",
              background: "#f1f5f9",
              borderRadius: "10px",
              maxWidth: "560px",
              width: "100%",
              textAlign: "left",
            }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.08em", marginRight: "8px" }}>
                YOU
              </span>
              <span style={{ fontSize: "14px", color: "#334155" }}>{transcript}</span>
            </div>
          )}
        </div>

        {/* Responses */}
        {modelKeys.length > 0 && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Responses · {modelKeys.length} model{modelKeys.length !== 1 ? "s" : ""}
              </span>
              <span style={{ fontSize: "12px", color: "#cbd5e1" }}>Click play on any card to hear its audio</span>
            </div>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))",
              gap: "16px",
            }}>
              {modelKeys.map((name) => {
                const r = responses[name];
                return (
                  <ModelResponseCard
                    key={name}
                    modelName={name}
                    text={r.text}
                    audioUrl={r.audioUrl}
                    loading={r.loading}
                    error={r.error}
                  />
                );
              })}
            </div>
          </>
        )}

        {/* Empty state */}
        {modelKeys.length === 0 && !isRecording && (
          <div style={{ textAlign: "center", padding: "80px 0", color: "#cbd5e1" }}>
            <svg width="44" height="44" viewBox="0 0 44 44" fill="none" style={{ marginBottom: "12px" }}>
              <rect x="18" y="4" width="8" height="22" rx="4" fill="#e2e8f0" />
              <path d="M9 20c0 7.18 5.82 13 13 13s13-5.82 13-13" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
              <line x1="22" y1="33" x2="22" y2="40" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
              <line x1="16" y1="40" x2="28" y2="40" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <p style={{ margin: 0, fontSize: "14px" }}>Record a question to see responses from all models</p>
          </div>
        )}
      </div>
    </main>
  );
}