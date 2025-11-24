from constants import PROJECTS, MODELS, TASKS

from pipeline.metaprompters import OpenMP
from pipeline.optimizers import *

from pipeline.profiler import *

import difflib
from pathlib import Path
import subprocess
import tempfile
import os

#testing
PROJECTS = {'whisper'}

class OptimizationError(Exception):
    def __init__(self, code_object, optimizer_name, attempts=10):
        self.code_object = code_object
        self.optimizer_name = optimizer_name
        self.attempts = attempts
        message = (
            f"Failed to optimize code object\n"
            f"{code_object['code']}\n"
            f"with optimizer '{optimizer_name}' after {attempts} attempts"
        )
        super().__init__(message)

class MyPatch:
    def __init__(self, code_object: dict, optimized_code: str, root : str):
        self.code_object = code_object
        self.optimized_code = optimized_code.splitlines(keepends=True)
        self.root = Path(root)
        self.patch = None

    def _make_patch(self):
        file_path = self.code_object['rel_path']

        # indices are 0-indexed
        start_line = self.code_object['start_line']
        end_line = self.code_object['end_line']
        base_indent : int = self.code_object['base_indent']

        with open(self.root / file_path, 'r', encoding='utf-8') as f:
            old_module = f.readlines()

        # formatting
        if not self.optimized_code[-1].endswith('\n'):
            self.optimized_code[-1] += '\n'
        indent = ' ' * base_indent
        self.optimized_code = [indent + line if line.strip() else line for line in self.optimized_code]

        # edit module
        optimized_module = (old_module[:start_line] + 
                            self.optimized_code + 
                            old_module[end_line + 1:])

        old_code = old_module[start_line:end_line + 1]

        # testing
        with open('./temp2.txt', 'w', encoding='utf-8') as f:
            f.writelines(old_module)
        with open('./temp.txt', 'w', encoding='utf-8') as f:
            f.writelines(optimized_module)
        with open('./oldobj.txt', 'w', encoding='utf-8') as f:
            f.writelines(old_code)

        diff_lines = list(difflib.unified_diff(old_module,
                                               optimized_module,
                                               fromfile=f'a/{file_path.as_posix()}',
                                               tofile=f'b/{file_path.as_posix()}',
                                               lineterm='\n'))
        self.patch = ''.join(diff_lines)
            
    def _apply_patch(self) -> bool:
        if self.patch is None:
            self._make_patch()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False, encoding='utf-8', newline='\n') as patch_file:
            patch_file.write(self.patch)
            patch_path = patch_file.name

        result = subprocess.run(['git', 'apply', patch_path], 
                              capture_output=True, 
                              text=True,
                              cwd=self.root)

        self.patch_path = patch_path

        if result.returncode != 0:
            print(f"Failed to apply patch: {result.stderr}")
            return False
        return True
    
    def _revert_patch(self):
        subprocess.run(['git', 'apply', '--reverse', self.patch_path],
                     capture_output=True,
                     cwd=self.root)
        try:
            os.unlink(self.patch_path)
        except:
            pass

def optimize_projects(objective : str):
    mpo4 = OpenMP()
    optims = (AnthroOptimizer(), OpenOptimizer(), GeminiOptimizer())

    for proj_name in list(PROJECTS):
        # split this for python / cpp
        # pick out bottlenecks
        og_failure_count, duration = get_pyprofile(proj_name)
        if not og_failure_count:
            print(f"Test suite on {proj_name} errors - skipping")
            continue
        print(f"Project: {proj_name}, Failure Count: {og_failure_count}, Duration: {duration}")
        filter_speedscope(proj_name)
        project = PyProj(proj_name)

        # generate snippets for each revision model
        task = list(TASKS)[0]
        for optim in optims:
            runtimes = []
            patches = []
            try:
                while True:
                    mp_prompt = mpo4.get_prompt(objective, proj_name, task, optim.name)
                    print(mp_prompt) # remove -just for testing!

                    for i, code_object in enumerate(project.top_functions):
                        snippet = code_object['code']
                        scope = code_object['scope']

                        for failed_optims in range(10):
                            optimized_code = optim.generate(mp_prompt, snippet, scope)
                            patch = MyPatch(code_object, optimized_code, project.root_dir)

                            if patch._apply_patch():
                                patches.append(patch)
                                # run tests to get runtimes in this scope
                                new_failure_count, _ = get_pyprofile(proj_name, testing_patch=True)
                                if not new_failure_count or new_failure_count > og_failure_count:

                                    print(code_object['rel_path'], code_object['start_line'], code_object['end_line'])
                                    print(code_object['code']) # testing - may have to remove later

                                    patch._revert_patch()
                                    patches = patches[:-1]

                                else:

                                    break
                                
                            print(f"{failed_optims + 1} failed optimizations : regenerating attempt...")
                            if failed_optims == 9:
                                raise OptimizationError(code_object, optim.name)

                            if i == 0: # regenerate prompt if it fails on very first trial
                                print("Regenerating prompt...")
                                mp_prompt = mpo4.get_prompt(objective, proj_name, task, optim.name) 

                    break
            except Exception:
                [patch._revert_patch() for patch in patches]
                # atp all patches generated
                new_failure_count, duration = get_pyprofile(proj_name, testing_patch=True)
                if new_failure_count > og_failure_count:
                    continue

                else:
                    runtimes.append(duration)

                for patch in patches:
                    patch._revert_patch()