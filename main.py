from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from services.RAG_service import RAGService
from services.voice_handling.voice_input import transcribe_audio
from services.voice_handling.voice_output import text_to_speech
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

app = FastAPI(title="Sunmarke Voice Agent API")

# ✅ Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Initialize RAG once
rag = RAGService()

# ✅ Correct folder name
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)


@app.post("/api/query")
async def query_audio(file: UploadFile = File(...)):
    try:
        # -------------------------
        # 1️⃣ Save uploaded audio
        # -------------------------
        audio_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.wav")

        with open(audio_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        print("🎤 Saved input audio:", audio_path)

        # -------------------------
        # 2️⃣ Transcribe
        # -------------------------
        user_query = transcribe_audio(audio_path)

        print("🧠 Transcribed text:", user_query)

        if not user_query.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Could not understand audio"}
            )

        # -------------------------
        # 3️⃣ Multi-RAG
        # -------------------------
        results = rag.query_multi(user_query)

        # -------------------------
        # 4️⃣ Generate TTS in parallel
        # -------------------------
        response_data = {}

        def tts_task(model_name, answer_text):
            audio_file_name = f"{model_name}_{uuid.uuid4()}.mp3"
            audio_file_path = os.path.join(TEMP_DIR, audio_file_name)

            text_to_speech(answer_text, audio_file_path)

            print(f"🔊 Generated TTS: {audio_file_path}")

            return model_name, audio_file_name

        with ThreadPoolExecutor(max_workers=len(results)) as executor:
            futures = [
                executor.submit(tts_task, model, res["answer"])
                for model, res in results.items()
            ]

            for future in as_completed(futures):
                model_name, audio_file_name = future.result()
                res = results[model_name]

                response_data[model_name.lower()] = {
                    "text": res["answer"],
                    # ✅ FIX: absolute URL (CRITICAL)
                    "audioUrl": f"http://localhost:8000/audio/{audio_file_name}",
                    "sources": res.get("sources", []),
                    "error": None if res["answer"] else "No answer",
                }

        return JSONResponse(content=response_data)

    except Exception as e:
        print("❌ ERROR:", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


# -------------------------
# 🎧 Serve audio files
# -------------------------
@app.get("/audio/{file_name}")
async def get_audio(file_name: str):
    file_path = os.path.join(TEMP_DIR, file_name)

    print("📁 Requested audio:", file_path)

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")

    print("❌ Audio NOT FOUND")
    return JSONResponse(status_code=404, content={"error": "Audio not found"})


# -------------------------
# 🚀 Run server
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)