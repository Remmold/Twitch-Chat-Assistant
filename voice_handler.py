import speech_recognition as sr
import threading
import time

class VoiceHandler:
    def __init__(self, on_speech_recognized_callback):
        self.recognizer = sr.Recognizer()
        
        # --- NEW: Increase the pause threshold ---
        # The default is 0.8 seconds. We're increasing it to 2.0 seconds,
        # allowing for longer pauses within a single sentence.
        self.recognizer.pause_threshold = 2.0

        self.microphone = sr.Microphone()
        self.main_callback = on_speech_recognized_callback
        self.stop_listening = None

        with self.microphone as source:
            print("🎤 Calibrating microphone for ambient noise... Please be quiet for a moment.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Microphone calibrated.")

    def _background_listener_callback(self, recognizer, audio):
        """
        This callback is called by listen_in_background when a phrase is detected.
        It runs in the background thread.
        """
        print("🧠 Recognizing speech...")
        try:
            text = recognizer.recognize_google(audio)
            print(f"💬 You said: \"{text}\"")
            
            self.main_callback(text)

        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
        except Exception as e:
            print(f"An unknown error occurred during speech recognition: {e}")

    def start(self):
        """
        Starts the background listening thread using the library's built-in method.
        """
        print("Starting background voice listener...")
        
        self.stop_listening = self.recognizer.listen_in_background(
            self.microphone, 
            self._background_listener_callback,
            # --- NEW: Set a maximum recording time ---
            # This sets a hard limit on the length of a single utterance.
            # We'll set it to 15 seconds to allow for longer thoughts.
            phrase_time_limit=15 
        )
        print("🎤 Listening for voice commands in the background (with longer pause detection)...")