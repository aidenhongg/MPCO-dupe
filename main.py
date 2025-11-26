from pipeline.pipeline import optimize_projects

def main():
    table = optimize_projects("Optimize the specific code object provided. Return ONLY the optimized version of that object, preserving its exact signature and interface. Do not recreate parent classes or surrounding code.")
    table.to_csv("test_results3.csv", index=False)
    
if __name__ == "__main__":
    main()