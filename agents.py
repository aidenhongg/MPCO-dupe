from constants import GEMINI_KEY, OPENAI_KEY, ANTHROPIC_KEY

class GeminiAgent():
    def __init__(self) -> None:
        from google import generativeai
        generativeai.configure(api_key=GEMINI_KEY)
        self.client = generativeai.GenerativeModel("gemini-2.5-pro")
        self.model_name = "25"

class OpenAIAgent():
    def __init__(self) -> None:
        from openai import OpenAI
        self.client = OpenAI(api_key=OPENAI_KEY)
        self.model_name = "4o"

class AnthroAgent():
    def __init__(self) -> None:
        from anthropic import Anthropic
        self.client = Anthropic(api_key=ANTHROPIC_KEY)
        self.model_name = "27"