import { useState } from 'react'
import { Save, TestTube, History } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Webhooks() {
  const [webhookUrl, setWebhookUrl] = useState('')
  const [events, setEvents] = useState({
    user_registered: true,
    order_paid: true,
  })
  const [activeTab, setActiveTab] = useState<'config' | 'logs'>('config')

  const handleSave = () => {
    toast.success('Configuration saved!')
  }

  const handleTest = () => {
    toast.success('Test webhook sent!')
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
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Events
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={events.user_registered}
                    onChange={(e) =>
                      setEvents({ ...events, user_registered: e.target.checked })
                    }
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">User Registered</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={events.order_paid}
                    onChange={(e) =>
                      setEvents({ ...events, order_paid: e.target.checked })
                    }
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Order Paid</span>
                </label>
              </div>
            </div>

            <div className="flex space-x-4">
              <button onClick={handleSave} className="btn btn-primary">
                <Save className="h-5 w-5 mr-2" />
                Save Configuration
              </button>
              <button onClick={handleTest} className="btn btn-secondary">
                <TestTube className="h-5 w-5 mr-2" />
                Test Webhook
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Webhook Logs</h2>
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
              <tr>
                <td colSpan={4} className="text-center py-8 text-gray-500">
                  No webhook logs yet
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
