import { useState, useEffect } from 'react'
import { Activity, Terminal, FileText, CheckCircle, XCircle, RefreshCw, Copy, AlertCircle } from 'lucide-react'

// Types
interface DecisionResponse {
  action: 'HOLD' | 'BUY' | 'SELL'
  outcome?: string
  maxCashUsd?: number
}

interface Observation {
  schemaVersion?: number
  timestamp?: number
  market?: {
    id?: string
    secondsToClose?: number
  }
  account?: {
    cashUsd?: number
    eligibleVolumeUsd?: number
    completedCycles?: number
    position?: any
  }
  rules?: {
    maximumBuyCashUsd?: number
    targetVolumeUsd?: number
    evaluationWindowHours?: number
    onePositionAtATime?: boolean
    buyFeesIncludedInMaximum?: boolean
  }
  reference?: {
    btcMidUsd?: number
    openingTargetUsd?: number
    observedAt?: number
    targetObservedAt?: number
    targetProvisional?: boolean
  }
  books?: {
    YES?: {
      bids?: any[]
      asks?: any[]
      minOrderSize?: number
    }
    NO?: {
      bids?: any[]
      asks?: any[]
      minOrderSize?: number
    }
  }
}

// Sample observation from the repository
const SAMPLE_OBSERVATION: Observation = {
  schemaVersion: 1,
  timestamp: 1789880823.619,
  market: {
    id: "sample-btc-5m-market",
    secondsToClose: 84
  },
  account: {
    cashUsd: 10,
    eligibleVolumeUsd: 0,
    completedCycles: 0,
    position: null
  },
  rules: {
    maximumBuyCashUsd: 5,
    targetVolumeUsd: 1000,
    evaluationWindowHours: 24,
    onePositionAtATime: true,
    buyFeesIncludedInMaximum: true
  },
  reference: {
    btcMidUsd: 80482.155,
    openingTargetUsd: 80424.946,
    observedAt: 1789880823.019,
    targetObservedAt: 1789880814.203,
    targetProvisional: false
  },
  books: {
    YES: {
      bids: [[0.49, 100]],
      asks: [[0.50, 100]],
      minOrderSize: 5
    },
    NO: {
      bids: [[0.49, 100]],
      asks: [[0.50, 100]],
      minOrderSize: 5
    }
  }
}

function App() {
  const [activeTab, setActiveTab] = useState<'workspace' | 'docs'>('workspace')
  const [jsonInput, setJsonInput] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [response, setResponse] = useState<DecisionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null)
  const [lastHealthCheck, setLastHealthCheck] = useState<string | null>(null)
  const [showRawResponse, setShowRawResponse] = useState(false)

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

  // Health check
  const checkHealth = async () => {
    try {
      const url = apiBaseUrl ? `${apiBaseUrl}/health` : '/health'
      const res = await fetch(url)
      const data = await res.json()
      setIsHealthy(data.status === 'healthy')
      setLastHealthCheck(new Date().toLocaleTimeString())
    } catch (err) {
      setIsHealthy(false)
      setLastHealthCheck(new Date().toLocaleTimeString())
    }
  }

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [apiBaseUrl])

  const validateJson = (text: string): boolean => {
    try {
      JSON.parse(text)
      setValidationError(null)
      return true
    } catch (err) {
      setValidationError('Invalid JSON: ' + (err as Error).message)
      return false
    }
  }

  const loadSample = () => {
    setJsonInput(JSON.stringify(SAMPLE_OBSERVATION, null, 2))
    setValidationError(null)
    setResponse(null)
    setError(null)
  }

  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setJsonInput(e.target.value)
    if (e.target.value.trim()) {
      validateJson(e.target.value)
    } else {
      setValidationError(null)
    }
  }

  const runAnalysis = async () => {
    if (!validateJson(jsonInput)) {
      return
    }

    setIsLoading(true)
    setError(null)
    setResponse(null)

    try {
      const observation = JSON.parse(jsonInput)
      const url = apiBaseUrl ? `${apiBaseUrl}/decide` : '/decide'
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(observation),
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()
      setResponse(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsLoading(false)
    }
  }

  const reset = () => {
    setJsonInput('')
    setValidationError(null)
    setResponse(null)
    setError(null)
  }

  const copyResponse = () => {
    if (response) {
      navigator.clipboard.writeText(JSON.stringify(response, null, 2))
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Activity className="logo-icon" size={24} />
          <h1>YeNo Research Console</h1>
        </div>
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === 'workspace' ? 'active' : ''}`}
            onClick={() => setActiveTab('workspace')}
          >
            <Terminal size={18} />
            Decision Workspace
          </button>
          <button
            className={`nav-item ${activeTab === 'docs' ? 'active' : ''}`}
            onClick={() => setActiveTab('docs')}
          >
            <FileText size={18} />
            API Documentation
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="health-status">
            <span className="health-label">Backend Status:</span>
            {isHealthy === null ? (
              <span className="health-indicator checking">Checking...</span>
            ) : isHealthy ? (
              <span className="health-indicator healthy">
                <CheckCircle size={16} />
                Connected
              </span>
            ) : (
              <span className="health-indicator unhealthy">
                <XCircle size={16} />
                Unavailable
              </span>
            )}
          </div>
          {lastHealthCheck && (
            <div className="health-time">Last check: {lastHealthCheck}</div>
          )}
          <button className="refresh-btn" onClick={checkHealth}>
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </aside>

      <main className="main-content">
        <div className="disclaimer-banner">
          <AlertCircle size={16} />
          <span>
            <strong>Paper Trading Research Tool:</strong> This is a research interface for competition evaluation. It does not execute real trades or use real money.
          </span>
        </div>

        {activeTab === 'workspace' && (
          <div className="workspace">
            <div className="input-section">
              <div className="section-header">
                <h2>Market Observation</h2>
                <div className="input-actions">
                  <button className="secondary-btn" onClick={loadSample}>
                    Load Sample
                  </button>
                  <button className="secondary-btn" onClick={reset}>
                    Reset
                  </button>
                </div>
              </div>
              <textarea
                className="json-input"
                value={jsonInput}
                onChange={handleJsonChange}
                placeholder="Paste your market observation JSON here..."
                spellCheck={false}
              />
              {validationError && (
                <div className="error-message">{validationError}</div>
              )}
              <button
                className="primary-btn"
                onClick={runAnalysis}
                disabled={!jsonInput.trim() || !!validationError || isLoading}
              >
                {isLoading ? 'Processing...' : 'Run Analysis'}
              </button>
            </div>

            {error && (
              <div className="error-banner">
                <XCircle size={20} />
                <div>
                  <strong>Error</strong>
                  <p>{error}</p>
                </div>
              </div>
            )}

            {response && (
              <div className="results-section">
                <div className="section-header">
                  <h2>Decision Result</h2>
                  <button className="icon-btn" onClick={copyResponse} title="Copy response">
                    <Copy size={16} />
                  </button>
                </div>
                <div className="result-card">
                  <div className="result-row">
                    <span className="result-label">Action:</span>
                    <span className={`result-value action-${response.action.toLowerCase()}`}>
                      {response.action}
                    </span>
                  </div>
                  {response.outcome && (
                    <div className="result-row">
                      <span className="result-label">Outcome:</span>
                      <span className="result-value">{response.outcome}</span>
                    </div>
                  )}
                  {response.maxCashUsd !== undefined && (
                    <div className="result-row">
                      <span className="result-label">Max Cash:</span>
                      <span className="result-value">${response.maxCashUsd.toFixed(6)}</span>
                    </div>
                  )}
                  <div className="result-row">
                    <span className="result-label">Response Time:</span>
                    <span className="result-value">{new Date().toLocaleString()}</span>
                  </div>
                </div>
                <button
                  className="toggle-btn"
                  onClick={() => setShowRawResponse(!showRawResponse)}
                >
                  {showRawResponse ? 'Hide' : 'Show'} Raw JSON
                </button>
                {showRawResponse && (
                  <pre className="raw-response">{JSON.stringify(response, null, 2)}</pre>
                )}
                <div className="result-note">
                  <strong>Note:</strong> This response is from the decision engine. It does not represent a profitable trade or real market execution.
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'docs' && (
          <div className="docs">
            <h2>API Documentation</h2>
            
            <div className="doc-section">
              <h3>POST /decide</h3>
              <p>Submit a market observation to receive a trading decision.</p>
              <div className="doc-code">
                <strong>Request Body:</strong>
                <pre>{JSON.stringify(SAMPLE_OBSERVATION, null, 2)}</pre>
              </div>
              <div className="doc-code">
                <strong>Response:</strong>
                <pre>{`{
  "action": "HOLD" | "BUY" | "SELL",
  "outcome": "YES" | "NO",  // Only for BUY
  "maxCashUsd": number       // Only for BUY, max $5
}`}</pre>
              </div>
            </div>

            <div className="doc-section">
              <h3>GET /health</h3>
              <p>Check if the backend service is running.</p>
              <div className="doc-code">
                <strong>Response:</strong>
                <pre>{`{
  "status": "healthy"
}`}</pre>
              </div>
            </div>

            <div className="doc-section">
              <h3>Running the Sample</h3>
              <ol>
                <li>Click "Load Sample" in the Decision Workspace</li>
                <li>Review the JSON observation structure</li>
                <li>Click "Run Analysis" to send the request</li>
                <li>View the decision response</li>
              </ol>
            </div>

            <div className="doc-section">
              <h3>Troubleshooting</h3>
              <ul>
                <li><strong>Invalid JSON:</strong> Ensure your observation follows the schema exactly</li>
                <li><strong>Backend Unavailable:</strong> Check that the Python server is running</li>
                <li><strong>CORS Errors:</strong> Configure CORS if running on a different origin</li>
                <li><strong>Timeout:</strong> The backend may be processing a complex observation</li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
