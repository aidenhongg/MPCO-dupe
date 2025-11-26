from pipeline.metaprompters import OpenMP, MetaPrompter
from pipeline.optimizers import *
from pipeline.components import *
from pipeline.profiler import *

from constants import *

from pathlib import Path
import pandas as pd
import subprocess
import traceback
import tempfile
import difflib
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

        result = subprocess.run(['git', 'apply', '--allow-empty', patch_path], 
                              capture_output=True, 
                              text=True,
                              cwd=self.root)

        self.patch_path = patch_path

        if result.returncode != 0:
            print(f"Failed to apply patch: {result.stderr}")
            return False
        return True
    
    def _revert_patch(self):
        reversion = subprocess.run(['git', 'apply', '--allow-empty', '--reverse', self.patch_path],
                                    capture_output=True,
                                    cwd=self.root)
        if reversion.returncode != 0:
            print(f"Failed to revert patch: {reversion.stderr}")
            raise Exception("Failed to revert patch")

        try:
            os.unlink(self.patch_path)
        except:
            pass

def optimize_projects(objective : str):
    master_table = pd.DataFrame(columns=['original_snippet', 'edited_snippet', 
                                         'project', 'optimizer', 'prompt', 'prompt_type', 
                                         'failed_attempts', 'avg_runtime'])
    mpo4 = OpenMP()
    optims = (AnthroOptimizer(), OpenOptimizer(), GeminiOptimizer(),)

    for proj_name in list(PROJECTS):
        # split this for python / cpp
        # pick out bottlenecks
        fix_venv(proj_name) # possible refactor into main in root
        
        og_failure_count, duration, _ = get_pyprofile(proj_name, 0)
        if og_failure_count is None:
            print(f"Test suite on {proj_name} errors - skipping")
            continue

        project = PyProj(proj_name)

        # generate snippets for each revision model
        task = list(TASKS)[0]
        
        for optim in optims:
            # generate necessary prompts
            meta_prompt = mpo4.get_prompt(objective, proj_name, task, optim.name)
            print("GENERATED META PROMPT: \n" + meta_prompt)
            base_contextual_prompt = _base_template(objective, proj_name, task, optim.name)
            for prompt, metaprompter, prompt_type in ((meta_prompt, mpo4, 'MP'),
                                                    (FEW_SHOT, None, 'FS'),
                                                    (COT, None, 'COT'),
                                                    (base_contextual_prompt, None, 'BASE')):
                runtimes = []
                patches = []
                
                all_snippets = []       
                all_attempts = []
                try:
                    while True: # optimization loop given params (project, prompt, optimizer model)
                        for _ in range(10):
                            try:
                                edits, failed_optims, prompt = _optimize_snippet(objective, task, 
                                                                                project, optim, prompt, 
                                                                                patches, og_failure_count, 
                                                                                metaprompter = metaprompter)
                            except (OptimizationError, ValueError, KeyError) as e: # if theres an error show it
                                project.revisions += 1
                                traceback.print_exc()
                                print(type(e).__name__)
                                print(f"Error optimizing {proj_name} with {optim.name}: {e}")

                            all_snippets.append(edits)
                            all_attempts.append(failed_optims)

                        if project.revisions == 0:
                            print(f"No successful optimizations - moving to next prompt type")
                            break
                        print("Optimizations generated - benchmarking...")

                        # now we have ~10 patches - run tests on current revision (10th)
                        new_failure_count, duration, profile = get_pyprofile(proj_name, 'bench', testing_patch=True)

                        # if the last revision is worse, revert all patches and try again
                        if new_failure_count > og_failure_count:
                            print("Critical optimization failure - reverting patches and trying again ")
                            
                            # display 
                            print(profile.stderr.decode('utf-8'))
                            
                            [patch._revert_patch() for patch in patches]
                            continue
                        
                        # if the last revision is successful, keep testing and then breka
                        else:
                            print(f"Benchmark {1} complete with duration {duration}")
                            runtimes.append(duration)
                            for bench in range(9):
                                _, duration, _ = get_pyprofile(proj_name, 'bench', testing_patch=True)
                                print(f"Benchmark {bench + 2} complete with duration {duration}")
                                runtimes.append(duration)
                            break
                except BaseException as e:
                    print(f"Error during optimization loop: {e}")
                    traceback.print_exc()
                finally:
                    print(f"\nDone with {prompt_type} prompting - moving to next prompt type for project {proj_name} with optimizer {optim.name}\n")
                    _assemble_results(master_table, all_snippets, 
                                      proj_name, optim.name, 
                                      prompt, prompt_type, 
                                      all_attempts, runtimes) # record results

                    [patch._revert_patch() for patch in patches] # always revert all patches at the end
                    project.revisions = 0 # reset revisions for next set of revisions
                    
            print(f"Done with {optim.name} - moving to next optimizer...")

    return master_table

def _optimize_snippet(objective : str, task : str, 
                      project : PyProj, optim : AnthroOptimizer | OpenOptimizer | GeminiOptimizer, 
                      prompt : str, patches : list, 
                      og_failure_count : list, metaprompter : MetaPrompter = None):
    
    proj_name = project.name

    code_object = project.load_function()
    old_snippet = code_object['code']
    scope = code_object['scope']

    for failed_optims in range(10):
        try: 
            print("Optimizing...")
            new_snippet = optim.generate(prompt, old_snippet, scope)
        except (ValueError, KeyError) as e:
            print(f"Error generating code: {e}")
            print("Trying one more time...")
            new_snippet = optim.generate(prompt, old_snippet, scope)

        patch = MyPatch(code_object, new_snippet, project.root_dir)
        if patch._apply_patch():
            # run tests to get runtimes in this scope
            new_failure_count, _, profile = get_pyprofile(proj_name, project.revisions + 1, testing_patch = True)
            
            if not new_failure_count or new_failure_count > og_failure_count:
                print("============FAULTY CODE============")
                print(code_object['rel_path'], code_object['start_line'], code_object['end_line'])
                print(code_object['code']) # testing - may have to remove later
                print("===================================")

                print(profile.stdout.decode('utf-8'))

                patch._revert_patch()
                print(f"{failed_optims + 1} failed optimizations : regenerating attempt...")
                
                if failed_optims == 9:
                    raise OptimizationError(code_object, optim.name)
                if project.revisions == 0 and metaprompter: # only regenerate prompt if the very first revision fails
                    print("Regenerating prompt...")
                    prompt = metaprompter.get_prompt(objective, proj_name, task, optim.name) 
                    print("GENERATED META PROMPT: \n" + prompt)

            else:
                patches.insert(0, patch)
                project.revisions += 1
                return {old_snippet : new_snippet}, failed_optims, prompt
        else:
            patch._revert_patch()

    raise OptimizationError(code_object, optim.name)

def _base_template(objective, proj_name, task, optim_name):
    p_name, p_desc, p_lang = (PROJECT_CONTEXTS[proj_name]['name'], 
                                PROJECT_CONTEXTS[proj_name]['description'],
                                PROJECT_CONTEXTS[proj_name]['languages'])
    
    t_desc, t_cons = (TASK_CONTEXTS[task]['description'], 
                      TASK_CONTEXTS[task]['considerations'])

    llm_name, llm_cons = (MODEL_CONTEXTS[optim_name]['name'], 
                      MODEL_CONTEXTS[optim_name]['considerations'])

    return BASE_TEMPLATE(objective, p_name, p_desc, p_lang, 
                         t_desc, t_cons,
                         llm_name, llm_cons)

def _assemble_results(master_table : pd.DataFrame, all_snippets : list, 
                      proj_name : str, optim_name : str, 
                      prompt : str, prompt_type : str, 
                      all_attempts : list, runtimes : list) -> list:

    avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0
    
    for (snippet_dict, attempts) in zip(all_snippets, all_attempts):
        for original, edited in snippet_dict.items():
            row = pd.Series({
                'original_snippet': original,
                'edited_snippet': edited,
                'project': proj_name,
                'optimizer': optim_name,
                'prompt': prompt,
                'prompt_type': prompt_type,
                'failed_attempts': attempts,
                'avg_runtime': avg_runtime
            })
            master_table.loc[len(master_table)] = row