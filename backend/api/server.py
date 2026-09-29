from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import json

from twin.finances.bill import compute_bill
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import run_scenario

app = FastAPI(title="Renewable Grid Digital Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/scenarios")
def get_scenarios():
    scenarios = []
    if os.path.exists("configs"):
        for f in sorted(os.listdir("configs")):
            if f.endswith(".yaml") and f != "defaults.yaml":
                scenarios.append(f.replace(".yaml", ""))
    return {"scenarios": scenarios}

@app.post("/simulate/{scenario_id}")
def simulate_scenario(scenario_id: str, force: bool = False):
    try:
        report_path = f"reports/results_{scenario_id}.json"
        if not force and os.path.exists(report_path):
            with open(report_path, "r") as f:
                report = json.load(f)
            bill = compute_bill(scenario_id)
            return {"status": "success", "scenario_id": scenario_id, "report": report, "bill": bill, "cached": True}
            
        report = run_scenario(scenario_id, force_randomize=force)
        bill = compute_bill(scenario_id)
        return {"status": "success", "scenario_id": scenario_id, "report": report, "bill": bill, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/{scenario_id}")
def get_results(scenario_id: str):
    report_path = f"reports/results_{scenario_id}.json"
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    with open(report_path, "r") as f:
        report = json.load(f)
        
    bill = compute_bill(scenario_id)
    
    return {
        "scenario_id": scenario_id,
        "report": report,
        "bill": bill
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
