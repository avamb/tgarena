import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
import toast from 'react-hot-toast'

// Settings storage key
const SETTINGS_STORAGE_KEY = 'tg_ticket_agent_settings'

interface SystemSettings {
  botUsername: string
  defaultZone: string
  eventCacheTTL: number
  webhookUrl: string
}

const defaultSettings: SystemSettings = {
  botUsername: '',
  defaultZone: 'test',
  eventCacheTTL: 900,
  webhookUrl: '',
}

// Load settings from localStorage
const loadSettings = (): SystemSettings => {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (stored) {
      return { ...defaultSettings, ...JSON.parse(stored) }
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
  return defaultSettings
}

// Save settings to localStorage
const saveSettings = (settings: SystemSettings) => {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  } catch (error) {
    console.error('Failed to save settings:', error)
  }
}

// Password complexity requirements: Min 8 chars, mixed case, numbers
const validatePassword = (password: string): { valid: boolean; error: string } => {
  if (password.length < 8) {
    return { valid: false, error: 'Password must be at least 8 characters long' }
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, error: 'Password must contain at least one lowercase letter' }
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, error: 'Password must contain at least one uppercase letter' }
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, error: 'Password must contain at least one number' }
  }
  return { valid: true, error: '' }
}

export default function Settings() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')

  // System settings state
  const [settings, setSettings] = useState<SystemSettings>(defaultSettings)

  // Load settings on mount
  useEffect(() => {
    setSettings(loadSettings())
  }, [])

  const updateSetting = <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = () => {
    saveSettings(settings)
    toast.success('Settings saved!')
  }

  const handlePasswordChange = () => {
    // Clear previous errors
    setPasswordError('')

    // Validate current password is provided
    if (!currentPassword) {
      toast.error('Please enter your current password')
      return
    }

    // Validate new password complexity
    const validation = validatePassword(newPassword)
    if (!validation.valid) {
      setPasswordError(validation.error)
      toast.error(validation.error)
      return
    }

    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      toast.error('Passwords do not match')
      return
    }

    // Clear error and show success (actual API call would go here)
    setPasswordError('')
    toast.success('Password updated successfully!')
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
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
              value={settings.botUsername}
              onChange={(e) => updateSetting('botUsername', e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Webhook URL
            </label>
            <input
              type="url"
              className="w-full"
              placeholder="https://example.com/webhook"
              value={settings.webhookUrl}
              onChange={(e) => updateSetting('webhookUrl', e.target.value)}
            />
            <p className="mt-1 text-sm text-gray-500">
              URL for receiving order notifications
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Default Zone
            </label>
            <select
              className="w-full"
              value={settings.defaultZone}
              onChange={(e) => updateSetting('defaultZone', e.target.value)}
            >
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
              value={settings.eventCacheTTL}
              onChange={(e) => updateSetting('eventCacheTTL', parseInt(e.target.value) || 900)}
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
            <input
              type="password"
              className="w-full"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              New Password
            </label>
            <input
              type="password"
              className={`w-full ${passwordError ? 'border-red-500' : ''}`}
              value={newPassword}
              onChange={(e) => {
                setNewPassword(e.target.value)
                setPasswordError('')
              }}
            />
            {passwordError && (
              <p className="mt-1 text-sm text-red-600">{passwordError}</p>
            )}
            <p className="mt-1 text-sm text-gray-500">
              Min 8 characters, must include uppercase, lowercase, and number
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confirm New Password
            </label>
            <input
              type="password"
              className="w-full"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <button onClick={handlePasswordChange} className="btn btn-primary">
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
