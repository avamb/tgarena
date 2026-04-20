import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import toast from 'react-hot-toast'
import { apiUrl } from '../api'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuthStore((state) => state.login)

  // Get the intended destination from location state, default to dashboard
  const from = (location.state as { from?: string })?.from || '/dashboard'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await fetch(apiUrl('/api/admin/login'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })

      if (response.ok) {
        const data = await response.json()
        // Decode JWT to get user info (payload is base64 encoded)
        const payload = JSON.parse(atob(data.access_token.split('.')[1]))
        login(data.access_token, {
          id: payload.user_id,
          username: payload.sub,
          role: payload.role,
        })
        toast.success('Login successful!')
        navigate(from, { replace: true })
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Invalid credentials')
      }
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Login failed. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="max-w-md w-full">
        <div className="card">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">TG-Ticket-Agent</h1>
            <p className="text-gray-600 mt-2">Admin Panel</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full"
                placeholder="Enter username"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full"
                placeholder="Enter password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
