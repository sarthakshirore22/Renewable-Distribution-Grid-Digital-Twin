# Renewable Distribution Grid — Digital Twin

A real-time digital twin system that monitors, predicts, and autonomously controls a renewable-integrated power distribution grid.

## What This Project Does

Traditional power grids were designed for one-way electricity flow from large power plants to consumers. When we connect unpredictable renewable sources like solar panels, the grid faces dangerous instabilities — **voltage spikes** when solar output exceeds demand, and **thermal overloads** when transformers overheat during peak evening hours.

This system solves that problem by creating a **digital replica** of the physical grid that:

1. **Ingests real-time data** — solar irradiance, consumer load profiles, and grid sensor readings
2. **Runs AC power flow physics** — using Newton-Raphson load flow analysis (via Pandapower) to simulate current, voltage, and temperature at every node
3. **Predicts violations** — forecasts when voltage will exceed safe limits or when transformers will overheat
4. **Autonomously deploys corrective actions** — selects the cheapest fix from a library of interventions (battery dispatch, tap changing, PV curtailment, network reconfiguration)
5. **Generates a financial report** — calculates the total operating cost based on IEEE C57.91 transformer aging, curtailment penalties, and equipment wear

## Live Demo

- **Frontend (Vercel):** [Your Vercel URL]
- **Backend API (Render):** [Your Render URL]

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js + Vite |
| Backend API | Python 3.11 + FastAPI |
| Physics Engine | Pandapower (Newton-Raphson AC Load Flow) |
| State Estimation | Weighted Least Squares (WLS) |
| Data Generation | NumPy (stochastic noise modeling) |
| Hosting | Vercel (frontend) + Render (backend) |

## Project Structure

```
├── frontend/               # React website
│   ├── src/
│   │   ├── App.jsx          # Main dashboard UI
│   │   └── App.css          # Styling and responsive layout
│   ├── package.json
│   └── vite.config.js
│
├── backend/                 # Python physics engine + API
│   ├── api/
│   │   └── server.py        # FastAPI endpoints
│   ├── twin/
│   │   ├── config.py        # Pydantic scenario configuration
│   │   ├── orchestrator.py  # Digital Twin brain (estimation + forecast + search)
│   │   ├── grid/
│   │   │   ├── builder.py   # IEEE 33-bus network builder
│   │   │   ├── limits.py    # Voltage & thermal limit checker
│   │   │   └── topology.py  # Radial topology validator
│   │   ├── control/
│   │   │   ├── actions.py   # GridAction classes (Battery, Tap, PV, Switch)
│   │   │   └── search.py    # Cost-ranked action search with deepcopy isolation
│   │   ├── estimation/
│   │   │   └── estimator.py # WLS state estimation (pandapower.estimation)
│   │   ├── forecast/
│   │   │   └── predictor.py # Load & PV forecaster with P10/P50/P90 bounds
│   │   ├── thermal/
│   │   │   └── transformer.py # IEEE C57.91 hot-spot temperature model
│   │   ├── finances/
│   │   │   └── bill.py      # Operating cost calculator
│   │   ├── data/
│   │   │   ├── profiles.py  # Normalized load shape curves
│   │   │   └── weather.py   # Solar irradiance generator
│   │   └── gateway/
│   │       └── sensor.py    # Telemetry message generator with noise
│   ├── configs/              # YAML scenario definitions
│   ├── tests/                # 33 automated tests
│   ├── main.py               # Simulation orchestration loop
│   └── requirements.txt
```

## How to Run Locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

### Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `VITE_API_URL` | Vercel (frontend) | Points to the Render backend URL |
| `PYTHON_VERSION` | Render (backend) | Set to `3.11.0` |

## Grid Scenarios

| ID | Name | What It Tests |
|----|------|--------------|
| S1 | Midday Overvoltage | High solar + low load causes voltage spike |
| S2 | Evening Thermal | Peak demand overheats transformers |
| S3 | Cloud Transient | Rapid irradiance changes from passing clouds |
| S4 | N-1 Outage | A major feeder line is disconnected |
| S5 | Battery Depleted | Grid storage is fully exhausted |
| S6 | Infeasible | No single action can resolve the violation |
| S7 | Hidden Plant | Unregistered generation on the network |

## Financial Model

Every automated action has a real-world cost:

| Intervention | Cost | Reasoning |
|-------------|------|-----------|
| Network Reconfiguration | $0 | Software-only feeder switching |
| Transformer Tap Change | $1 | Mechanical wear on tap mechanism |
| Battery Dispatch | $10 | Lithium-ion cell degradation per cycle |
| PV Curtailment | $100 | Lost clean energy + contract penalties |

Unresolved grid stress carries a penalty of **$1.50 per severity unit**, representing accelerated transformer aging per IEEE C57.91.

## Tests

```bash
cd backend
pytest      # Runs all 33 tests
```

## License

This project was built for the Smart India Hackathon / academic competition.
