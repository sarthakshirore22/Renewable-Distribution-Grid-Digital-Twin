import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

// Support Vercel deployment via environment variables, fallback to local development server
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [scenarios, setScenarios] = useState([])
  const [selectedScenario, setSelectedScenario] = useState('')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState(null)
  const [bill, setBill] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(res => {
        setScenarios(res.data.scenarios)
        if (res.data.scenarios.length > 0) {
          setSelectedScenario(res.data.scenarios[0])
        }
      })
      .catch(err => {
        console.error(err)
        setError('Failed to connect to the backend server. Please ensure the Grid API is running.')
      })
  }, [])

  const runAnalysis = () => {
    setLoading(true)
    setError(null)
    setReport(null)
    setBill(null)
    
    axios.post(`${API_BASE_URL}/simulate/${selectedScenario}`)
      .then(res => {
        return axios.get(`${API_BASE_URL}/results/${selectedScenario}`)
      })
      .then(res => {
        setReport(res.data.report)
        setBill(res.data.bill)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setError('Analysis failed or report not found.')
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
        setError('Report not found. You may need to execute the analysis first.')
        setLoading(false)
      })
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
        <section className="controls-panel">
          <div className="control-group">
            <label htmlFor="scenario-select">Active Grid Scenario</label>
            <select 
              id="scenario-select"
              value={selectedScenario} 
              onChange={e => setSelectedScenario(e.target.value)}
            >
              {scenarios.map(s => (
                <option key={s} value={s}>{s.replace(/_/g, ' ').toUpperCase()}</option>
              ))}
            </select>
          </div>
          <div className="button-group">
            <button onClick={fetchReport} disabled={loading || !selectedScenario} className="btn-secondary">
              Load Latest Report
            </button>
            <button onClick={runAnalysis} disabled={loading || !selectedScenario} className="btn-primary">
              {loading ? 'Evaluating Grid State...' : 'Execute Analysis'}
            </button>
          </div>
          {error && <div className="error-banner">{error}</div>}
        </section>
        
        {loading && (
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Gathering telemetry and projecting grid state...</p>
          </div>
        )}

        {report && bill && !loading && (
          <section className="dashboard-container fade-in">
            <div className="dashboard-grid">
              <div className="card summary-card">
                <div className="card-header">
                  <h2>Operation Summary</h2>
                  <span className="status-indicator success">Active</span>
                </div>
                <div className="summary-stats">
                  <div className="stat-item">
                    <span className="stat-label">Scenario ID</span>
                    <span className="stat-value">{report.scenario_id}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Evaluation Time</span>
                    <span className="stat-value">{report.execution_time_seconds.toFixed(2)}s</span>
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
                  <span className="bill-total-label">Estimated Operating Cost</span>
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
                <h2>Automated Control Registry</h2>
              </div>
              <div className="table-container">
                {report.action_log && report.action_log.length > 0 ? (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Interval Step</th>
                        <th>Timestamp</th>
                        <th>Intervention Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.action_log.map((act, i) => (
                        <tr key={i} className="table-row">
                          <td className="step-cell">{act.step}</td>
                          <td className="time-cell">{act.time}</td>
                          <td className="action-cell">
                            <span className={`action-badge ${act.action.toLowerCase()}`}>
                              {act.action}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="empty-state">
                    <p>Grid parameters optimal. No interventions required during this period.</p>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
