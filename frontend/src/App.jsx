import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Human-readable names for intervention types
const INTERVENTION_LABELS = {
  'BatteryDispatchAction': 'Battery Dispatch',
  'TapChangerAction': 'Transformer Tap Adjustment',
  'CurtailPVAction': 'Solar Panel Curtailment',
  'SwitchReconfigureAction': 'Network Reconfiguration'
}

const INTERVENTION_DESCRIPTIONS = {
  'BatteryDispatchAction': 'Grid-scale battery was charged or discharged to balance load.',
  'TapChangerAction': 'Transformer voltage tap was adjusted to regulate bus voltage.',
  'CurtailPVAction': 'Solar generation was reduced to prevent overvoltage.',
  'SwitchReconfigureAction': 'Power flow was rerouted through alternate feeders.'
}

// Format raw ISO timestamp into human-readable format
function formatTimestamp(isoStr) {
  if (!isoStr) return '—'
  // "2026-09-29T04:00:00Z" → "Sep 29, 2026 — 04:00 AM"
  try {
    const d = new Date(isoStr)
    const options = { year: 'numeric', month: 'short', day: 'numeric' }
    const dateStr = d.toLocaleDateString('en-US', options)
    const hours = d.getUTCHours()
    const mins = d.getUTCMinutes()
    const ampm = hours >= 12 ? 'PM' : 'AM'
    const h12 = hours % 12 || 12
    const timeStr = `${h12}:${String(mins).padStart(2, '0')} ${ampm}`
    return `${dateStr} — ${timeStr}`
  } catch {
    return isoStr
  }
}

function App() {
  const [scenarios, setScenarios] = useState([])
  const [selectedScenario, setSelectedScenario] = useState('')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState(null)
  const [bill, setBill] = useState(null)
  const [error, setError] = useState(null)
  const [scenariosLoading, setScenariosLoading] = useState(true)

  useEffect(() => {
    setScenariosLoading(true)
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(res => {
        const sorted = [...res.data.scenarios].sort()
        setScenarios(sorted)
        if (sorted.length > 0) {
          setSelectedScenario(sorted[0])
        }
        setScenariosLoading(false)
      })
      .catch(err => {
        console.error(err)
        setError('Failed to connect to the backend server. Please ensure the Grid API is running.')
        setScenariosLoading(false)
      })
  }, [])

  const runAnalysis = () => {
    setLoading(true)
    setError(null)
    setReport(null)
    setBill(null)
    
    axios.post(`${API_BASE_URL}/simulate/${selectedScenario}?force=true`)
      .then(res => {
        setReport(res.data.report)
        setBill(res.data.bill)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
          setError('The analysis is taking longer than expected. Please try "Load Latest Report" in a moment.')
        } else {
          setError('Analysis failed. Please check your connection and try again.')
        }
        setLoading(false)
      })
  }
  
  const fetchReport = () => {
    setLoading(true)
    setError(null)
    axios.get(`${API_BASE_URL}/results/${selectedScenario}`)
      .then(res => {
        setReport(res.data.report)
        setBill(res.data.bill)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setError('Report not found. You may need to run a new simulation first.')
        setLoading(false)
      })
  }

  // Format scenario ID for display: "s1_midday_overvoltage" → "S1 — Midday Overvoltage"
  const formatScenarioName = (s) => {
    if (!s) return ''
    const parts = s.split('_')
    const id = parts[0].toUpperCase()
    const name = parts.slice(1).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    return name ? `${id} — ${name}` : id
  }

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <h1>Renewable Distribution Grid Intelligence</h1>
          <p className="subtitle">Real-time Predictive Analytics & Automated Control</p>
        </div>
      </header>
      
      <main className="app-main">
        {/* Project Information Section */}
        <section className="info-panel">
          <h2>About This Digital Twin</h2>
          <p>
            This system is a sophisticated digital replica of a renewable distribution grid. 
            It continuously forecasts power flow conditions based on solar irradiance and load data. 
            When instability (like voltage spikes or thermal overloads) is predicted, the automated Orchestrator 
            calculates and deploys the most cost-effective grid interventions (e.g., Battery Dispatch, Tap Changing) 
            to restore safety in real-time.
          </p>
          <div className="info-actions">
            <div className="info-item">
              <strong>Load Latest Report:</strong> Instantly views the most recently cached grid state.
            </div>
            <div className="info-item">
              <strong>Run New Simulation:</strong> Analyzes the grid with realistic real-time variations, generating unique real-world conditions.
            </div>
          </div>
          
          <div className="financial-logic-section">
            <h3>How are operating costs calculated?</h3>
            <p>Our financial engine translates grid stress directly into monetary cost using real-world engineering standards:</p>
            <ul>
              <li><strong>Transformer Degradation:</strong> We calculate insulation loss using the <em>IEEE C57.91 standard</em>. Operating above 110°C Hot-Spot temperature exponentially accelerates asset aging, incurring heavy financial replacement penalties.</li>
              <li><strong>PV Curtailment:</strong> Disconnecting solar farms wastes clean energy and violates grid contracts, incurring a steep <strong>$100.00</strong> penalty per instance.</li>
              <li><strong>Battery Wear:</strong> Cycling lithium-ion grid storage degrades the cells. We assign a <strong>$10.00</strong> mechanical wear cost per dispatch.</li>
              <li><strong>Tap Changes:</strong> Mechanical transformer tap changes cause physical wear and tear, costing <strong>$1.00</strong> per operation.</li>
            </ul>
            <p className="logic-summary">The Digital Twin's goal is to automatically select the intervention strategy that resolves grid violations for the absolute lowest financial cost.</p>
          </div>

          <div className="glossary-section">
            <h3>Key Terms</h3>
            <ul>
              <li><strong>System Stress Index:</strong> A unitless score (0 = perfect, higher = worse) that sums all voltage and thermal violations detected across the 24-hour evaluation period. A score of 0.00 means the grid operated within all safe limits.</li>
              <li><strong>Automated Interventions:</strong> The total number of corrective actions the Digital Twin deployed to keep the grid safe.</li>
              <li><strong>Evaluation Time:</strong> The real-world wall-clock time (in seconds) the physics engine took to complete all power flow calculations.</li>
            </ul>
          </div>
        </section>

        <section className="controls-panel">
          <div className="control-group">
            <label htmlFor="scenario-select">Active Grid Scenario</label>
            <div className="select-wrapper">
              <select 
                id="scenario-select"
                value={selectedScenario} 
                onChange={e => setSelectedScenario(e.target.value)}
                disabled={scenariosLoading}
              >
                {scenariosLoading ? (
                  <option>Loading scenarios...</option>
                ) : (
                  scenarios.map(s => (
                    <option key={s} value={s}>{formatScenarioName(s)}</option>
                  ))
                )}
              </select>
            </div>
          </div>
          <div className="button-group">
            <button onClick={fetchReport} disabled={loading || !selectedScenario || scenariosLoading} className="btn-secondary">
              Load Latest Report
            </button>
            <button onClick={runAnalysis} disabled={loading || !selectedScenario || scenariosLoading} className="btn-primary">
              {loading ? 'Evaluating Grid State...' : 'Run New Simulation'}
            </button>
          </div>
          {error && <div className="error-banner">{error}</div>}
        </section>
        
        {loading && (
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Running physics engine — analyzing power flow across all grid nodes...</p>
            <p className="loading-subtext"><strong>(This may take up to 30 seconds)</strong></p>
          </div>
        )}

        {report && bill && !loading && (
          <section className="dashboard-container fade-in">
            <div className="dashboard-grid">
              <div className="card summary-card">
                <div className="card-header">
                  <h2>Operation Summary</h2>
                  <span className="status-indicator success">Complete</span>
                </div>
                <div className="summary-stats">
                  <div className="stat-item">
                    <span className="stat-label">Scenario</span>
                    <span className="stat-value">{formatScenarioName(report.scenario_id)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Evaluation Time</span>
                    <span className="stat-value">{report.execution_time_seconds.toFixed(1)} sec</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Automated Interventions</span>
                    <span className="stat-value highlight">{report.actions_taken}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">System Stress Index</span>
                    <span className="stat-value warning">{report.total_plant_severity.toFixed(2)}</span>
                  </div>
                </div>
              </div>
              
              <div className="card bill-card">
                <div className="card-header">
                  <h2>Financial Impact Assessment</h2>
                </div>
                <div className="bill-total-container">
                  <span className="bill-total-label">Estimated Operating Cost (USD)</span>
                  <span className="bill-total-value">{bill.total_formatted}</span>
                </div>
                <div className="bill-breakdown">
                  <h3>Cost Drivers</h3>
                  <ul className="cost-list">
                    {Object.entries(bill.breakdown_formatted).map(([key, val]) => (
                      <li key={key} className="cost-list-item">
                        <span className="cost-key">{key.replace(/_/g, ' ')}</span>
                        <span className="cost-val">{val}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
            
            <div className="card full-width-card action-log-card">
              <div className="card-header">
                <h2>Automated Control Log</h2>
              </div>
              <div className="table-container">
                {report.action_log && report.action_log.length > 0 ? (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Time of Day</th>
                        <th>Date & Time</th>
                        <th>Action Taken</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.action_log.map((act, i) => (
                        <tr key={i} className="table-row">
                          <td className="step-cell">{act.step}:00</td>
                          <td className="time-cell">{formatTimestamp(act.time)}</td>
                          <td className="action-cell">
                            <span className="action-badge">
                              {INTERVENTION_LABELS[act.action] || act.action}
                            </span>
                          </td>
                          <td className="desc-cell">{INTERVENTION_DESCRIPTIONS[act.action] || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="empty-state">
                    <p>✅ Grid parameters optimal — no corrective interventions were required during this evaluation period.</p>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="app-footer">
        <p>Renewable Distribution Grid Digital Twin &mdash; Powered by Pandapower AC Load Flow &amp; Newton-Raphson State Estimation</p>
      </footer>
    </div>
  )
}

export default App
