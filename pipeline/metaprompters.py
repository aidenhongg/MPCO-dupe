from constants import MP_TEMPLATE, PROJECTS, TASKS, PROJECT_CONTEXTS, TASK_CONTEXTS, MODEL_CONTEXTS, MAX_TOKENS
from agents import *

class InvalidTask(Exception):
    pass

class MetaPrompter():
    def generate(self, prompt : str) -> str:
        raise NotImplementedError("No generate method defined for this MetaPrompter instance")

    def get_prompt(self, objective : str, project : str, task : str, model : str) -> str:
        if project in PROJECTS and task in TASKS:
            p_name, p_desc, p_lang = (PROJECT_CONTEXTS[project]['name'], 
                                      PROJECT_CONTEXTS[project]['description'],
                                      PROJECT_CONTEXTS[project]['languages'])
            
            t_desc, t_cons = (TASK_CONTEXTS[task]['description'], 
                              TASK_CONTEXTS[task]['considerations'])
            
            llm_name, llm_cons = (MODEL_CONTEXTS[model]['name'], 
                              MODEL_CONTEXTS[model]['considerations'])
            
            prompt = MP_TEMPLATE(objective,
                                p_name, p_desc, p_lang, 
                                t_desc, t_cons,
                                llm_name, llm_cons)
            return self.generate(prompt)
        else:
            raise InvalidTask(f"Invalid project/task passed! Must be in {PROJECTS} & {TASKS}")

class GeminiMP(GeminiAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()
        self.generate = self._gemini_gen

    def _gemini_gen(self, prompt : str):
        response = self.client.generate_content(prompt)
        return response.text

class OpenMP(OpenAIAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()
        self.generate = self._openai_gen

    def _openai_gen(self, prompt : str):
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=MAX_TOKENS,
            messages=[{"role": "system", 
                       "content": "You are a metaprompt generator. Generate ONLY the requested prompt with no introductory text, explanatory text, or concluding remarks."},
                       {"role": "user", 
                        "content": prompt}]
            )
        return completion.choices[0].message.content

class AnthroMP(AnthroAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()        
        self.generate = self._anthropic_gen

    def _anthropic_gen(self, prompt : str):
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    
"""
from constants import MP_TEMPLATE, PROJECTS, TASKS, PROJECT_CONTEXTS, TASK_CONTEXTS, MODEL_CONTEXTS, MAX_TOKENS
from agents import *
from google.generativeai import GenerationConfig
import json

class InvalidTask(Exception):
    pass

class MetaPrompter():
    def generate(self, prompt : str) -> str:
        raise NotImplementedError("No generate method defined for this MetaPrompter instance")

    def get_prompt(self, objective : str, project : str, task : str, model : str) -> str:
        if project in PROJECTS and task in TASKS:
            p_name, p_desc, p_lang = (PROJECT_CONTEXTS[project]['name'], 
                                      PROJECT_CONTEXTS[project]['description'],
                                      PROJECT_CONTEXTS[project]['languages'])
            
            t_desc, t_cons = (TASK_CONTEXTS[task]['description'], 
                              TASK_CONTEXTS[task]['considerations'])
            
            llm_name, llm_cons = (MODEL_CONTEXTS[model]['name'], 
                              MODEL_CONTEXTS[model]['considerations'])
            
            prompt = MP_TEMPLATE(objective,
                                p_name, p_desc, p_lang, 
                                t_desc, t_cons,
                                llm_name, llm_cons)
            return self.generate(prompt)
        else:
            raise InvalidTask(f"Invalid project/task passed! Must be in {PROJECTS} & {TASKS}")

class GeminiMP(GeminiAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()
        self.generate = self._gemini_gen

    def _gemini_gen(self, prompt : str):
        schema = {"type": "object",
            "properties": {"prompt": {"type": "string"}},
            "required": ["prompt"]}
        response = self.client.generate_content(
            contents=prompt,
            generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema, 
            max_output_tokens=MAX_TOKENS))
        
        return json.loads(response.text)["prompt"]


class OpenMP(OpenAIAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()
        self.generate = self._openai_gen

    def _openai_gen(self, prompt : str):
        schema = {"type": "object",
                  "properties": {"prompt": {"type": "string"}}, 
                  "required": ["prompt"],
                  "additionalProperties": False}

        completion = self.client.chat.completions.create(
            model="gpt-4o", 
            max_tokens=MAX_TOKENS,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "prompt_response",
                                "strict": True,
                                "schema": schema}
                },
                
            messages=[{"role": "user", "content": prompt}])
        
        return json.loads(completion.choices[0].message.content)["prompt"]

class AnthroMP(AnthroAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()        
        self.generate = self._anthropic_gen

    def _anthropic_gen(self, prompt : str):
        code_tool={"name": "prompt_output", 
                "description": "Return only the prompt", 
                "input_schema": 
                {"type": "object", "properties": {"prompt": {"type": "string"}},
                 "required": ["prompt"]}}
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514", 
            max_tokens=MAX_TOKENS, 
            messages=[{"role": "user", "content": prompt}],
            tools=[code_tool],
            tool_choice={"type": "tool", "name": "code_output"})

        return response.content[0].input["prompt"]
"""