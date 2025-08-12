# main.py
from irc_client import IRCClient
from gemini_handler import GeminiHandler
from voice_handler import VoiceHandler
from memory_handler import MemoryHandler
import config
import time
import random
import threading
import queue
import os
import shutil
from datetime import datetime

def main():
    # --- Queues ---
    voice_command_queue = queue.Queue()

    # --- State Management ---
    bot_state = {
        'is_waiting_for_reply': False,
        'last_question_time': 0,
        'last_activity_time': time.time(),
        'last_streamer_utterance': None,
        'inactivity_prompt_sent': False,
        'last_ai_call_time': 0,
    }
    REPLY_TIMEOUT = 60

    # --- Initialize Handlers ---
    memory_handler = MemoryHandler(config.MEMORY_FILE)
    if os.path.exists(config.MEMORY_FILE):
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            base, ext = os.path.splitext(config.MEMORY_FILE)
            backup_path = f"{base}_backup_{timestamp}{ext}"
            shutil.copy2(config.MEMORY_FILE, backup_path)
            print(f"✅ Created memory backup at: {backup_path}")
        except Exception as e:
            print(f"[ERROR] Could not create memory backup: {e}")

    ai_handler = GeminiHandler(
        api_key=config.GEMINI_API_KEY,
        system_prompt=config.SYSTEM_PROMPT,
        max_history=config.MAX_HISTORY_LENGTH,
        memory_handler=memory_handler
    )
    
    irc_client = IRCClient(
        server=config.SERVER,
        port=config.PORT,
        token=config.OAUTH_TOKEN,
        bot_nick=config.BOT_NICK,
        channel=config.CHANNEL
    )

    # --- Voice Logic (Queueing) ---
    def on_voice_recognized(text):
        """This function adds the recognized text to a queue for processing."""
        print(f"✅ Voice command queued: '{text}'")
        voice_command_queue.put(text)

    # --- Dedicated Voice Command Processor ---
    def process_voice_commands():
        """
        This function runs in a separate thread, processing voice commands from the queue
        one by one, respecting the AI cooldown.
        """
        while True:
            text = voice_command_queue.get()

            # Cooldown Logic acts as a "thinking" delay
            time_since_last_call = time.time() - bot_state['last_ai_call_time']
            if time_since_last_call < config.AI_CALL_COOLDOWN:
                wait_time = config.AI_CALL_COOLDOWN - time_since_last_call
                print(f"[COOLDOWN] Waiting for {wait_time:.1f}s before processing next voice command...")
                time.sleep(wait_time)
            
            # Original processing logic is now here
            bot_state['last_streamer_utterance'] = text
            is_direct_mention = any(nick in text.lower() for nick in config.BOT_NICKNAMES)

            if bot_state['is_waiting_for_reply']:
                time_since_last_q = time.time() - bot_state['last_question_time']
                if time_since_last_q > REPLY_TIMEOUT:
                    print("--> Reply timeout. Forgetting previous question.")
                    bot_state['is_waiting_for_reply'] = False

            if is_direct_mention or bot_state['is_waiting_for_reply']:
                print("[STATE] Active conversation state.")
                prompt_for_ai = text
                if is_direct_mention:
                    bot_state['is_waiting_for_reply'] = False
            else:
                time_since_last_chat = time.time() - bot_state['last_activity_time']
                if time_since_last_chat < config.CHAT_SILENCE_THRESHOLD:
                    print(f"[STATE] Inactive. Ignoring ambient chatter.")
                    continue 
                print("--> Processing as a new topic (from voice)...")
                prompt_for_ai = f'The streamer, {config.PRIVILEGED_USER}, just said: "{text}"'

            bot_state['last_ai_call_time'] = time.time()
            ai_response = ai_handler.get_response(prompt_for_ai)

            if "IGNORE" in ai_response.upper():
                print("--> AI decided to ignore the voice command. Staying silent.")
                continue

            if ai_response.endswith('?'):
                bot_state['is_waiting_for_reply'] = True
                bot_state['last_question_time'] = time.time()
                print("[STATE] Awaiting reply. Conversation remains active.")
            else:
                bot_state['is_waiting_for_reply'] = False
                print("[STATE] Concluded topic. Conversation is now inactive.")

            irc_client.send_privmsg(ai_response)
            bot_state['last_activity_time'] = time.time()
            print("[INFO] Bot activity timer updated.")

    # --- Start Services ---
    voice_handler = VoiceHandler(on_speech_recognized_callback=on_voice_recognized)
    voice_handler.start()
    irc_client.start()
    
    voice_processor_thread = threading.Thread(target=process_voice_commands, daemon=True)
    voice_processor_thread.start()
    print("🗣️ Voice command processor thread started.")

    # --- Main Application Loop (OVERHAULED Inactivity Logic) ---
    while True:
        try:
            username, message = irc_client.message_queue.get(timeout=1.0)
            
            print(f"[{username}]: {message}")
            bot_state['last_activity_time'] = time.time()
            bot_state['inactivity_prompt_sent'] = False

            if message.lower().startswith("!lor"):
                time_since_last_call = time.time() - bot_state['last_ai_call_time']
                if time_since_last_call < config.AI_CALL_COOLDOWN:
                    print(f"[COOLDOWN] !lor command ignored due to AI cooldown.")
                    continue

                prompt_for_ai = message[len('!lor'):].strip()
                if not prompt_for_ai:
                    irc_client.send_privmsg(f"Hi @{username}! To use me, type !lor followed by your question.")
                    continue
                
                bot_state['last_ai_call_time'] = time.time()
                ai_response = ai_handler.get_response(prompt_for_ai)
                
                irc_client.send_privmsg(ai_response)
                bot_state['last_activity_time'] = time.time()

        except queue.Empty:
            # This block runs when no messages are in the queue (i.e., chat is quiet)
            time_since_activity = time.time() - bot_state['last_activity_time']
            
            if (time_since_activity > config.INACTIVITY_THRESHOLD and 
                not bot_state['inactivity_prompt_sent']):
                
                time_since_last_call = time.time() - bot_state['last_ai_call_time']
                if time_since_last_call < config.AI_CALL_COOLDOWN:
                    print(f"[COOLDOWN] Inactivity prompt skipped due to recent AI activity.")
                    bot_state['inactivity_prompt_sent'] = True
                    continue

                print("[INFO] 5 minutes of inactivity detected. Engaging proactive question mode...")
                
                # Check if the current game is known
                if "Current Game" not in memory_handler.memory:
                    prompt_for_ai = "It's quiet and you don't know the current game. Ask the streamer what they are playing."
                else:
                    prompt_for_ai = "It's quiet. Based on your memory, ask an interesting, open-ended question to learn more about an existing topic (like the current game or the streamer's preferences)."
                
                bot_state['last_ai_call_time'] = time.time()
                ai_response = ai_handler.get_response(prompt_for_ai)
                bot_state['inactivity_prompt_sent'] = True 

                if "IGNORE" not in ai_response.upper():
                    print(f"--> AI generated proactive question: {ai_response}")
                    irc_client.send_privmsg(ai_response)
                    bot_state['last_activity_time'] = time.time()
                    print("[INFO] Bot activity timer updated.")
                else:
                    print("--> AI decided not to ask a question right now.")

        except KeyboardInterrupt:
            print("\nScript interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()