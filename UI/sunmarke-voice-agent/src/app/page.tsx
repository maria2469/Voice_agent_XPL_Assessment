"use client";

import { useState } from "react";
import VoiceRecorder from "./components/voice_recorder";
import ModelResponseCard from "./components/model_response_card";
import { sendAudioToRAG } from "./utils/api";

export default function HomePage() {
  const [responses, setResponses] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState<{
    gemini: boolean;
    kimi: boolean;
    deepseek: boolean;
  }>({
    gemini: false,
    kimi: false,
    deepseek: false,
  });

  const handleRecordingComplete = async (audioBlob: Blob) => {
    setResponses([]);
    setLoadingModels({ gemini: true, kimi: true, deepseek: true });

    try {
      const data = await sendAudioToRAG(audioBlob);

      // data format: { gemini: { text, audioUrl }, kimi: {...}, deepseek: {...} }
      setResponses([
        { modelName: "Gemini", ...data.gemini },
        { modelName: "Kimi", ...data.kimi },
        { modelName: "DeepSeek", ...data.deepseek },
      ]);
    } catch (err) {
      console.error(err);
      setResponses([
        { modelName: "Gemini", text: "", audioUrl: "", error: "Failed" },
        { modelName: "Kimi", text: "", audioUrl: "", error: "Failed" },
        { modelName: "DeepSeek", text: "", audioUrl: "", error: "Failed" },
      ]);
    } finally {
      setLoadingModels({ gemini: false, kimi: false, deepseek: false });
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Sunmarke Voice Assistant</h1>
      <VoiceRecorder onRecordingComplete={handleRecordingComplete} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "20px",
          marginTop: "20px",
        }}
      >
        {responses.map((r) => (
          <ModelResponseCard
            key={r.modelName}
            modelName={r.modelName}
            text={r.text}
            audioUrl={r.audioUrl}
            loading={loadingModels[r.modelName.toLowerCase() as keyof typeof loadingModels]}
            error={r.error}
          />
        ))}
      </div>
    </div>
  );
}