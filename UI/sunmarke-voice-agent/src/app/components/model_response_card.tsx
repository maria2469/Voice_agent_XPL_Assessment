"use client";

import React, { useRef, useState } from "react";

type ModelResponseCardProps = {
    modelName: string;
    text: string;
    audioUrl: string;
    loading: boolean;
    error?: string;
    onAudioEnd?: () => void;
};

const MODEL_META: Record<string, { color: string; bg: string; icon: string; label: string }> = {
    deepseek: { color: "#1a6de8", bg: "#e8f0fe", icon: "D", label: "DeepSeek" },
    kimi: { color: "#0e8a5f", bg: "#e1f5ee", icon: "K", label: "Kimi" },
    default: { color: "#7c3aed", bg: "#ede9fe", icon: "AI", label: "Model" },
};

function getModelMeta(name: string) {
    const key = name.toLowerCase();
    for (const [k, v] of Object.entries(MODEL_META)) {
        if (key.includes(k)) return v;
    }
    return { ...MODEL_META.default, label: name };
}

export default function ModelResponseCard({
    modelName,
    text,
    audioUrl,
    loading,
    error,
    onAudioEnd,
}: ModelResponseCardProps) {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [playing, setPlaying] = useState(false);
    const meta = getModelMeta(modelName);

    const togglePlay = () => {
        if (!audioRef.current) return;
        if (playing) {
            audioRef.current.pause();
        } else {
            audioRef.current.play().catch(() => { });
        }
    };

    return (
        <div style={{
            display: "flex",
            flexDirection: "column",
            borderRadius: "14px",
            border: "1px solid #e2e8f0",
            background: "#fff",
            overflow: "hidden",
            boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
            minHeight: "220px",
        }}>
            {/* Header */}
            <div style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "14px 16px",
                borderBottom: "1px solid #f1f5f9",
                background: meta.bg,
            }}>
                <div style={{
                    width: "34px",
                    height: "34px",
                    borderRadius: "8px",
                    background: meta.color,
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "13px",
                    fontWeight: 700,
                    letterSpacing: "-0.02em",
                    flexShrink: 0,
                }}>
                    {meta.icon}
                </div>
                <div>
                    <p style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: meta.color }}>
                        {meta.label}
                    </p>
                    <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
                        {loading ? "generating…" : error ? "error" : audioUrl ? "response ready" : text ? "responded" : "waiting"}
                    </p>
                </div>
                <div style={{
                    marginLeft: "auto",
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: loading ? "#f59e0b" : error ? "#ef4444" : text ? "#22c55e" : "#e2e8f0",
                    flexShrink: 0,
                }} />
            </div>

            {/* Body */}
            <div style={{ padding: "16px", flex: 1, display: "flex", flexDirection: "column", gap: "12px" }}>
                {loading ? (
                    <LoadingDots color={meta.color} />
                ) : error ? (
                    <p style={{ margin: 0, fontSize: "13px", color: "#ef4444", lineHeight: 1.6 }}>
                        ⚠ {error}
                    </p>
                ) : (
                    <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.7, color: "#1e293b", flex: 1 }}>
                        {text || <span style={{ color: "#cbd5e1" }}>No response yet.</span>}
                    </p>
                )}

                {/* Audio — plays ONLY when play button is clicked */}
                {audioUrl && !loading && !error && (
                    <div style={{
                        marginTop: "auto",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        padding: "10px 12px",
                        background: "#f8fafc",
                        borderRadius: "8px",
                        border: "1px solid #e2e8f0",
                    }}>
                        <button
                            onClick={togglePlay}
                            style={{
                                width: "32px",
                                height: "32px",
                                borderRadius: "50%",
                                background: meta.color,
                                border: "none",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexShrink: 0,
                            }}
                            title={playing ? "Pause" : "Play audio response"}
                        >
                            {playing ? <PauseIcon /> : <PlayIcon />}
                        </button>
                        <div style={{ flex: 1, fontSize: "12px", color: "#64748b" }}>
                            {playing ? "Playing audio response…" : "Click to play audio response"}
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
    return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M3 2l7 4-7 4V2z" fill="white" />
        </svg>
    );
}

function PauseIcon() {
    return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <rect x="2" y="2" width="3" height="8" rx="1" fill="white" />
            <rect x="7" y="2" width="3" height="8" rx="1" fill="white" />
        </svg>
    );
}

function LoadingDots({ color }: { color: string }) {
    return (
        <div style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 0" }}>
            {[0, 1, 2].map((i) => (
                <div
                    key={i}
                    style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "50%",
                        background: color,
                        opacity: 0.3,
                        animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }}
                />
            ))}
            <style>{`
                @keyframes pulse {
                    0%, 100% { opacity: 0.3; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.2); }
                }
            `}</style>
        </div>
    );
}