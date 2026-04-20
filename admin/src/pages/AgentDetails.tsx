import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Copy, Edit, Users, ShoppingCart, DollarSign, Loader2, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'
import { apiUrl } from '../api'

interface Agent {
  id: number
  name: string
  fid: number
  zone: string
  is_active: boolean
  created_at: string
  deep_link: string
}

interface AgentStats {
  users: number
  orders: number
  revenue: number
  revenue_by_currency: CurrencyBreakdown[]
}

interface CurrencyBreakdown {
  currency: string
  amount: number
}

export default function AgentDetails() {
  const { id } = useParams<{ id: string }>()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const authToken = useAuthStore((state) => state.token)

  const formatCurrency = (amount: number, currency: string) => {
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
      }).format(amount)
    } catch {
      return `${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
  }

  useEffect(() => {
    if (id) {
      fetchAgent()
      fetchStats()
    }
  }, [id])

  const fetchAgent = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setAgent(data)
      } else if (response.status === 404) {
        setError('Agent not found')
      } else if (response.status === 401) {
        setError('Session expired. Please login again.')
      } else {
        setError('Failed to load agent details')
      }
    } catch (err) {
      console.error('Failed to fetch agent:', err)
      setError('Failed to load agent details. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/stats`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch agent stats:', err)
    }
  }

  const copyDeepLink = () => {
    if (agent?.deep_link) {
      navigator.clipboard.writeText(agent.deep_link)
      toast.success('Deep link copied!')
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <span className="ml-2 text-gray-500">Loading agent details...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/agents" className="inline-flex items-center text-primary-600 hover:text-primary-800">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agents
        </Link>
        <div className="card">
          <div className="flex h-64 items-center justify-center">
            <AlertCircle className="mr-3 h-8 w-8 text-red-500" />
            <span className="text-gray-700">{error}</span>
          </div>
        </div>
      </div>
    )
  }

  if (!agent) {
    return null
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/agents" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">{agent.name}</h1>
          <span className={`badge ${agent.is_active ? 'badge-success' : 'badge-danger'}`}>
            {agent.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <Link to="/agents" className="btn btn-secondary">
          <Edit className="mr-2 h-4 w-4" />
          Edit
        </Link>
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold">Agent Information</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-500">ID</label>
            <p className="mt-1 font-mono text-sm text-gray-900">{agent.id}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Bill24 FID</label>
            <p className="mt-1 font-mono text-sm text-gray-900">{agent.fid}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Zone</label>
            <p className="mt-1">
              <span className={`badge ${agent.zone === 'real' ? 'badge-success' : 'badge-warning'}`}>
                {agent.zone}
              </span>
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Created</label>
            <p className="mt-1 text-sm text-gray-900">
              {new Date(agent.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-500">Deep Link</label>
            <div className="mt-1 flex items-center space-x-2">
              <code className="flex-1 overflow-hidden text-ellipsis rounded bg-gray-100 px-3 py-1 text-sm">
                {agent.deep_link}
              </code>
              <button onClick={copyDeepLink} className="btn btn-secondary text-sm">
                <Copy className="mr-1 h-4 w-4" />
                Copy
              </button>
            </div>
          </div>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="card border-blue-200 bg-blue-50">
            <div className="flex items-center">
              <Users className="h-10 w-10 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-blue-600">Total Users</p>
                <p className="text-2xl font-bold text-blue-900">{stats.users}</p>
              </div>
            </div>
          </div>
          <div className="card border-green-200 bg-green-50">
            <div className="flex items-center">
              <ShoppingCart className="h-10 w-10 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-green-600">Total Orders</p>
                <p className="text-2xl font-bold text-green-900">{stats.orders}</p>
              </div>
            </div>
          </div>
          <div className="card border-purple-200 bg-purple-50">
            <div className="flex items-center">
              <DollarSign className="h-10 w-10 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-purple-600">Revenue</p>
                <div className="text-2xl font-bold text-purple-900">
                  {stats.revenue_by_currency?.length ? (
                    stats.revenue_by_currency.map((item) => (
                      <p key={item.currency}>{formatCurrency(item.amount, item.currency)}</p>
                    ))
                  ) : (
                    <p>0</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
