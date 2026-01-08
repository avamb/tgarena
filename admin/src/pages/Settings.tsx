import { Save } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Settings() {
  const handleSave = () => {
    toast.success('Settings saved!')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">General Settings</h2>
        <p className="text-gray-500 mb-6">
          Configure application settings.
        </p>

        <div className="space-y-6 max-w-xl">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bot Username
            </label>
            <input
              type="text"
              className="w-full"
              placeholder="@YourBotUsername"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Default Zone
            </label>
            <select className="w-full">
              <option value="test">Test</option>
              <option value="real">Real</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Default Bill24 zone for new agents
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Event Cache TTL (seconds)
            </label>
            <input
              type="number"
              className="w-full"
              defaultValue={900}
              min={60}
              max={3600}
            />
            <p className="mt-1 text-sm text-gray-500">
              How long to cache event data from Bill24 API
            </p>
          </div>

          <button onClick={handleSave} className="btn btn-primary">
            <Save className="h-5 w-5 mr-2" />
            Save Settings
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Change Password</h2>
        <div className="space-y-6 max-w-xl">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Current Password
            </label>
            <input type="password" className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              New Password
            </label>
            <input type="password" className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confirm New Password
            </label>
            <input type="password" className="w-full" />
          </div>
          <button className="btn btn-primary">
            Update Password
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">About</h2>
        <dl className="space-y-2">
          <div>
            <dt className="text-sm font-medium text-gray-500">Version</dt>
            <dd className="text-sm text-gray-900">0.1.0</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Environment</dt>
            <dd className="text-sm text-gray-900">Development</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
