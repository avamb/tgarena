import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, MessageCircle, User as UserIcon, Calendar, Globe, Loader2, AlertCircle } from 'lucide-react'
import { useAuthStore } from '../store/auth'

interface User {
  id: number
  telegram_chat_id: number
  telegram_username: string | null
  telegram_first_name: string
  telegram_last_name: string | null
  preferred_language: string
  current_agent_id: number | null
  created_at: string
  last_active_at: string | null
}

interface Agent {
  id: number
  name: string
}

export default function UserDetails() {
  const { id } = useParams<{ id: string }>()
  const [user, setUser] = useState<User | null>(null)
  const [agent, setAgent] = useState<Agent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const authToken = useAuthStore((state) => state.token)

  useEffect(() => {
    if (id) {
      fetchUser()
    }
  }, [id])

  const fetchUser = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`http://localhost:8000/api/admin/users/${id}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setUser(data)
        // Fetch agent info if user has an agent
        if (data.current_agent_id) {
          fetchAgent(data.current_agent_id)
        }
      } else if (response.status === 404) {
        setError('User not found')
      } else if (response.status === 401) {
        setError('Session expired. Please login again.')
      } else {
        setError('Failed to load user details')
      }
    } catch (err) {
      console.error('Failed to fetch user:', err)
      setError('Failed to load user details. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const fetchAgent = async (agentId: number) => {
    try {
      const response = await fetch(`http://localhost:8000/api/admin/agents/${agentId}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setAgent(data)
      }
    } catch (err) {
      console.error('Failed to fetch agent:', err)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <span className="ml-2 text-gray-500">Loading user details...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/users" className="inline-flex items-center text-primary-600 hover:text-primary-800">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Users
        </Link>
        <div className="card">
          <div className="flex items-center justify-center h-64">
            <AlertCircle className="h-8 w-8 text-red-500 mr-3" />
            <span className="text-gray-700">{error}</span>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const fullName = user.telegram_first_name + (user.telegram_last_name ? ` ${user.telegram_last_name}` : '')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link to="/users" className="text-gray-500 hover:text-gray-700">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">{fullName}</h1>
        {user.telegram_username && (
          <span className="text-primary-600">@{user.telegram_username}</span>
        )}
      </div>

      {/* User Info Card */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">User Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex items-start space-x-3">
            <UserIcon className="h-5 w-5 text-gray-400 mt-0.5" />
            <div>
              <label className="block text-sm font-medium text-gray-500">User ID</label>
              <p className="mt-1 text-sm text-gray-900 font-mono">{user.id}</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <MessageCircle className="h-5 w-5 text-gray-400 mt-0.5" />
            <div>
              <label className="block text-sm font-medium text-gray-500">Telegram Chat ID</label>
              <p className="mt-1 text-sm text-gray-900 font-mono">{user.telegram_chat_id}</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <Globe className="h-5 w-5 text-gray-400 mt-0.5" />
            <div>
              <label className="block text-sm font-medium text-gray-500">Preferred Language</label>
              <p className="mt-1">
                <span className={`badge ${user.preferred_language === 'ru' ? 'badge-info' : 'badge-secondary'}`}>
                  {user.preferred_language.toUpperCase()}
                </span>
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <Calendar className="h-5 w-5 text-gray-400 mt-0.5" />
            <div>
              <label className="block text-sm font-medium text-gray-500">Joined</label>
              <p className="mt-1 text-sm text-gray-900">{formatDate(user.created_at)}</p>
            </div>
          </div>
          {user.last_active_at && (
            <div className="flex items-start space-x-3">
              <Calendar className="h-5 w-5 text-gray-400 mt-0.5" />
              <div>
                <label className="block text-sm font-medium text-gray-500">Last Active</label>
                <p className="mt-1 text-sm text-gray-900">{formatDate(user.last_active_at)}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Agent Info */}
      {agent && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Current Agent</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">{agent.name}</p>
              <p className="text-sm text-gray-500">Agent ID: {agent.id}</p>
            </div>
            <Link to={`/agents/${agent.id}`} className="btn btn-secondary text-sm">
              View Agent
            </Link>
          </div>
        </div>
      )}

      {/* Orders section placeholder */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Order History</h2>
        <p className="text-gray-500">No orders yet.</p>
      </div>
    </div>
  )
}
