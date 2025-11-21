from constants import PROJECTS

from pipeline.metaprompters import OpenMP
from pipeline.optimizers import *

from pipeline.profiler import *

import os

#testing
PROJECTS = {'whisper'}
def optimize_main():
    mpo4 = OpenMP()
    optims = (AnthroOptimizer(), OpenOptimizer(), GeminiOptimizer())

    for proj_name in list(PROJECTS):
        if not os.path.exists(f"./pipeline/profiler/profiles/{proj_name}_profile.speedscope"):
            print(f"./pipeline/profiler/profiles/{proj_name}_profile.speedscope")
            try:
                get_speedscope(proj_name)
            except KeyboardInterrupt:
                print("Tests halted - speedscope saved")

        if not os.path.exists(f"./pipeline/profiles/{proj_name}_profile.speedscope"):
            filter_speedscope(proj_name)

        project = PyProj(proj_name)

        for _ in range(10):
            
            for optim in optims: