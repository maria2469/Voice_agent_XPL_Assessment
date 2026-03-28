from gtts import gTTS
import os

def text_to_speech(text, filename):
    tts = gTTS(text)
    tts.save(filename)
    return filename