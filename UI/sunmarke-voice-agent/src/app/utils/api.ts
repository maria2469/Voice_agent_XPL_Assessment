export async function sendAudioToRAG(audioBlob: Blob) {
    const formData = new FormData();
    formData.append("file", audioBlob, "voice.wav");

    const res = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || "API request failed");
    }

    return res.json(); // returns { gemini, kimi, deepseek }
}