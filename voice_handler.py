# voice_handler.py
import speech_recognition as sr
import threading
import time

class VoiceHandler:
    def __init__(self, on_speech_recognized_callback):
        self.recognizer = sr.Recognizer()
        # --- NEW: Increase the pause threshold ---
        # This allows for longer pauses within a sentence. The default is 0.8.
        self.recognizer.pause_threshold = 2.0  # seconds

        self.microphone = sr.Microphone()
        self.callback = on_speech_recognized_callback
        with self.microphone as source:
            print("🎤 Calibrating microphone for ambient noise... Please be quiet for a moment.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Microphone calibrated.")

    def _listen_in_background(self):
        """This function will run in a separate thread."""
        while True:
            try:
                with self.microphone as source:
                    print("🎤 Listening for voice command...")
                    # --- NEW: Added a phrase time limit ---
                    # This sets an absolute max duration for a single utterance.
                    audio = self.recognizer.listen(source, phrase_time_limit=15)
                
                print("🧠 Recognizing speech...")
                text = self.recognizer.recognize_google(audio)
                print(f"💬 You said: \"{text}\"")
                
                self.callback(text)

            except sr.WaitTimeoutError:
                # This error happens if no speech is detected for a while. It's safe to ignore.
                pass
            except sr.UnknownValueError:
                pass 
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
                time.sleep(5)
            except Exception as e:
                print(f"An unknown error occurred in voice handler: {e}")

    def start(self):
        """Starts the background listening thread."""
        print("Starting voice handler thread...")
        thread = threading.Thread(target=self._listen_in_background, daemon=True)
        thread.start()