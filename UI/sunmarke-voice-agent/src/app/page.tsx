"use client";

import { useState, useCallback, useRef } from "react";
import VoiceRecorder, { ModelResponse } from "./components/voice_recorder";
import ModelResponseCard from "./components/model_response_card";

type ModelState = {
  text: string;
  audioUrl: string;
  loading: boolean;
  error?: string;
  responseTimeMs?: number;  // ms from record-stop to response arrival
};

const FIXED_MODELS = ["deepseek", "kimi", "gemini"];

export default function HomePage() {
  const [transcript, setTranscript] = useState<string>("");
  const [query, setQuery] = useState<string>("");   // raw query for relevance scoring
  const [responses, setResponses] = useState<Record<string, ModelState>>({});
  const [isRecording, setIsRecording] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  // Track when the user stopped recording (= start of model clock)
  const recordStopTimeRef = useRef<number>(0);

  const handleStart = useCallback(() => {
    setIsRecording(true);
    setHasStarted(true);
    setTranscript("");
    setQuery("");
    const loading: Record<string, ModelState> = {};
    FIXED_MODELS.forEach((m) => {
      loading[m] = { text: "", audioUrl: "", loading: true };
    });
    setResponses(loading);
  }, []);

  const handleDone = useCallback(() => {
    setIsRecording(false);
    // Mark the clock start — models race from here
    recordStopTimeRef.current = Date.now();
    // Safety: mark any still-loading models as done after 30 s
    setTimeout(() => {
      setResponses((prev) => {
        const next = { ...prev };
        FIXED_MODELS.forEach((m) => {
          if (next[m]?.loading) next[m] = { ...next[m], loading: false };
        });
        return next;
      });
    }, 30_000);
  }, []);

  const handleData = useCallback((data: ModelResponse & { transcript?: string }) => {
    if (data.transcript) {
      setTranscript(data.transcript);
      setQuery(data.transcript);  // use transcript as the relevance query
    }

    const modelKey = (data.model ?? "").toLowerCase();
    const matched = FIXED_MODELS.find((m) => modelKey.includes(m)) ?? modelKey;
    const responseTimeMs = recordStopTimeRef.current
      ? Date.now() - recordStopTimeRef.current
      : undefined;

    setResponses((prev) => ({
      ...prev,
      [matched]: {
        text: data.text ?? "",
        audioUrl: data.audioUrl ?? "",
        loading: false,
        error: data.error,
        responseTimeMs,
      },
    }));
  }, []);

  return (
    <main style={{
      minHeight: "100vh",
      background: "#f4f6f9",
      fontFamily: "'DM Sans', 'Segoe UI', system-ui, sans-serif",
    }}>
      {/* ── Nav ── */}
      <nav style={{
        background: "#0f1117", borderBottom: "1px solid #1e2330",
        padding: "0 32px", display: "flex", alignItems: "center",
        height: "58px", gap: "14px",
      }}>
        <div style={{
          width: "32px", height: "32px", borderRadius: "9px",
          background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <circle cx="7.5" cy="7.5" r="5.5" stroke="white" strokeWidth="1.4" />
            <circle cx="7.5" cy="7.5" r="2.2" fill="white" />
          </svg>
        </div>
        <span style={{ fontWeight: 700, fontSize: "15px", color: "#f1f5f9", letterSpacing: "-0.01em" }}>
          Sunmarke Voice Agent
        </span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#64748b" }}>
          <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#22c55e" }} />
          Live
        </div>
      </nav>

      {/* ── Hero ── */}
      <div style={{
        background: "#0f1117", borderBottom: "1px solid #1e2330",
        padding: "48px 24px",
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: "24px", textAlign: "center",
      }}>
        <div>
          <h1 style={{
            margin: "0 0 8px",
            fontSize: "clamp(22px, 4vw, 32px)",
            fontWeight: 800, color: "#f8fafc",
            letterSpacing: "-0.03em", lineHeight: 1.2,
          }}>
            Ask anything about Sunmarke
          </h1>
          <p style={{ margin: 0, fontSize: "15px", color: "#64748b" }}>
            Speak your question — DeepSeek, Kimi &amp; Gemini answer simultaneously
          </p>
        </div>

        <VoiceRecorder onData={handleData} onStart={handleStart} onDone={handleDone} />

        {transcript && (
          <div style={{
            padding: "11px 20px",
            background: "#1e2330", border: "1px solid #2d3548",
            borderRadius: "100px", maxWidth: "600px", width: "100%",
            display: "flex", alignItems: "center", gap: "10px",
          }}>
            <span style={{ fontSize: "10px", fontWeight: 700, color: "#3b82f6", letterSpacing: "0.1em", textTransform: "uppercase", flexShrink: 0 }}>
              YOU
            </span>
            <span style={{ fontSize: "14px", color: "#cbd5e1", textAlign: "left" }}>
              {transcript}
            </span>
          </div>
        )}
      </div>

      {/* ── Grid ── */}
      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 20px" }}>

        {hasStarted && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                Model Responses
              </span>
              <span style={{ fontSize: "11px", color: "#64748b" }}>
                Score = Speed (2) + Length (1) + Relevance (2)
              </span>
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "16px",
            }}>
              {FIXED_MODELS.map((name) => {
                const r = responses[name];
                return (
                  <ModelResponseCard
                    key={name}
                    modelName={name}
                    text={r?.text ?? ""}
                    audioUrl={r?.audioUrl ?? ""}
                    loading={r?.loading ?? false}
                    error={r?.error}
                    query={query}
                    responseTimeMs={r?.responseTimeMs}
                  />
                );
              })}
            </div>
          </>
        )}

        {!hasStarted && (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ marginBottom: "16px", opacity: 0.25 }}>
              <rect x="19" y="4" width="10" height="24" rx="5" fill="#475569" />
              <path d="M10 22c0 7.73 6.27 14 14 14s14-6.27 14-14" stroke="#475569" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="24" y1="36" x2="24" y2="44" stroke="#475569" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="17" y1="44" x2="31" y2="44" stroke="#475569" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <p style={{ margin: 0, fontSize: "15px", fontWeight: 500, color: "#475569" }}>
              Press the mic button above to begin
            </p>
            <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#64748b" }}>
              Scores are calculated automatically from speed, response length, and keyword relevance
            </p>
          </div>
        )}
      </div>

      <style>{`
        @media (max-width: 768px) {
          div[style*="repeat(3, 1fr)"] { grid-template-columns: 1fr !important; }
        }
        @media (min-width: 769px) and (max-width: 1024px) {
          div[style*="repeat(3, 1fr)"] { grid-template-columns: repeat(2, 1fr) !important; }
        }
        * { box-sizing: border-box; }
      `}</style>
    </main>
  );
}