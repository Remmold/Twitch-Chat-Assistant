import os
import socket
from dotenv import load_dotenv

load_dotenv()

BOT_NICK = os.getenv("BOT_NICK")
CHANNEL = os.getenv("CHANNEL_NAME")
OAUTH_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")

# Twitch IRC server info
SERVER = "irc.chat.twitch.tv"
PORT = 6667

def send_message(sock, message):
    sock.send(f"PRIVMSG #{CHANNEL} :{message}\r\n".encode("utf-8"))

def main():
    sock = socket.socket()
    sock.connect((SERVER, PORT))

    # Authenticate with Twitch IRC
    sock.send(f"PASS {OAUTH_TOKEN}\r\n".encode("utf-8"))
    sock.send(f"NICK {BOT_NICK}\r\n".encode("utf-8"))
    sock.send(f"JOIN #{CHANNEL}\r\n".encode("utf-8"))

    print(f"Connected to #{CHANNEL} as {BOT_NICK}")

    while True:
        resp = sock.recv(2048).decode("utf-8")

        if resp.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            print("PONG sent")

        if "PRIVMSG" in resp:
            parts = resp.split(":", 2)
            if len(parts) < 3:
                continue

            username = parts[1].split("!")[0]
            message = parts[2].strip()

            print(f"{username}: {message}")

            if username.lower() == "remmold":  # your Twitch username here
                # Respond to any message from remmold
                send_message(sock, f"Hey @{username}, you said: {message}")


if __name__ == "__main__":
    main()
