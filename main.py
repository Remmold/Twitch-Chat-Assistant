# main.py
from irc_client import IRCClient
from gemini_handler import GeminiHandler
from voice_handler import VoiceHandler
import config
import time
import random

def main():
    # --- State Management ---
    bot_state = {
        'is_waiting_for_reply': False,
        'last_question_time': 0,
        'last_activity_time': time.time()
    }
    REPLY_TIMEOUT = 60 

    # --- Initialize Handlers ---
    # (No changes needed here)
    ai_handler = GeminiHandler(
        api_key=config.GEMINI_API_KEY,
        system_prompt=config.SYSTEM_PROMPT,
        max_history=config.MAX_HISTORY_LENGTH
    )
    
    # This is the correct way to initialize the IRC client as well.
    irc_client = IRCClient(
        server=config.SERVER,
        port=config.PORT,
        token=config.OAUTH_TOKEN,
        bot_nick=config.BOT_NICK,
        channel=config.CHANNEL
    )

    # --- The Core Logic for Handling Your Voice ---
    def on_voice_recognized(text):
        """This function is called by the voice handler thread."""
        print(f"✅ Voice command received: '{text}'")

        # --- MODIFIED: Check for any nickname in the list ---
        # The 'any()' function returns True if any item in the list is found.
        is_direct_mention = any(nick in text.lower() for nick in config.BOT_NICKNAMES)
        
        # (The rest of this function remains the same)
        if bot_state['is_waiting_for_reply']:
            time_since_last_q = time.time() - bot_state['last_question_time']
            if time_since_last_q > REPLY_TIMEOUT:
                print("--> Reply timeout. Forgetting previous question.")
                bot_state['is_waiting_for_reply'] = False

        if is_direct_mention or bot_state['is_waiting_for_reply']:
            print("--> Processing as a direct interaction...")
            prompt_for_ai = text
            if is_direct_mention:
                bot_state['is_waiting_for_reply'] = False
        else:
            time_since_last_chat = time.time() - bot_state['last_activity_time']
            if time_since_last_chat < config.CHAT_SILENCE_THRESHOLD:
                print(f"--> Chat is active. Ignoring ambient chatter.")
                return 
            
            print("--> Processing as a new topic...")
            prompt_for_ai = f'The streamer, {config.PRIVILEGED_USER}, just said: "{text}"'
        
        ai_response = ai_handler.get_response(prompt_for_ai)
        
        if ai_response.endswith('?'):
            print("--> Bot asked a question. Waiting for reply.")
            bot_state['is_waiting_for_reply'] = True
            bot_state['last_question_time'] = time.time()
        else:
            bot_state['is_waiting_for_reply'] = False

        # Reinstate the chat delay
        delay = random.uniform(2.0, 4.5)
        print(f"--> Simulating typing delay for {delay:.2f} seconds...")
        time.sleep(delay)
        
        irc_client.send_privmsg(ai_response)

    # (The rest of the file is unchanged)
    voice_handler = VoiceHandler(on_speech_recognized_callback=on_voice_recognized)
    voice_handler.start()
    irc_client.connect()
    
    for username, message in irc_client.listen_for_messages():
        print(f"[{username}]: {message}")
        bot_state['last_activity_time'] = time.time()
        if message.lower().startswith("!lor"):
            prompt_for_ai = message[len('!lor'):].strip()
            if not prompt_for_ai:
                irc_client.send_privmsg(f"Hi @{username}! To use me, type !lor followed by your question.")
                continue
            
            ai_response = ai_handler.get_response(prompt_for_ai)
            
            # Keep the delay for text commands as well
            time.sleep(random.uniform(1.5, 3.0))
            irc_client.send_privmsg(ai_response)

if __name__ == "__main__":
    main()