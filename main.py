from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
import json

from services.RAG_service import RAGService
from services.voice_handling.voice_input import transcribe_audio

# -----------------------------
# Initialize FastAPI
# -----------------------------
app = FastAPI(title="Sunmarke Voice Agent API")

# -----------------------------
# CORS Middleware
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Initialize RAG Service (once at startup)
# -----------------------------
rag = RAGService()

# -----------------------------
# Temp folder for audio
# -----------------------------
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)


# -----------------------------
# Streaming endpoint
# -----------------------------
@app.post("/api/query-stream")
async def query_audio_stream(file: UploadFile = File(...)):
    """
    Receives audio, transcribes it, queries the RAG service,
    and streams results back as Server-Sent Events (SSE).
    """
    audio_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.wav")

    try:
        # Save uploaded audio
        with open(audio_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        print(f"🎤 Saved audio: {audio_path}")

        # Transcribe audio
        user_query = transcribe_audio(audio_path)
        print(f"🧠 Transcribed: {user_query}")

        if not user_query or not user_query.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Could not understand audio"}
            )

        # SSE generator — runs synchronously inside StreamingResponse
        def event_generator():
            try:
                for result in rag.query_multi_stream(user_query):
                    payload = json.dumps(result)
                    yield f"data: {payload}\n\n"
                # Signal end-of-stream (client ignores "event: done" data: {})
                yield "event: done\ndata: {}\n\n"
            except Exception as exc:
                error_payload = json.dumps({"error": str(exc)})
                yield f"event: error\ndata: {error_payload}\n\n"
            finally:
                # Clean up audio file after streaming
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                # Prevent buffering / caching on the stream
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as exc:
        print(f"❌ ERROR in query-stream: {exc}")
        # Attempt cleanup on unexpected error
        try:
            os.remove(audio_path)
        except OSError:
            pass
        return JSONResponse(status_code=500, content={"error": str(exc)})


# -----------------------------
# Serve audio files
# -----------------------------
@app.get("/audio/{file_name}")
async def get_audio(file_name: str):
    file_path = os.path.join(TEMP_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    return JSONResponse(status_code=404, content={"error": "Audio not found"})


# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)