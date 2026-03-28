import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
DURATION = 5  # seconds (you can make dynamic later)

# Load model once
model = WhisperModel("base")

def record_audio(filename="input.wav"):
    print("🎤 Recording... Speak now")
    
    audio = sd.rec(int(SAMPLE_RATE * DURATION),
                   samplerate=SAMPLE_RATE,
                   channels=1,
                   dtype='int16')
    
    sd.wait()
    wav.write(filename, SAMPLE_RATE, audio)
    
    print("✅ Recording complete")
    return filename


def transcribe_audio(file_path):
    segments, _ = model.transcribe(file_path)

    text = " ".join([seg.text for seg in segments])
    
    print(f"🧠 Transcribed: {text}")
    return text