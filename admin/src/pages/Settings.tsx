import { useEffect, useState } from 'react'
import { Loader2, Save, ShieldAlert, Settings2, Webhook } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiUrl } from '../api'
import { useAuthStore } from '../store/auth'

interface RiskSettings {
  allow_negative_balance: boolean
  auto_block_enabled: boolean
  refund_window_days: number
  refund_event_warning_count: number
  refund_event_block_count: number
  rolling_reserve_percent_bps: number
  min_reserve_balance_minor: number
  default_credit_limit_minor: number
  payment_success_url: string
  stripe_connect_return_url: string
  stripe_connect_refresh_url: string
  telegram_bot_username: string
  default_zone: string
  event_cache_ttl: number
  webhook_url: string
}

const defaultSettings: RiskSettings = {
  allow_negative_balance: true,
  auto_block_enabled: true,
  refund_window_days: 30,
  refund_event_warning_count: 3,
  refund_event_block_count: 7,
  rolling_reserve_percent_bps: 0,
  min_reserve_balance_minor: 0,
  default_credit_limit_minor: 0,
  payment_success_url: '',
  stripe_connect_return_url: '',
  stripe_connect_refresh_url: '',
  telegram_bot_username: '',
  default_zone: 'test',
  event_cache_ttl: 900,
  webhook_url: '',
}

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
  const authToken = useAuthStore((state) => state.token)
  const [settings, setSettings] = useState<RiskSettings>(defaultSettings)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const response = await fetch(apiUrl('/api/admin/risk/settings'), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to load settings')
      }

      const data: RiskSettings = await response.json()
      setSettings(data)
    } catch (error) {
      console.error('Failed to load settings:', error)
      toast.error('Failed to load rollout settings')
    } finally {
      setLoading(false)
    }
  }

  const updateSetting = <K extends keyof RiskSettings>(key: K, value: RiskSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    if (settings.refund_event_block_count < settings.refund_event_warning_count) {
      toast.error('Block count must be greater than or equal to warning count')
      return
    }

    setSaving(true)
    try {
      const response = await fetch(apiUrl('/api/admin/risk/settings'), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(settings),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to save settings')
      }

      const data: RiskSettings = await response.json()
      setSettings(data)
      toast.success('Rollout settings saved')
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordChange = () => {
    setPasswordError('')

    if (!currentPassword) {
      toast.error('Please enter your current password')
      return
    }

    const validation = validatePassword(newPassword)
    if (!validation.valid) {
      setPasswordError(validation.error)
      toast.error(validation.error)
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      toast.error('Passwords do not match')
      return
    }

    setPasswordError('')
    toast.success('Password update API is not wired yet')
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
  }

  const formatMajorPlaceholder = (minor: number) => (minor / 100).toFixed(2)

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <span className="ml-2 text-gray-500">Loading rollout settings...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-500">Backend-backed rollout configuration for risk, checkout, and Stripe onboarding.</p>
        </div>
        <button onClick={handleSave} className="btn btn-primary" disabled={saving}>
          {saving ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Save className="mr-2 h-5 w-5" />}
          Save Settings
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card space-y-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-2 text-amber-700">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Risk Defaults</h2>
              <p className="text-sm text-gray-500">Applied when a new agent risk policy or wallet is initialized.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">Allow negative balance</span>
              <input
                type="checkbox"
                checked={settings.allow_negative_balance}
                onChange={(e) => updateSetting('allow_negative_balance', e.target.checked)}
              />
            </label>
            <label className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">Auto-block enabled</span>
              <input
                type="checkbox"
                checked={settings.auto_block_enabled}
                onChange={(e) => updateSetting('auto_block_enabled', e.target.checked)}
              />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Refund window (days)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.refund_window_days}
                onChange={(e) => updateSetting('refund_window_days', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Event cache TTL (seconds)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.event_cache_ttl}
                onChange={(e) => updateSetting('event_cache_ttl', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Refund warning count</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.refund_event_warning_count}
                onChange={(e) => updateSetting('refund_event_warning_count', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Refund block count</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.refund_event_block_count}
                onChange={(e) => updateSetting('refund_event_block_count', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Rolling reserve (bps)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.rolling_reserve_percent_bps}
                onChange={(e) => updateSetting('rolling_reserve_percent_bps', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Default credit limit (minor)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.default_credit_limit_minor}
                onChange={(e) => updateSetting('default_credit_limit_minor', parseInt(e.target.value, 10) || 0)}
              />
              <p className="mt-1 text-xs text-gray-500">Approx. major amount: {formatMajorPlaceholder(settings.default_credit_limit_minor)}</p>
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-gray-700">Minimum reserve balance (minor)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={settings.min_reserve_balance_minor}
                onChange={(e) => updateSetting('min_reserve_balance_minor', parseInt(e.target.value, 10) || 0)}
              />
            </div>
          </div>
        </div>

        <div className="card space-y-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-2 text-blue-700">
              <Settings2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Payment Rollout</h2>
              <p className="text-sm text-gray-500">Checkout and Stripe Connect URLs now come from backend settings.</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Checkout success URL</label>
              <input
                type="url"
                className="w-full"
                value={settings.payment_success_url}
                onChange={(e) => updateSetting('payment_success_url', e.target.value)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Stripe return URL</label>
              <input
                type="url"
                className="w-full"
                value={settings.stripe_connect_return_url}
                onChange={(e) => updateSetting('stripe_connect_return_url', e.target.value)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Stripe refresh URL</label>
              <input
                type="url"
                className="w-full"
                value={settings.stripe_connect_refresh_url}
                onChange={(e) => updateSetting('stripe_connect_refresh_url', e.target.value)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Telegram bot username</label>
              <input
                type="text"
                className="w-full"
                placeholder="@ArenaAppTestZone_bot"
                value={settings.telegram_bot_username}
                onChange={(e) => updateSetting('telegram_bot_username', e.target.value)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Default agent zone</label>
              <select
                className="w-full"
                value={settings.default_zone}
                onChange={(e) => updateSetting('default_zone', e.target.value)}
              >
                <option value="test">Test</option>
                <option value="real">Real</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
              <Webhook className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Webhook Endpoint</h2>
              <p className="text-sm text-gray-500">Shared backend-stored webhook target for operational notifications.</p>
            </div>
          </div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Outbound webhook URL</label>
          <input
            type="url"
            className="w-full"
            placeholder="https://example.com/hooks/orders"
            value={settings.webhook_url}
            onChange={(e) => updateSetting('webhook_url', e.target.value)}
          />
        </div>

        <div className="card">
          <h2 className="mb-4 text-lg font-semibold">Change Password</h2>
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Current Password</label>
              <input type="password" className="w-full" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">New Password</label>
              <input
                type="password"
                className={`w-full ${passwordError ? 'border-red-500' : ''}`}
                value={newPassword}
                onChange={(e) => {
                  setNewPassword(e.target.value)
                  setPasswordError('')
                }}
              />
              {passwordError && <p className="mt-1 text-sm text-red-600">{passwordError}</p>}
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Confirm New Password</label>
              <input type="password" className="w-full" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            </div>
            <button onClick={handlePasswordChange} className="btn btn-secondary">
              Update Password
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold">About</h2>
        <dl className="space-y-2">
          <div>
            <dt className="text-sm font-medium text-gray-500">Version</dt>
            <dd className="text-sm text-gray-900">0.1.0</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Environment</dt>
            <dd className="text-sm text-gray-900">Admin rollout configuration</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
