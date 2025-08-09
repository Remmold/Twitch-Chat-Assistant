# gemini_handler.py
import google.generativeai as genai

class GeminiHandler:
    def __init__(self, api_key, system_prompt, max_history):
        print("Configuring Gemini API...")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt # The new, smarter prompt is used here
        )
        self.history = []
        self.max_history = max_history
        print("Gemini model created.")

    def get_response(self, user_prompt):
        """Gets an AI response, managing a single, unified chat history."""
        try:
            # We now use one continuous history for all interactions
            self.history.append({"role": "user", "parts": [user_prompt]})
            
            chat_session = self.model.start_chat(history=self.history)
            response = chat_session.send_message(user_prompt)
            
            self.history.append({"role": "model", "parts": [response.text]})
            
            if len(self.history) > self.max_history:
                self.history = self.history[2:]
            
            return response.text

        except Exception as e:
            print(f"❌ An error occurred with the Gemini API: {e}")
            if self.history and self.history[-1]['role'] == 'user':
                self.history.pop()
            return "Sorry, I'm having a bit of brain fog right now."