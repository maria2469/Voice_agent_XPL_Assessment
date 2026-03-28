from services.RAG_service import RAGService
from services.voice_handling.voice_input import record_audio, transcribe_audio
from services.voice_handling.voice_output import text_to_speech
from concurrent.futures import ThreadPoolExecutor, as_completed

rag = RAGService()

print("🎤 Voice Agent Ready! Press ENTER to speak or type 'exit'.")

while True:
    cmd = input("\n>> ")
    if cmd.lower() == "exit":
        break

    # --------------------------
    # Step 1: Record Audio
    # --------------------------
    audio_file = record_audio()

    # --------------------------
    # Step 2: Transcribe
    # --------------------------
    user_query = transcribe_audio(audio_file)
    if not user_query.strip():
        print("❌ Could not understand audio")
        continue

    print(f"📝 You said: {user_query}")
    print("🤖 Processing with all LLMs...")

    # --------------------------
    # Step 3: Multi-RAG (Parallel)
    # --------------------------
    results = rag.query_multi(user_query)

    # --------------------------
    # Step 4: Text-to-Speech in Parallel
    # --------------------------
    def tts_task(model_name, answer_text):
        file_name = f"{model_name}.mp3"
        text_to_speech(answer_text, file_name)
        return model_name, file_name

    # Use ThreadPoolExecutor to generate all audio simultaneously
    with ThreadPoolExecutor(max_workers=len(results)) as executor:
        futures = [
            executor.submit(tts_task, model, res["answer"])
            for model, res in results.items()
        ]

        # Display text and TTS progress
        for future in as_completed(futures):
            model_name, audio_file_path = future.result()
            print(f"\n===== {model_name.upper()} =====")
            print(results[model_name]["answer"])
            print(f"🔊 Audio saved: {audio_file_path}")

print("👋 Voice Agent terminated.")