"use client";

import React, { useRef, useState, useMemo } from "react";

type ModelResponseCardProps = {
    modelName: string;
    text: string;
    audioUrl: string;
    loading: boolean;
    error?: string;
    query?: string;           // the original user query — for relevance scoring
    responseTimeMs?: number;  // how long the model took to respond
    onAudioEnd?: () => void;
};

const MODEL_META: Record<string, {
    color: string; gradFrom: string; gradTo: string;
    bg: string; border: string; icon: string; label: string;
}> = {
    deepseek: { color: "#3b82f6", gradFrom: "#3b82f6", gradTo: "#1d4ed8", bg: "#eff6ff", border: "#bfdbfe", icon: "DS", label: "DeepSeek V3" },
    kimi: { color: "#10b981", gradFrom: "#10b981", gradTo: "#059669", bg: "#ecfdf5", border: "#a7f3d0", icon: "KI", label: "Kimi K2" },
    gemini: { color: "#f59e0b", gradFrom: "#f59e0b", gradTo: "#d97706", bg: "#fffbeb", border: "#fde68a", icon: "GM", label: "Gemini" },
    default: { color: "#8b5cf6", gradFrom: "#8b5cf6", gradTo: "#7c3aed", bg: "#f5f3ff", border: "#ddd6fe", icon: "AI", label: "Model" },
};

function getMeta(name: string) {
    const key = name.toLowerCase();
    for (const [k, v] of Object.entries(MODEL_META)) {
        if (key.includes(k)) return v;
    }
    return { ...MODEL_META.default, label: name };
}

// ─────────────────────────────────────────────
// Scoring logic — all 3 dimensions → 0–5 total
// ─────────────────────────────────────────────

type ScoreBreakdown = {
    speed: number;       // 0–2  (faster = higher)
    length: number;      // 0–1  (sweet-spot length)
    relevance: number;   // 0–2  (keyword overlap with query)
    total: number;       // 0–5
    label: string;
};

function computeScore(text: string, query: string, responseTimeMs?: number): ScoreBreakdown {
    // ── Speed (0–2) ──────────────────────────────
    // <3 s = 2 pts, 3–6 s = 1 pt, >6 s = 0 pts
    let speed = 0;
    if (responseTimeMs !== undefined) {
        if (responseTimeMs < 3000) speed = 2;
        else if (responseTimeMs < 6000) speed = 1;
    }

    // ── Length / completeness (0–1) ──────────────
    // Sweet spot: 80–400 words. Too short or too long loses the point.
    const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
    const length = wordCount >= 80 && wordCount <= 400 ? 1 : 0;

    // ── Relevance (0–2) ──────────────────────────
    // Extract meaningful query keywords (≥4 chars, ignore stop-words).
    const STOP = new Set(["what", "with", "this", "that", "from", "have", "will", "your", "about", "which", "when", "then", "they", "their", "there", "these", "those", "been", "were", "also", "into", "more", "such", "some", "than", "each", "only", "both"]);
    const queryWords = query
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, "")
        .split(/\s+/)
        .filter((w) => w.length >= 4 && !STOP.has(w));

    if (queryWords.length === 0) {
        // No scoreable keywords — give benefit of the doubt
        return { speed, length, relevance: 2, total: Math.min(5, speed + length + 2), label: scoreLabel(speed + length + 2) };
    }

    const textLower = text.toLowerCase();
    const matched = queryWords.filter((w) => textLower.includes(w)).length;
    const ratio = matched / queryWords.length;

    let relevance = 0;
    if (ratio >= 0.6) relevance = 2;
    else if (ratio >= 0.3) relevance = 1;

    const total = Math.min(5, speed + length + relevance);
    return { speed, length, relevance, total, label: scoreLabel(total) };
}

function scoreLabel(total: number): string {
    if (total >= 5) return "Excellent";
    if (total >= 4) return "Good";
    if (total >= 3) return "Fair";
    if (total >= 2) return "Weak";
    return "Poor";
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export default function ModelResponseCard({
    modelName, text, audioUrl, loading, error,
    query = "", responseTimeMs, onAudioEnd,
}: ModelResponseCardProps) {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [playing, setPlaying] = useState(false);
    const meta = getMeta(modelName);

    const hasContent = !loading && !error && !!text;

    const score: ScoreBreakdown | null = useMemo(() => {
        if (!hasContent) return null;
        return computeScore(text, query, responseTimeMs);
    }, [hasContent, text, query, responseTimeMs]);

    const togglePlay = () => {
        if (!audioRef.current) return;
        playing ? audioRef.current.pause() : audioRef.current.play().catch(() => { });
    };

    return (
        <div style={{
            display: "flex", flexDirection: "column",
            borderRadius: "16px",
            border: `1px solid ${loading ? "#e2e8f0" : error ? "#fecaca" : meta.border}`,
            background: "#fff",
            overflow: "hidden",
            minHeight: "280px",
            transition: "border-color 0.3s",
        }}>

            {/* ── Header ── */}
            <div style={{
                background: loading ? "#f8fafc" : meta.bg,
                borderBottom: `1px solid ${loading ? "#f1f5f9" : meta.border}`,
                padding: "16px",
                display: "flex", alignItems: "center", gap: "12px",
                transition: "background 0.3s",
            }}>
                <div style={{
                    width: "40px", height: "40px", borderRadius: "10px", flexShrink: 0,
                    background: loading ? "#e2e8f0" : `linear-gradient(135deg, ${meta.gradFrom}, ${meta.gradTo})`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#fff", fontSize: "11px", fontWeight: 800,
                }}>
                    {loading ? <PulsingDot /> : meta.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: loading ? "#94a3b8" : meta.color }}>
                        {meta.label}
                    </p>
                    <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
                        {loading ? "Thinking…" : error ? "Failed" : audioUrl ? "Response + audio ready" : text ? "Response ready" : "Waiting…"}
                    </p>
                </div>
                <div style={{
                    width: "9px", height: "9px", borderRadius: "50%", flexShrink: 0,
                    background: loading ? "#f59e0b" : error ? "#ef4444" : text ? "#22c55e" : "#e2e8f0",
                    boxShadow: loading ? "0 0 0 3px #fef3c7" : error ? "0 0 0 3px #fee2e2" : text ? "0 0 0 3px #dcfce7" : "none",
                    transition: "all 0.3s",
                }} />
            </div>

            {/* ── Score Bar ── */}
            <div style={{
                padding: "12px 16px 0",
                display: "flex", flexDirection: "column", gap: "6px",
            }}>
                {/* Bar + label row */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                        Score
                    </span>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: score ? meta.color : "#cbd5e1" }}>
                        {score ? `${score.total}/5 — ${score.label}` : "—"}
                    </span>
                </div>

                {/* 5-segment bar */}
                <div style={{ display: "flex", gap: "3px" }}>
                    {[1, 2, 3, 4, 5].map((seg) => (
                        <div key={seg} style={{
                            flex: 1, height: "5px", borderRadius: "3px",
                            background: score && seg <= score.total ? meta.color : "#f1f5f9",
                            transition: "background 0.4s ease",
                        }} />
                    ))}
                </div>

                {/* Dimension breakdown — only when scored */}
                {score && (
                    <div style={{ display: "flex", gap: "8px", paddingTop: "2px" }}>
                        {[
                            { label: "Speed", val: score.speed, max: 2 },
                            { label: "Length", val: score.length, max: 1 },
                            { label: "Relevance", val: score.relevance, max: 2 },
                        ].map(({ label, val, max }) => (
                            <div key={label} style={{
                                flex: 1, padding: "5px 8px", borderRadius: "6px",
                                background: "#f8fafc", border: "1px solid #f1f5f9",
                                display: "flex", flexDirection: "column", alignItems: "center", gap: "2px",
                            }}>
                                <span style={{ fontSize: "9px", color: "#94a3b8", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                                    {label}
                                </span>
                                <span style={{ fontSize: "12px", fontWeight: 700, color: val > 0 ? meta.color : "#cbd5e1" }}>
                                    {val}/{max}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* ── Body ── */}
            <div style={{ padding: "14px 16px", flex: 1, display: "flex", flexDirection: "column", gap: "12px" }}>
                {loading ? (
                    <LoadingLines />
                ) : error ? (
                    <div style={{ padding: "12px", borderRadius: "8px", background: "#fef2f2", border: "1px solid #fecaca" }}>
                        <p style={{ margin: 0, fontSize: "13px", color: "#dc2626", lineHeight: 1.6 }}>⚠ {error}</p>
                    </div>
                ) : text ? (
                    <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.75, color: "#1e293b", flex: 1 }}>
                        {text}
                    </p>
                ) : (
                    <p style={{ margin: 0, fontSize: "13px", color: "#cbd5e1", fontStyle: "italic" }}>
                        No response yet.
                    </p>
                )}

                {/* ── Audio Player ── */}
                {audioUrl && !loading && !error && (
                    <div
                        onClick={togglePlay}
                        style={{
                            marginTop: "auto", display: "flex", alignItems: "center", gap: "10px",
                            padding: "10px 14px", borderRadius: "10px", cursor: "pointer",
                            background: playing ? meta.bg : "#f8fafc",
                            border: `1px solid ${playing ? meta.border : "#e2e8f0"}`,
                            transition: "all 0.2s",
                        }}
                    >
                        <div style={{
                            width: "34px", height: "34px", borderRadius: "50%", flexShrink: 0,
                            background: `linear-gradient(135deg, ${meta.gradFrom}, ${meta.gradTo})`,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            boxShadow: playing ? `0 0 0 4px ${meta.bg}` : "none",
                            transition: "box-shadow 0.2s",
                        }}>
                            {playing ? <PauseIcon /> : <PlayIcon />}
                        </div>
                        <div style={{ flex: 1 }}>
                            <p style={{ margin: 0, fontSize: "12px", fontWeight: 600, color: playing ? meta.color : "#475569" }}>
                                {playing ? "Playing…" : "Audio response"}
                            </p>
                            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
                                {playing ? "Click to pause" : "Click to play"}
                            </p>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "2px" }}>
                            {[12, 20, 14, 22, 10, 18, 16].map((h, i) => (
                                <div key={i} style={{
                                    width: "3px", height: `${playing ? h : 6}px`, borderRadius: "2px",
                                    background: playing ? meta.color : "#cbd5e1",
                                    transition: `height 0.3s ease ${i * 0.05}s`,
                                }} />
                            ))}
                        </div>
                        <audio
                            ref={audioRef}
                            src={audioUrl}
                            onPlay={() => setPlaying(true)}
                            onPause={() => setPlaying(false)}
                            onEnded={() => { setPlaying(false); onAudioEnd?.(); }}
                            style={{ display: "none" }}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

function PlayIcon() {
    return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 2l7 4-7 4V2z" fill="white" /></svg>;
}
function PauseIcon() {
    return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><rect x="2" y="2" width="3" height="8" rx="1" fill="white" /><rect x="7" y="2" width="3" height="8" rx="1" fill="white" /></svg>;
}
function PulsingDot() {
    return (
        <>
            <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#cbd5e1", animation: "dotPulse 1.4s ease-in-out infinite" }} />
            <style>{`@keyframes dotPulse { 0%,100%{opacity:.4;transform:scale(.85)} 50%{opacity:1;transform:scale(1.1)} }`}</style>
        </>
    );
}
function LoadingLines() {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", paddingTop: "4px" }}>
            {[100, 85, 92, 60].map((w, i) => (
                <div key={i} style={{
                    height: "12px", borderRadius: "6px", width: `${w}%`,
                    background: "linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)",
                    backgroundSize: "200% 100%",
                    animation: `shimmer 1.5s ease-in-out ${i * 0.1}s infinite`,
                }} />
            ))}
            <style>{`@keyframes shimmer{0%{background-position:200% center}100%{background-position:-200% center}}`}</style>
        </div>
    );
}