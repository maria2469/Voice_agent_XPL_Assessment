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

🔷 High-Level Flow
User (Voice Input)
        ↓
Frontend (Next.js + Web Audio API)
        ↓
FastAPI Backend (Streaming SSE)
        ↓
Speech-to-Text (Whisper / STT)
        ↓
RAG Pipeline
   ├── Vector DB (PGVector)
   ├── Retriever (MMR)
   └── Prompt Builder
        ↓
Parallel LLM Calls
   ├── Gemini
   ├── DeepSeek
   └── Kimi (OpenRouter)
        ↓
Streaming Response (as each finishes)
        ↓
Text-to-Speech (TTS)
        ↓
Audio + Text streamed to UI
🔷 Key Design Decisions
1. Single Retrieval, Multi-LLM
Documents are retrieved once
Shared across all LLMs
✅ Reduces latency + cost
2. Parallel LLM Execution
Uses ThreadPoolExecutor
Each model runs independently
✅ Fastest model responds first
3. Streaming (SSE)
Backend streams results:
data: {model: "kimi", ...}
data: {model: "deepseek", ...}
Frontend processes chunk-by-chunk
✅ No waiting for all models
4. Streaming TTS
As soon as a model finishes:
TTS is generated
Audio is streamed back
✅ Real-time voice feedback
5. Model Routing Strategy
Model	Role
Gemini	Fast / general
DeepSeek	Best cost-performance
Kimi	Reasoning / long answers
📄 2. Assumptions & Limitations
🔷 Assumptions
Average query:
Input tokens: ~1,000
Output tokens: ~300
3 LLMs called per request
Audio duration: ~5–10 seconds
TTS cost is negligible (local or cheap API)
🔷 Limitations
1. 🚫 Rate Limits
Gemini free tier → easily exhausted
Kimi (Moonshot/OpenRouter) → strict rate limits
DeepSeek → more stable
2. ⚠️ Cost Multiplication
You are calling 3 LLMs per query
Cost = 3× compared to single-model systems
3. ⚠️ Latency Variance
Some models (Kimi reasoning) slower
Streaming mitigates this
4. ⚠️ Token Explosion (Hidden Cost)
Some models use extra “thinking tokens”
Real cost may be higher than expected
5. ⚠️ No Smart Routing (Yet)

Currently:

ALL models are called every time

Better future:

Route based on query complexity
📄 3. Estimated Cost per 1,000 Queries
🔷 Latest Pricing (2026)
🟢 Gemini Flash
Input: ~$0.10 / 1M tokens
Output: ~$0.40 / 1M tokens
🔵 DeepSeek V3.2
Input: ~$0.28 / 1M
Output: ~$0.42 / 1M
🟣 OpenRouter (Kimi / similar class)
Rough estimate: ~$0.50–$2 / 1M tokens (varies)
🔷 Cost Per Query (Estimate)

Assume:

Input: 1,000 tokens
Output: 300 tokens
🧮 Per Model Cost
Gemini
= (1000 * 0.10/1M) + (300 * 0.40/1M)
≈ $0.00010 + $0.00012
≈ $0.00022
DeepSeek
≈ $0.00028 + $0.00013
≈ $0.00041
Kimi (OpenRouter estimate)
≈ $0.001 – $0.002
🔷 Total Per Query (3 Models)
≈ 0.00022 + 0.00041 + 0.0015
≈ $0.0021 per query
🔷 Cost per 1,000 Queries
≈ $2.1 per 1000 queries
🔷 Realistic Range
Scenario	Cost
Optimized (2 models)	$1.2 / 1000
Current (3 models)	~$2–3 / 1000
Worst case (long outputs)	$5+ / 1000

Built by a passionate AI engineer 🚀