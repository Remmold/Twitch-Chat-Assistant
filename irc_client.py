# irc_client.py
import socket
import threading
import queue
import time

class IRCClient:
    def __init__(self, server, port, token, bot_nick, channel):
        self.server = server
        self.port = port
        self.token = token
        self.bot_nick = bot_nick
        self.channel = channel
        
        self.sock = socket.socket()
        self.message_queue = queue.Queue()
        self.is_connected = False
        self._stop_event = threading.Event()

    def connect(self):
        """Connects to the Twitch IRC server and joins the channel."""
        print(f"Connecting to {self.server}:{self.port}...")
        self.sock = socket.socket()
        self.sock.connect((self.server, self.port))
        
        # --- FINAL FIX: Ensure the token has the 'oauth:' prefix ---
        # This resolves the authentication rejection from the Twitch server.
        formatted_token = self.token if self.token.startswith("oauth:") else f"oauth:{self.token}"
        
        self.sock.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n".encode("utf-8"))
        self.sock.send(f"PASS {formatted_token}\r\n".encode("utf-8"))
        self.sock.send(f"NICK {self.bot_nick}\r\n".encode("utf-8"))
        self.sock.send(f"JOIN #{self.channel}\r\n".encode("utf-8"))
        
        self.is_connected = True
        self._stop_event.clear()

    # (The rest of the file remains the same as the previous version)
    # _listen_thread, start, _connection_manager, and send_privmsg
    # do not need any further changes.
    # irc_client.py -> _listen_thread function

    def _listen_thread(self):
        """Listens for all incoming messages and handles server commands."""
        while not self._stop_event.is_set():
            try:
                resp = self.sock.recv(4096).decode("utf-8")
                if not resp:
                    print("[INFO] Connection stream empty. Closing connection.")
                    self.is_connected = False
                    break

                for line in resp.strip().split("\r\n"):
                    # --- NEW: Print every single raw message from the server for diagnosis ---
                    print(f"<<< {line}") 

                    if line.startswith("PING"):
                        self.sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                        print("[INFO] Responded to server PING.")
                        continue

                    if "RECONNECT" in line:
                        print("[INFO] Server requested a reconnect. Re-establishing connection...")
                        self.is_connected = False
                        break 

                    if "001" in line:
                        print("✅ Bot has successfully logged in and is ready.")
                        print("---")

                    if "PRIVMSG" in line:
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            username = parts[1].split("!")[0]
                            message = parts[2]
                            self.message_queue.put((username, message))

            except (ConnectionResetError, ConnectionAbortedError, OSError):
                print("[ERROR] Connection was lost.")
                self.is_connected = False
                break
            except Exception as e:
                print(f"[ERROR] An unexpected error occurred in the listen thread: {e}")
                self.is_connected = False
                break
        
        self.is_connected = False
        self._stop_event.set()
        self.sock.close()
        print("[INFO] IRC listener thread has stopped.")


    def start(self):
        """Starts a master thread that connects and maintains the connection."""
        master_thread = threading.Thread(target=self._connection_manager, daemon=True)
        master_thread.start()
        print("🤖 Bot services started.")

    def _connection_manager(self):
        """Keeps the bot connected, attempting to reconnect on failure."""
        while not self._stop_event.is_set():
            try:
                self.connect()
                # The "✅ Connected" printout is now moved to after a successful login (001)
                # print("---")
                # print(f"✅ Connected to #{self.channel} as {self.bot_nick}")
                # print("---")

                listen_thread = threading.Thread(target=self._listen_thread)
                listen_thread.start()
                listen_thread.join()
            except Exception as e:
                print(f"[ERROR] Connection manager failed: {e}")

            if not self._stop_event.is_set():
                print("Attempting to reconnect in 5 seconds...")
                time.sleep(5)


    def send_privmsg(self, message):
        """Sends a chat message to the channel, now with error handling."""
        if not self.is_connected:
            print("[WARN] Cannot send message, not connected.")
            return
        try:
            print(f"[{self.bot_nick}]: {message}")
            self.sock.send(f"PRIVMSG #{self.channel} :{message}\r\n".encode("utf-8"))
        except OSError as e:
            print(f"[ERROR] Failed to send message: {e}")
            self.is_connected = False