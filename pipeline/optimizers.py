from agents import *
from constants import MAX_TOKENS
from google.generativeai import GenerationConfig
import json

# prompt should be like {prompt} \n\n "here is the code: " \n\n {code}

class GeminiOptimizer(GeminiAgent):
    def __init__(self) -> None:
        super().__init__()
        self.generate = self._gemini_gen
        self.name = "25"

    def _gemini_gen(self, prompt : str, snippet : str, scope : str):
        schema = {"type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"]}
        
        response = self.client.generate_content(
            contents=assemble_prompt(prompt, snippet, scope),
            generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema, 
            max_output_tokens=MAX_TOKENS))
        
        return json.loads(response.text)["code"]

class OpenOptimizer(OpenAIAgent):
    def __init__(self) -> None:
        super().__init__()
        self.generate = self._openai_gen
        self.name = "4o"

    def _openai_gen(self, prompt : str, snippet : str, scope : str):
        schema = {
            "type": "object",
            "properties": {"code": {"type": "string"}}, 
            "required": ["code"],
            "additionalProperties": False
        }

        completion = self.client.chat.completions.create(
            model="gpt-4o", 
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_schema", "json_schema": {"name": "code_response", "schema": schema, "strict": True}},
            messages=[
                {"role": "system", "content": "Return ONLY the optimized code in the 'code' field. Include only executable code in this field, and exclude any comments, explanations, markdown formatting, or additional text."},
                {"role": "user", "content": assemble_prompt(prompt, snippet, scope)}
            ])
        
        return json.loads(completion.choices[0].message.content)["code"]

class AnthroOptimizer(AnthroAgent):
    def __init__(self) -> None:
        super().__init__()        
        self.generate = self._anthropic_gen
        self.name = "40"

    def _anthropic_gen(self, prompt : str, snippet : str, scope : str):
        code_tool={"name": "code_output", 
                "description": "Return only code", 
                "input_schema": 
                {"type": "object", "properties": {"code": {"type": "string"}},
                 "required": ["code"]}}
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514", 
            max_tokens=MAX_TOKENS, 
            messages=[{"role": "user", "content": assemble_prompt(prompt, snippet, scope)}],
            tools=[code_tool],
            tool_choice={"type": "tool", "name": "code_output"})

        for block in response.content:
            if block.type == "tool_use" and block.name == "code_output":
                return block.input["code"]
    
        raise ValueError("No code_output tool use found in response")
    
def assemble_prompt(prompt : str, snippet : str, scope : str) -> str:
    return f"{prompt}\n\nObject to be optimized:\n\n{snippet}\n\nEnclosing scope of object:\n\n{scope}"

