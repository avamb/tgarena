import { useState, useEffect } from 'react'
import { Save, TestTube, History, CheckCircle, XCircle, RefreshCw, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

interface WebhookConfig {
  url: string
  events: string[]
  is_active: boolean
}

interface WebhookLog {
  id: number
  event_type: string
  payload: Record<string, unknown>
  response_status: number | null
  response_body: string | null
  success: boolean
  sent_at: string
}

interface WebhookTestResult {
  success: boolean
  attempts: Array<{
    attempt: number
    timestamp: string
    status?: number
    success: boolean
    error?: string
  }>
  total_attempts: number
  error?: string
  log_id?: number
}

export default function Webhooks() {
  const token = useAuthStore((state) => state.token)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [isActive, setIsActive] = useState(false)
  const [events, setEvents] = useState({
    'user.registered': true,
    'order.paid': true,
  })
  const [activeTab, setActiveTab] = useState<'config' | 'logs'>('config')
  const [logs, setLogs] = useState<WebhookLog[]>([])
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<WebhookTestResult | null>(null)

  const getAuthHeader = () => {
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // Fetch webhook configuration on mount
  useEffect(() => {
    fetchConfig()
  }, [])

  // Fetch logs when logs tab is selected
  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs()
    }
  }, [activeTab])

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/webhooks/config`, {
        headers: getAuthHeader(),
      })
      if (response.ok) {
        const config: WebhookConfig = await response.json()
        setWebhookUrl(config.url || '')
        setIsActive(config.is_active)
        const eventState: Record<string, boolean> = {}
        for (const event of ['user.registered', 'order.paid']) {
          eventState[event] = config.events.includes(event)
        }
        setEvents(eventState as typeof events)
      }
    } catch (error) {
      console.error('Failed to fetch webhook config:', error)
    }
  }

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/webhooks/logs`, {
        headers: getAuthHeader(),
      })
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
      }
    } catch (error) {
      console.error('Failed to fetch webhook logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const selectedEvents = Object.entries(events)
        .filter(([, enabled]) => enabled)
        .map(([event]) => event)

      const response = await fetch(`${API_BASE}/webhooks/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          url: webhookUrl,
          events: selectedEvents,
          is_active: isActive,
        }),
      })

      if (response.ok) {
        toast.success('Configuration saved!')
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to save configuration')
      }
    } catch (error) {
      toast.error('Failed to save configuration')
      console.error('Save error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTest = async () => {
    if (!webhookUrl) {
      toast.error('Please enter a webhook URL first')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const response = await fetch(`${API_BASE}/webhooks/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({ url: webhookUrl }),
      })

      const result: WebhookTestResult = await response.json()
      setTestResult(result)

      if (result.success) {
        toast.success(`Webhook sent successfully after ${result.total_attempts} attempt(s)`)
      } else {
        toast.error(`Webhook failed after ${result.total_attempts} retry attempt(s): ${result.error}`)
      }

      // Refresh logs to show the new entry
      if (activeTab === 'logs') {
        fetchLogs()
      }
    } catch (error) {
      toast.error('Failed to test webhook')
      console.error('Test error:', error)
    } finally {
      setTesting(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('config')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'config'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Configuration
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'logs'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <History className="h-4 w-4 inline mr-2" />
            Logs
          </button>
        </nav>
      </div>

      {activeTab === 'config' ? (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Webhook Configuration</h2>
          <p className="text-gray-500 mb-6">
            Configure webhooks to receive notifications when events occur.
            Failed webhooks will be retried up to 3 times with exponential backoff.
          </p>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Webhook URL (n8n endpoint)
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full"
                placeholder="https://your-n8n.com/webhook/..."
              />
            </div>

            <div>
              <label className="flex items-center mb-4">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm font-medium text-gray-700">Enable Webhooks</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Events
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={events['user.registered']}
                    onChange={(e) =>
                      setEvents({ ...events, 'user.registered': e.target.checked })
                    }
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">User Registered</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={events['order.paid']}
                    onChange={(e) =>
                      setEvents({ ...events, 'order.paid': e.target.checked })
                    }
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Order Paid</span>
                </label>
              </div>
            </div>

            <div className="flex space-x-4">
              <button onClick={handleSave} className="btn btn-primary" disabled={loading}>
                <Save className="h-5 w-5 mr-2" />
                {loading ? 'Saving...' : 'Save Configuration'}
              </button>
              <button onClick={handleTest} className="btn btn-secondary" disabled={testing}>
                {testing ? (
                  <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                ) : (
                  <TestTube className="h-5 w-5 mr-2" />
                )}
                {testing ? 'Testing...' : 'Test Webhook'}
              </button>
            </div>

            {/* Test Result Display */}
            {testResult && (
              <div className={`mt-6 p-4 rounded-lg ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center mb-2">
                  {testResult.success ? (
                    <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500 mr-2" />
                  )}
                  <span className={`font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                    {testResult.success ? 'Webhook Sent Successfully' : 'Webhook Failed'}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-2">
                  Total attempts: {testResult.total_attempts}
                </p>
                {testResult.error && (
                  <p className="text-sm text-red-600">
                    Error: {testResult.error}
                  </p>
                )}
                <div className="mt-3">
                  <p className="text-xs font-medium text-gray-500 mb-1">Attempt Details:</p>
                  <div className="space-y-1">
                    {testResult.attempts.map((attempt) => (
                      <div key={attempt.attempt} className="text-xs flex items-center">
                        {attempt.success ? (
                          <CheckCircle className="h-3 w-3 text-green-500 mr-1" />
                        ) : (
                          <AlertCircle className="h-3 w-3 text-red-500 mr-1" />
                        )}
                        <span>
                          Attempt {attempt.attempt}: {attempt.success ? `Success (HTTP ${attempt.status})` : attempt.error}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Webhook Logs</h2>
            <button onClick={fetchLogs} className="btn btn-secondary text-sm" disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
          <table className="table">
            <thead className="bg-gray-50">
              <tr>
                <th>Event</th>
                <th>Status</th>
                <th>Response</th>
                <th>Sent At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-8 text-gray-500">
                    No webhook logs yet
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id}>
                    <td className="font-mono text-sm">{log.event_type}</td>
                    <td>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        log.success
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {log.success ? (
                          <CheckCircle className="h-3 w-3 mr-1" />
                        ) : (
                          <XCircle className="h-3 w-3 mr-1" />
                        )}
                        {log.response_status || 'N/A'}
                      </span>
                    </td>
                    <td className="max-w-xs truncate text-sm text-gray-500">
                      {log.response_body || '-'}
                    </td>
                    <td className="text-sm text-gray-500">
                      {formatDate(log.sent_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
