"""
AIKO HEARING ENGINE
Speech-to-Text capabilities using SpeechRecognition (Google API default) or Whisper if available.
"""

import asyncio
import threading

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False
    print(" [!] SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")

class HearingEngine:
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        if HAS_SR:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                # Adjust for ambient noise once at startup
                # with self.microphone as source:
                #     self.recognizer.adjust_for_ambient_noise(source)
            except Exception as e:
                print(f" [!] Microphone init failed: {e}")
                self.microphone = None

    def is_available(self):
        return HAS_SR and self.microphone is not None

    def listen_sync(self):
        """Blocking listen."""
        if not self.is_available(): return None
        
        try:
            with self.microphone as source:
                # Fast adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print(" [Ear] Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            print(" [Ear] Processing...")
            text = self.recognizer.recognize_google(audio)
            print(f" [Ear] Heard: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None # Unintelligible
        except Exception as e:
            print(f" [Ear] Error: {e}")
            return None

    async def listen_async(self):
        """Async wrapper for listening."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.listen_sync)
