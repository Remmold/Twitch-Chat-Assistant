# gemini_handler.py
import google.generativeai as genai
import json
import re

class GeminiHandler:
    def __init__(self, api_key, system_prompt, max_history, memory_handler):
        print("Configuring Gemini API...")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt
        )
        self.history = []
        self.max_history = max_history
        self.memory_handler = memory_handler
        print("Gemini model created.")

    def _process_ai_commands(self, response_text):
        """Parses the AI's response for memory commands and executes them."""
        lines = response_text.split('\n')
        cleaned_lines = []
        
        learn_pattern = re.compile(r'\[LEARN\] (.*)')

        for line in lines:
            learn_match = learn_pattern.match(line)

            if learn_match:
                try:
                    data = json.loads(learn_match.group(1))
                    self.memory_handler.learn_fact(data['topic'], data['fact'])
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[ERROR] Could not parse LEARN command: {e}")
                continue
            
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def get_response(self, user_prompt):
        """Gets an AI response, managing history and structured memory."""
        try:
            # Get the formatted memory string
            memory_string = self.memory_handler.get_memory_for_prompt()
            prompt_with_memory = f"{memory_string}\n{user_prompt}"

            self.history.append({"role": "user", "parts": [prompt_with_memory]})
            
            chat_session = self.model.start_chat(history=self.history)
            response = chat_session.send_message(prompt_with_memory)
            
            cleaned_response_text = self._process_ai_commands(response.text)

            self.history.append({"role": "model", "parts": [cleaned_response_text]})
            
            if len(self.history) > self.max_history:
                self.history = self.history[2:]
            
            return cleaned_response_text

        except Exception as e:
            print(f"❌ An error occurred with the Gemini API: {e}")
            if self.history and self.history[-1]['role'] == 'user':
                self.history.pop()
            return "Sorry, I'm having a bit of brain fog right now."