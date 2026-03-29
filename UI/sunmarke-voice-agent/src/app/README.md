# 🎤 Sunmarke Voice Agent (Multi-LLM RAG System)

A real-time AI voice assistant that:
- 🎤 Takes audio input from users
- 🧠 Uses Retrieval-Augmented Generation (RAG)
- 🤖 Queries multiple LLMs in parallel (Gemini, Kimi, DeepSeek)
- ⚡ Streams responses instantly (no waiting for all models)
- 🔊 Converts responses into speech (TTS)
- 📡 Streams results to frontend using Server-Sent Events (SSE)

---

## 🚀 Features

✅ Real-time voice interaction  
✅ Multi-LLM parallel processing  
✅ Streaming responses (low latency)  
✅ Audio playback per model  
✅ RAG with vector database (PGVector)  
✅ Modular architecture (easy to extend)  

---

## 🏗️ Architecture


Frontend (Next.js)
↓
VoiceRecorder (Audio Capture)
↓
FastAPI Backend (SSE Streaming)
↓
Transcription (Whisper)
↓
RAG Pipeline (Vector DB + Context)
↓
Parallel LLM Calls (Gemini / Kimi / DeepSeek)
↓
TTS Generation (Audio)
↓
Streaming Response to UI


---

## 📁 Project Structure

```

.
├── services/
│   ├── RAG_service.py
│   ├── llms/
│   │   ├── gemini.py
│   │   ├── kimi.py
│   │   └── deepseek.py
│   └── voice_handling/
│       ├── voice_input.py
│       └── voice_output.py
│
├── db/
│   └── vector_store.py
│
├── temp_audio/          # Generated audio files
├── main.py              # FastAPI app
├── requirements.txt
└── README.md

⚙️ Installation
1️⃣ Clone the repository
git clone <your-repo-url>
cd sunmarke-voice-agent
2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
3️⃣ Install dependencies
pip install -r requirements.txt
4️⃣ Setup environment variables

Create a .env file:

MOONSHOT_API_KEY=your_kimi_api_key
GOOGLE_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key (optional)
🧠 Running the Backend
python main.py

Or:

uvicorn main:app --reload

Server runs at:

http://localhost:8000
🌐 API Endpoints
🎤 POST /api/query-stream

Upload audio and receive streaming responses.

Request:
multipart/form-data
field: file (audio WAV)
Response:
Server-Sent Events (SSE)

Example stream:

data: { "model": "kimi", "text": "...", "audioUrl": "...", "sources": [] }

data: { "model": "gemini", "text": "...", "audioUrl": "...", "sources": [] }
🔊 GET /audio/{file_name}

Returns generated audio file.

🎤 Frontend Integration
Usage:
<VoiceRecorder
  onData={(data) => {
    console.log("Streaming response:", data);
  }}
/>
⚡ How Streaming Works
User records voice
Audio sent to backend
Backend transcribes audio
RAG retrieves context
All LLMs run in parallel
Each model response is streamed immediately
Frontend receives + plays audio instantly
🧠 RAG Pipeline
Vector Store: PGVector
Retrieval: MMR (Max Marginal Relevance)
Top-K: 5 documents
Prompt Engineering:
Friendly assistant tone
No hallucinations
Context-only answering
🤖 Supported Models
Model	Provider
Gemini	Google
Kimi	Moonshot AI
DeepSeek	DeepSeek
🔊 Audio Pipeline
Input:
Microphone → WAV (16kHz)
Processing:
Speech-to-Text (Whisper / Faster-Whisper)
Output:
Text-to-Speech (gTTS)
⚡ Performance Optimizations
✅ Parallel LLM execution (ThreadPool)
✅ Streaming (SSE)
✅ Shared context (retrieval once)
✅ Non-blocking UI updates
❗ Common Issues & Fixes
1. ❌ onData is not a function

✔️ Fix:

<VoiceRecorder onData={(data) => console.log(data)} />
2. ❌ Audio not playing
Check /audio/{file} endpoint
Ensure correct URL (localhost:8000)
3. ❌ Rate limit errors
Gemini / Kimi free tier limits
Add retry or switch model
4. ❌ ffmpeg error

Install ffmpeg:

https://ffmpeg.org/download.html
🔐 Security Notes
Do NOT expose API keys in frontend
Use .env for secrets
Restrict CORS in production
🚀 Future Improvements
🔄 Streaming token-level responses (not full text)
⚡ Async FastAPI (instead of threads)
🧠 Memory / conversation history
📊 Model ranking (best answer selection)
🗣️ Voice cloning TTS
🤝 Contributing

Pull requests are welcome!

📜 License

MIT License

👨‍💻 Author

Built by a passionate AI engineer 🚀