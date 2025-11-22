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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content

class AnthroMP(AnthroAgent, MetaPrompter):
    def __init__(self) -> None:
        super().__init__()        
        self.generate = self._anthropic_gen

    def _anthropic_gen(self, prompt : str):
        message = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text