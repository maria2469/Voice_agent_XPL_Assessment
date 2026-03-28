"use client";

import React from "react";

type ModelResponseCardProps = {
    modelName: string;
    text: string;
    audioUrl: string;
    loading: boolean;
    error?: string;
};

export default function ModelResponseCard({
    modelName,
    text,
    audioUrl,
    loading,
    error,
}: ModelResponseCardProps) {
    return (
        <div
            style={{
                border: "1px solid #ccc",
                padding: "10px",
                borderRadius: "8px",
                minHeight: "120px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
            }}
        >
            <h3>{modelName}</h3>
            {loading ? (
                <p>Loading...</p>
            ) : error ? (
                <p style={{ color: "red" }}>{error}</p>
            ) : (
                <>
                    <p>{text}</p>
                    {audioUrl && <audio controls src={audioUrl}></audio>}
                </>
            )}
        </div>
    );
}