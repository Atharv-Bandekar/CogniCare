import os
import tempfile
import threading
import speech_recognition as sr
from gtts import gTTS
import pygame

# Initialize the audio mixer once
pygame.mixer.init()

# Map UI language names to Google's language codes
LANG_CODES = {
    "English": "en-IN",
    "Hindi": "hi",
    "Marathi": "mr",
    "Tamil": "ta"
}

def play_audio(text, lang_name="English"):
    """Generates TTS and plays it without blocking the main thread."""
    def _speak():
        try:
            lang_code = LANG_CODES.get(lang_name, "en")
            tts = gTTS(text=text, lang=lang_code[:2]) # gTTS uses 2-letter codes mostly
            
            # Save to a temporary file
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(fp.name)
            
            pygame.mixer.music.load(fp.name)
            pygame.mixer.music.play()
            
            # Wait for audio to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            os.unlink(fp.name) # Clean up temp file
        except Exception as e:
            print(f"Audio playback error: {e}")

    threading.Thread(target=_speak, daemon=True).start()

def record_audio(lang_name="English"):
    """Listens to the mic and returns the transcribed text."""
    r = sr.Recognizer()
    lang_code = LANG_CODES.get(lang_name, "en-IN")
    
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=15)
            text = r.recognize_google(audio, language=lang_code)
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"Microphone error: {e}")
            return None