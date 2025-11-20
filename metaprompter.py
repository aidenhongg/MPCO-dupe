import json
import os
from constants import *

MODEL_CONTEXT_PATH = "./contexts/model_contexts.json"
PROJECT_CONTEXT_PATH = "./contexts/project_contexts.json"
TASK_CONTEXT_PATH = "./contexts/task_contexts.json"

"""
model_contexts.json
{
    "model" : {'name' : '', 'considerations' : ''},
    "model" : {'name' : '', 'considerations' : ''},
    and so on...
}

project_contexts.json
{
    "project" : {'name' : '', 'description' : '', 'languages' : ''},
    "project" : {'name' : '', 'description' : '', 'languages' : ''},
    and so on...
}

task_contexts.json
{
    "task_type" : {'description' : '', 'considerations' : ''},
    "task_type" : {'description' : '', 'considerations' : ''},
    and so on...
} note: currently only existing task_type is 'runtime' 
"""

class InvalidModel(Exception):
    pass

class InvalidProject(Exception):
    pass

class MetaPrompter():
    with open(PROJECT_CONTEXT_PATH, encoding="utf-8") as handle:
        project_contexts = dict(json.load(handle))

    with open(MODEL_CONTEXT_PATH, encoding="utf-8") as handle:
        model_contexts = dict(json.load(handle))

    with open(TASK_CONTEXT_PATH, encoding="utf-8") as handle:
        task_contexts = dict(json.load(handle))

    def __init__(self, model : str) -> None:
        if model == '25':
            from google import generativeai
            self.client = 

        elif model == '4o':
            from openai import OpenAI

        elif model == '47':
            from anthropic import Anthropic
            
        
        else:
            raise InvalidModel(f"Invalid model passed! Must be in {MODELS}")

    def get_prompt(self, project, task) -> str:
        if project in PROJECTS and task in TASKS:
            p_name, p_desc, p_lang = (self.project_contexts[project]['name'], 
                                      self.project_contexts[project]['description'],
                                      self.project_contexts[project]['language'])
            
            t_desc, t_cons = (self.task_contexts[project]['name'], 
                              self.project_contexts[project]['considerations'])

        else:
            raise InvalidProject(f"Invalid project passed! Must be in {PROJECTS}")