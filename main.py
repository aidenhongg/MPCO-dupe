from pipeline.pipeline import optimize_projects

def main():
    table = optimize_projects("Optimize the specific code object provided. Return ONLY the optimized version of that object, preserving its exact signature and interface. Do not recreate parent classes or surrounding code.")
    table.to_csv("test_results3.csv", index=False)
    
if __name__ == "__main__":
    main()


#     "runtime" : {"description" : "Synthesize a single, best-runtime optimized version of the given object, preserving its signature. Return ONLY the specific object provided (function/method/class), not parent classes or enclosing contexts.", "considerations" : "Algorithmic complexity and big O notation; data structures and their efficiency; loop optimizations and redundant iterations; memory access patterns and cache utilization; I/O operations and system calls; parallel processing and multi-threading; redundant computations"}