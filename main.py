import os
import socket
from dotenv import load_dotenv
import google.generativeai as genai # <-- INTEGRATED

# --- Step 1: Load environment variables ---
load_dotenv()

BOT_NICK = os.getenv("BOT_NICK")
CHANNEL = os.getenv("CHANNEL_NAME")
OAUTH_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # <-- INTEGRATED

# --- Step 2: Configuration ---
SERVER = "irc.chat.twitch.tv"
PORT = 6667

# A constant defining Lorelei's personality for the AI model. # <-- INTEGRATED
SYSTEM_PROMPT = f"""
You are Lorelei, a friendly and helpful AI chatbot in the Twitch channel of "{CHANNEL}".
Your personality is witty, concise, and engaging.
Keep your messages short and conversational, perfect for a fast-moving Twitch chat.
Avoid using emojis or emoticons. Do not repeat the user's question.
"""

# A list to store the recent chat history for context. # <-- INTEGRATED
chat_history = []
MAX_HISTORY_LENGTH = 10 

# --- Helper Function ---
def send_message(sock, message):
    """Encodes and sends a message to the Twitch IRC server."""
    print(f"[{BOT_NICK}]: {message}")
    sock.send(f"PRIVMSG #{CHANNEL} :{message}\r\n".encode("utf-8"))

# --- Main Bot Function ---
def main():
    global chat_history # <-- Add this line
    
    # --- Gemini AI Model Setup ---
    print("Configuring Gemini API...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=SYSTEM_PROMPT
    )
    print("Gemini model created.")
    
    # --- Twitch Connection ---
    sock = socket.socket()
    sock.connect((SERVER, PORT))
    sock.send(f"PASS {OAUTH_TOKEN}\r\n".encode("utf-8"))
    sock.send(f"NICK {BOT_NICK}\r\n".encode("utf-8"))
    sock.send(f"JOIN #{CHANNEL}\r\n".encode("utf-8"))
    print("---")
    print(f"✅ Connected to #{CHANNEL} as {BOT_NICK}")
    print("---")

    # --- Main Loop ---
    while True:
        resp = sock.recv(2048).decode("utf-8")

        if resp.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            print("--> PONG sent")

        if "PRIVMSG" in resp:
            try:
                parts = resp.split(":", 2)
                username = parts[1].split("!")[0]
                message = parts[2].strip()
                print(f"[{username}]: {message}")
            except IndexError:
                continue

            if username.lower() == "remmold":
                try:
                    chat_history.append({"role": "user", "parts": [message]})
                    
                    chat_session = model.start_chat(history=chat_history)
                    response = chat_session.send_message(message)
                    
                    chat_history.append({"role": "model", "parts": [response.text]})

                    if len(chat_history) > MAX_HISTORY_LENGTH:
                        chat_history = chat_history[2:]

                    send_message(sock, response.text)

                except Exception as e:
                    print(f"❌ An error occurred with the Gemini API: {e}")
                    send_message(sock, "Sorry, I'm having trouble thinking right now.")


if __name__ == "__main__":
    main()