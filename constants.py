import json
from textwrap3 import dedent

# Projects, tasks, and models allowed
PROJECTS : set = {'langflow', 'whisper'}
TASKS : set = {'runtime'}
MODELS : set = {'25', '4o', '47'}
MAX_TOKENS : int = 512

def load_json(path, key = None):
    with open(path, mode='r', encoding="utf-8") as handle:
        return json.load(handle) if key is None else json.load(handle)[key]

files = {
    'api_keys' : './API_KEYS.json',
    'model_contexts' : "./contexts/model_contexts.json",
    'project_contexts' : "./contexts/project_contexts.json",
    'task_contexts' : "./contexts/task_contexts.json"
}

# API keys
GEMINI_KEY : str = load_json(files['api_keys'], 'GEMINI_KEY')
OPENAI_KEY : str = load_json(files['api_keys'], 'OPENAI_KEY')
ANTHROPIC_KEY : str = load_json(files['api_keys'], 'ANTHROPIC_KEY')

# Project, model, and task constants
PROJECT_CONTEXTS : dict = load_json(files['project_contexts'])
MODEL_CONTEXTS : dict = load_json(files['model_contexts'])
TASK_CONTEXTS : dict = load_json(files['task_contexts'])

del files

# JSON structures:
"""
API_KEYS.json
{
    "GEMINI_KEY" : '',
    "OPENAI_KEY" : '',
    "ANTHROPIC_KEY" : ''
}

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

# Prompt templates
def MP_TEMPLATE(objective : str,
                p_name : str, p_desc : str, p_lang : str, 
                t_desc : str, t_cons : str,
                llm_name : str, llm_cons : str) -> str:
    template = f"""
        You are an expert in code optimization. Please generate a prompt that will instruct the target LLM {p_name} to optimize code for {objective}.
        Consider the project context, task context, and adapt the prompt complexity and style based on the target LLM's capabilities.

        ## Project Context
        Project Name: {p_name}
        Project Description: {p_desc}
        Primary Languages: {p_lang}

        ## Task Context
        - Description: {t_desc}
        - Considerations: {t_cons}

        ## Target LLM Context
        - Target Model: {llm_name}
        - Considerations: {llm_cons}
        """
    
    return dedent(template).strip()

def BASE_TEMPLATE(objective : str,
                p_name : str, p_desc : str, p_lang : str, 
                t_desc : str, t_cons : str,
                llm_name : str, llm_cons : str) -> str:
    template = f"""
        You are an expert in code optimization. Please optimize the provided code for {objective}. Consider the project context, task context, and adapt your optimization approach accordingly.
        
        ## Project Context
        Project Name: {p_name}
        Project Description: {p_desc}
        Primary Languages: {p_lang}
    
        ## Task Context
        - Description: {t_desc}
        - Considerations: {t_cons}

        ## Target LLM Context
        - Target Model: {llm_name}
        - Considerations: {llm_cons}"""
    
    return dedent(template).strip()

FEW_SHOT = """
Here are examples of code optimization:
Example 1 - Loop optimization:
Original: for i in range(len(arr)): if arr[i] > threshold: result.append(arr[i])
Optimized: result = [x for x in arr if x > threshold]

Example 2 - Algorithm optimization:
Original: for i in range(n): for j in range(n): if matrix[i][j] > 0: count += 1
Optimized: count = np.sum(matrix > 0)

Example 3 - Data structure optimization:
Original: items = []; for x in data: items.append(x); return sorted(items)
Optimized: return sorted(data)

Now optimize the code for better runtime performance, then provide only the final optimized code.""".strip()

COT = """
Let's optimize the following code step by step:

Please follow these reasoning steps:
1. First, analyze the current code to identify performance bottlenecks
2. Consider different optimization strategies (algorithmic, data structure, loop optimization, etc.)
3. Evaluate the trade-offs of each approach
4. Select the best optimization strategy
5. Implement the optimized version

Think through each step, then provide only the final optimized code.""".strip()

