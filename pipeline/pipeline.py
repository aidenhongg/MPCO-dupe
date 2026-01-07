from pipeline.metaprompters import OpenMP, MetaPrompter
from pipeline.optimizers import *
from pipeline.components import *
from pipeline.profiler import *

from constants import *

import pandas as pd
import traceback


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

def optimize_projects():
    mpo4 = OpenMP()
    optims = (AnthroOptimizer(), OpenOptimizer(), GeminiOptimizer(),)

    for proj_name in list(PROJECTS):        
        get_pyprofile(proj_name, 0)
        og_failure_count, _, _ = get_pyprofile(proj_name, 0) 
        # running twice may be necessary as some test suites need initialization run

        if og_failure_count is None:
            print(f"Test suite on {proj_name} errors - skipping")
            continue

        # get 10 trial average for the original runtime - before optimizations
        original_runtimes = []
        for _ in range(10):
            _, original_runtime, _ = get_pyprofile(proj_name, 0)
            original_runtimes.append(original_runtime)
        og_runtime = sum(original_runtimes) / len(original_runtimes)
        print(f"Benchmark completed for {proj_name} : avg runtime {og_runtime}")

        project = PyProj(proj_name)

        # generate snippets for each revision model
        task = list(TASKS)[0]
        
        for optim in optims:
            # generate necessary prompts
            meta_prompt = mpo4.get_prompt(OBJECTIVE, proj_name, task, optim.name)
            print("GENERATED META PROMPT: \n" + meta_prompt)
            base_contextual_prompt = _base_template(OBJECTIVE, proj_name, task, optim.name)
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
                                edits, failed_optims, prompt = _optimize_snippet(OBJECTIVE, task, 
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
                        new_failure_count, new_runtime, profile = get_pyprofile(proj_name, 'bench', testing_patch=True)

                        # if the last revision is worse, revert all patches and try again
                        if new_failure_count > og_failure_count:
                            print("Critical optimization failure - reverting patches and trying again ")
                            
                            # display 
                            print(profile.stderr.decode('utf-8'))
                            
                            [patch.revert_patch() for patch in patches]
                            continue
                        
                        # if the last revision is successful, keep testing and then breka
                        else:
                            print(f"Benchmark {1} complete with runtime {new_runtime}")
                            runtimes.append(new_runtime)
                            for bench in range(9):
                                _, new_runtime, _ = get_pyprofile(proj_name, 'bench', testing_patch=True)
                                print(f"Benchmark {bench + 2} complete with runtime {new_runtime}")
                                runtimes.append(new_runtime)
                            break
                except BaseException as e:
                    print(f"Error during optimization loop: {e}")
                    traceback.print_exc()
                finally:
                    print(f"\nDone with {prompt_type} prompting - moving to next prompt type for project {proj_name} with optimizer {optim.name}\n")
                    yield _assemble_results(all_snippets, 
                                           proj_name, optim.name, 
                                           prompt, prompt_type, 
                                           all_attempts, runtimes,
                                           og_runtime) # record results

                    [patch.revert_patch() for patch in patches] # always revert all patches at the end
                    project.revisions = 0 # reset revisions for next set of revisions
                    
            print(f"Done with {optim.name} - moving to next optimizer...")
        print(f"Optimization complete for project {proj_name}")
    return

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
        if patch.apply_patch():
            # run tests to get runtimes in this scope
            new_failure_count, _, profile = get_pyprofile(proj_name, project.revisions + 1, testing_patch = True)

            if (new_failure_count is None) or (new_failure_count > og_failure_count):
                print("============FAULTY CODE============")
                print(f"filename : {code_object['rel_path']}, startline : {code_object['start_line']}")
                print(new_snippet) 
                print("===================================")

                print(profile.stdout.decode('utf-8'))

                patch.revert_patch()
                print(f"{failed_optims + 1} failed optimizations : regenerating attempt...")
                
                if failed_optims == 9:
                    raise OptimizationError(code_object, optim.name)
                if metaprompter: # only regenerate prompt if the very first revision fails
                    print("Regenerating prompt...")
                    prompt = metaprompter.get_prompt(objective, proj_name, task, optim.name) 
                    print("GENERATED META PROMPT: \n" + prompt)

            else:
                patches.insert(0, patch)
                project.revisions += 1
                return {old_snippet : new_snippet}, failed_optims, prompt
        else:
            patch.revert_patch()

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

def _assemble_results(all_snippets : list, 
                      proj_name : str, optim_name : str, 
                      prompt : str, prompt_type : str, 
                      all_attempts : list, runtimes : list,
                      original_runtime : float) -> list:

    rows = []
    avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0
    
    for (snippet_dict, attempts) in zip(all_snippets, all_attempts):
        for original, edited in snippet_dict.items():
            rows.append({'original_snippet': original,
                         'edited_snippet': edited,
                         'project': proj_name,
                         'optimizer': optim_name,
                         'prompt': prompt,
                         'prompt_type': prompt_type,
                         'failed_attempts': attempts,
                         'avg_runtime': avg_runtime,
                         'original_runtime' : original_runtime})            

    return pd.DataFrame(rows)