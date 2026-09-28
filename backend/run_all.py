import os
import subprocess
import time
import yaml

def main():
    start_time = time.time()
    
    scenarios = []
    for f in os.listdir("configs"):
        if f.endswith(".yaml") and f != "defaults.yaml":
            scenarios.append(f.replace(".yaml", ""))
            
    print(f"Discovered {len(scenarios)} scenarios: {scenarios}")
    
    for s in scenarios:
        print(f"--- Running {s} ---")
        subprocess.run(["python", "main.py", "--scenario", s], check=True)
        
    print(f"All scenarios finished in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
