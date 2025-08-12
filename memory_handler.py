# memory_handler.py
import json
import os

class MemoryHandler:
    def __init__(self, filepath):
        self.filepath = filepath
        self.memory = self._load_memory()

    def _load_memory(self):
        """Loads the topic-based dictionary from the JSON file."""
        if not os.path.exists(self.filepath):
            print(f"[INFO] Memory file not found. Creating a new one at {self.filepath}")
            with open(self.filepath, 'w') as f:
                json.dump({}, f)
            return {}
        
        try:
            with open(self.filepath, 'r') as f:
                print("[INFO] Loading facts from memory bank...")
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ERROR] Could not read memory file: {e}. Starting with empty memory.")
            return {}

    def _save_memory(self):
        """Saves the current memory dictionary back to the JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.memory, f, indent=4)
        except IOError as e:
            print(f"[ERROR] Could not save memory file: {e}")

    def learn_fact(self, topic, fact, category="General"):
        """Adds a new fact to a specific topic in memory."""
        # Normalize topic for consistency
        topic = topic.strip()
        fact = fact.strip()

        if not topic or not fact:
            return

        if topic not in self.memory:
            print(f"[MEMORY] Creating new topic: '{topic}'")
            self.memory[topic] = {"category": category, "facts": []}

        if fact not in self.memory[topic]["facts"]:
            print(f"[MEMORY] Learning new fact for topic '{topic}': '{fact}'")
            self.memory[topic]["facts"].append(fact)
            self._save_memory()

    def forget_topic(self, topic):
        """Removes an entire topic and all its facts from memory."""
        if topic in self.memory:
            print(f"[MEMORY] Forgetting entire topic: '{topic}'")
            del self.memory[topic]
            self._save_memory()

    def get_memory_for_prompt(self):
        """Formats the entire memory for injection into the AI prompt."""
        if not self.memory:
            return ""
        
        formatted_string = "[MEMORY] You have learned the following:\n"
        for topic, data in self.memory.items():
            facts_str = "; ".join(data.get("facts", []))
            formatted_string += f'- Topic: {topic} | Facts: {facts_str}\n'
        return formatted_string