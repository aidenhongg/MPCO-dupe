from pipeline.pipeline import optimize_projects
from graphing import *
from constants import *

from pathlib import Path

import pandas as pd
import sys


class Teer:
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log = open(file_path, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()

def main():
    teer, old_stdout  = Teer("./results/test_logs.txt"), sys.stdout
    sys.stdout = teer

    try:
        dataset_file = "./results/test_results.csv"
        tester = optimize_projects()

        while True:
            try:
                test_results = next(tester)
                test_results.to_csv(dataset_file, mode='a', 
                                    header=not pd.io.common.file_exists(dataset_file), 
                                    index=False)

            except StopIteration:
                break
            except Exception as e:
                print(e)
                continue

    finally:
        sys.stdout = old_stdout
        teer.close()

        for profile in Path('./pipeline/profiler/profiles/').iterdir():
            profile.unlink() # cleanup

        graph_main(dataset_file)
            
if __name__ == "__main__":
    main()
