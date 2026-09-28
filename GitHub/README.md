# Digital Twin Grid Orchestrator

This project implements a high-performance Digital Twin for modern power grids, focusing on automated orchestration, limit enforcement (voltage and thermal), and action evaluation (curtailment, battery dispatch, tap changers, and reconfiguration). It features a Python/FastAPI backend and a React/Vite frontend.

## Project Structure

- `backend/`: Contains the core digital twin simulation and FastAPI server.
  - `api/`: FastAPI server endpoints (`server.py`).
  - `configs/`: YAML configuration files defining scenarios and grid parameters.
  - `reports/`: JSON cache of pre-calculated reports (for rapid UI rendering).
  - `twin/`: The Digital Twin library (physics, orchestration, financials).
  - `main.py`: Entry point for running simulations via CLI.
  - `run_all.py`: Orchestrates and tests all scenarios.
- `frontend/`: The React-based telemetry dashboard.

## Local Setup & Deployment

### 1. Backend (Python)
The backend uses Python 3.11+. To run the backend locally:

```bash
cd backend
python -m venv venv
# Activate venv:
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# Start the API server on port 8000
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (React/Vite)
The frontend uses Node.js. 

```bash
cd frontend
npm install

# Start the development server (runs on port 5173)
npm run dev
```

### Vercel Deployment
To deploy the frontend to Vercel:
1. Connect your GitHub repository to Vercel.
2. Set the "Root Directory" in your Vercel project settings to `frontend`.
3. Vercel will automatically run `npm install` and `npm run build`.
4. *Important:* The Vercel frontend is configured to talk to the backend via the `VITE_API_URL` environment variable. By default, it expects the backend to be running on `http://localhost:8000` (which is perfect for a local examiner). If you deploy the Python backend to a cloud provider like Render or Heroku, add `VITE_API_URL=https://your-backend-url.com` in your Vercel Environment Variables.

## Architecture & Optimizations
- **Physics Engine:** Uses `pandapower` (WLS state estimation) for robust AC load flow analysis.
- **Performance:** Simulation bottlenecks are bypassed using an advanced pandas state-restoration cache that eliminates expensive full-grid deepcopies during the search loop.
- **Instant UI Rendering:** The `api/server.py` implements a persistent cache layer (`reports/`). When the UI requests an analysis that has already been executed, the backend instantly streams the cached JSON report in milliseconds rather than re-computing the full timeline load flows.

## Usage
Select a scenario from the dropdown in the UI. Click **Execute Analysis** to see the system's financial repair bill, total violations, and automated resolutions over a 24-hour cycle.
