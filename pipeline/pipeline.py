from constants import PROJECTS, MODELS, TASKS

from pipeline.metaprompters import OpenMP
from pipeline.optimizers import *

from pipeline.profiler import *

import difflib

#testing
PROJECTS = {'whisper'}

def _make_patch(code_object: dict, optimized_code: str) -> str:
    file_path = code_object['file']

    # indices are 0-indexed
    start_line = code_object['start_line']
    end_line = code_object['end_line']
    base_indent : int = code_object['base_indent']
    
    with open(file_path, 'r', encoding='utf-8') as f:
        old_module = f.readlines()
    
    # formatting
    optimized_code = optimized_code.splitlines(keepends=True)
    if not optimized_code[-1].endswith('\n'):
        optimized_code[-1] += '\n'
    indent = ' ' * base_indent
    optimized_code = [indent + line if line.strip() else line for line in optimized_code]

    # edit module
    optimized_module = (
        old_module[:start_line] + 
        optimized_code + 
        old_module[end_line:]
    )
    
    patch = '\n'.join(difflib.unified_diff(old_module,
                                           optimized_module,
                                           fromfile=file_path,
                                           tofile=file_path,
                                           lineterm=''))
    
    return patch


def optimize_projects(objective : str):
    mpo4 = OpenMP()
    optims = (AnthroOptimizer(), OpenOptimizer(), GeminiOptimizer())

    for proj_name in list(PROJECTS):
        # split this for python / cpp
        # pick out bottlenecks
        failure_count, duration = _get_pyprofile(proj_name)
        print(f"Project: {proj_name}, Failure Count: {failure_count}, Duration: {duration}")
        filter_speedscope(proj_name)
        project = PyProj(proj_name)

        # generate snippets for each revision model
        task = list(TASKS)[0]
        for code_object in project.top_functions:
            snippet = code_object['code']
            
            for optim in optims:
                failed_tests = True
                mp_prompt = mpo4.get_prompt(objective, proj_name, task, optim.name)
                
                while failed_tests:
                    for _ in range(10):
                        runtimes = []
                        optimized_code = optim.generate(mp_prompt, snippet)
                        patch = _make_patch(code_object, optimized_code)
                        

# def get_prompt(self, objective : str, project : str, task : str, model : str) -> str:
