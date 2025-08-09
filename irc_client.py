# irc_client.py
import socket

class IRCClient:
    def __init__(self, server, port, token, bot_nick, channel):
        self.server = server
        self.port = port
        self.token = token
        self.bot_nick = bot_nick
        self.channel = channel
        self.sock = socket.socket()

    def connect(self):
        """Connects to the Twitch IRC server and joins the channel."""
        print(f"Connecting to {self.server}:{self.port}...")
        self.sock.connect((self.server, self.port))
        self.sock.send(f"PASS {self.token}\r\n".encode("utf-8"))
        self.sock.send(f"NICK {self.bot_nick}\r\n".encode("utf-8"))
        self.sock.send(f"JOIN #{self.channel}\r\n".encode("utf-8"))
        print("---")
        print(f"✅ Connected to #{self.channel} as {self.bot_nick}")
        print("---")

    def send_privmsg(self, message):
        """Sends a chat message to the channel."""
        print(f"[{self.bot_nick}]: {message}")
        self.sock.send(f"PRIVMSG #{self.channel} :{message}\r\n".encode("utf-8"))

    def listen_for_messages(self):
        """Listens for messages and yields them as they come in."""
        while True:
            resp = self.sock.recv(2048).decode("utf-8")
            
            if resp.startswith("PING"):
                self.sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                print("--> PONG sent")
            
            elif "PRIVMSG" in resp:
                try:
                    parts = resp.split(":", 2)
                    username = parts[1].split("!")[0]
                    message = parts[2].strip()
                    yield username, message
                except IndexError:
                    continue # Ignore malformed messages