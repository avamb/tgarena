import { useState, useEffect, useCallback } from 'react'
import { Plus, Edit, Trash2, Copy, X, Save, Loader2, BarChart3, Users, ShoppingCart, DollarSign, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'
import { useBlocker, useNavigate, Link } from 'react-router-dom'

interface Agent {
  id: number
  name: string
  fid: number
  token?: string
  zone: string
  is_active: boolean
  created_at: string
  deep_link?: string
}

interface AgentStats {
  users: number
  orders: number
  revenue: number
}

interface AgentFormData {
  name: string
  fid: string
  token: string
  zone: string
  is_active: boolean
}

const initialFormData: AgentFormData = {
  name: '',
  fid: '',
  token: '',
  zone: 'test',
  is_active: true,
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [showModal, setShowModal] = useState(false)
  const [showStatsModal, setShowStatsModal] = useState(false)
  const [formData, setFormData] = useState<AgentFormData>(initialFormData)
  const [originalFormData, setOriginalFormData] = useState<AgentFormData>(initialFormData)
  const [loading, setLoading] = useState(false)
  const [loadingAgents, setLoadingAgents] = useState(true)
  const [loadingStats, setLoadingStats] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [agentStats, setAgentStats] = useState<AgentStats | null>(null)
  const [showUnsavedWarning, setShowUnsavedWarning] = useState(false)
  const authToken = useAuthStore((state) => state.token)
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()

  // Handle 401 unauthorized - session expired
  const handleUnauthorized = useCallback(() => {
    toast.error('Session expired. Please login again.')
    logout()
    navigate('/login')
  }, [logout, navigate])

  // Check if form has unsaved changes
  const hasUnsavedChanges = useCallback(() => {
    if (!showModal) return false
    return (
      formData.name !== originalFormData.name ||
      formData.fid !== originalFormData.fid ||
      formData.token !== originalFormData.token ||
      formData.zone !== originalFormData.zone ||
      formData.is_active !== originalFormData.is_active
    )
  }, [showModal, formData, originalFormData])

  // Block navigation when there are unsaved changes
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges() && currentLocation.pathname !== nextLocation.pathname
  )

  // Fetch agents on component mount
  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    setLoadingAgents(true)
    setFetchError(null)
    try {
      const response = await fetch('http://localhost:8000/api/admin/agents', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setAgents(data)
      } else if (response.status === 401) {
        handleUnauthorized()
        return
      } else {
        setFetchError('Failed to load agents. Server returned an error.')
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error)
      setFetchError('Unable to connect to server. Please check your network connection.')
    } finally {
      setLoadingAgents(false)
    }
  }

  // Agent identification uses internal agent.id (NOT fid or token)
  // Deep link format: ?start=agent_{agent_id}
  const copyDeepLink = (agent: Agent) => {
    const link = agent.deep_link || `https://t.me/YourBotUsername?start=agent_${agent.id}`
    navigator.clipboard.writeText(link)
    toast.success('Deep link copied!')
  }

  const viewAgentStats = async (agent: Agent) => {
    setSelectedAgent(agent)
    setShowStatsModal(true)
    setLoadingStats(true)
    setAgentStats(null)

    try {
      const response = await fetch(`http://localhost:8000/api/admin/agents/${agent.id}/stats`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const stats = await response.json()
        setAgentStats(stats)
      } else if (response.status === 401) {
        handleUnauthorized()
        return
      } else {
        toast.error('Failed to load agent stats')
      }
    } catch (error) {
      console.error('Failed to fetch agent stats:', error)
      toast.error('Failed to load agent stats')
    } finally {
      setLoadingStats(false)
    }
  }

  const closeStatsModal = () => {
    setShowStatsModal(false)
    setSelectedAgent(null)
    setAgentStats(null)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate form
    if (!formData.name.trim()) {
      toast.error('Agent name is required')
      return
    }
    if (!formData.fid || isNaN(Number(formData.fid))) {
      toast.error('Valid Bill24 FID is required')
      return
    }
    if (!formData.token.trim()) {
      toast.error('Bill24 token is required')
      return
    }
    if (formData.token.trim().length < 10) {
      toast.error('Bill24 token must be at least 10 characters')
      return
    }

    setLoading(true)
    try {
      const url = editingAgent
        ? `http://localhost:8000/api/admin/agents/${editingAgent.id}`
        : 'http://localhost:8000/api/admin/agents'

      const response = await fetch(url, {
        method: editingAgent ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          name: formData.name.trim(),
          fid: Number(formData.fid),
          token: formData.token.trim(),
          zone: formData.zone,
          is_active: formData.is_active,
        }),
      })

      if (response.ok) {
        const savedAgent = await response.json()
        if (editingAgent) {
          setAgents(prev => prev.map(a => a.id === savedAgent.id ? savedAgent : a))
          toast.success('Agent updated successfully!')
        } else {
          setAgents(prev => [...prev, savedAgent])
          toast.success('Agent created successfully!')
        }
        closeModal()
      } else if (response.status === 401) {
        handleUnauthorized()
        return
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to save agent')
      }
    } catch (error) {
      console.error('Failed to save agent:', error)
      toast.error('Failed to save agent. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent)
    const editFormData = {
      name: agent.name,
      fid: String(agent.fid),
      token: agent.token || '',
      zone: agent.zone,
      is_active: agent.is_active,
    }
    setFormData(editFormData)
    setOriginalFormData(editFormData)
    setShowModal(true)
  }

  const handleDelete = async (agent: Agent) => {
    if (!confirm(`Are you sure you want to delete agent "${agent.name}"?`)) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/api/admin/agents/${agent.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })

      if (response.ok) {
        setAgents(prev => prev.filter(a => a.id !== agent.id))
        toast.success('Agent deleted successfully!')
      } else if (response.status === 401) {
        handleUnauthorized()
        return
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to delete agent')
      }
    } catch (error) {
      console.error('Failed to delete agent:', error)
      toast.error('Failed to delete agent')
    }
  }

  const openAddModal = () => {
    setEditingAgent(null)
    setFormData(initialFormData)
    setOriginalFormData(initialFormData)
    setShowModal(true)
  }

  const closeModal = () => {
    if (hasUnsavedChanges()) {
      setShowUnsavedWarning(true)
      return
    }
    forceCloseModal()
  }

  const forceCloseModal = () => {
    setShowModal(false)
    setEditingAgent(null)
    setFormData(initialFormData)
    setOriginalFormData(initialFormData)
    setShowUnsavedWarning(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        <button
          onClick={openAddModal}
          className="btn btn-primary"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Agent
        </button>
      </div>

      <div className="card overflow-x-auto">
        {loadingAgents ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary-600" />
            <p className="text-gray-500 mt-2">Loading agents...</p>
          </div>
        ) : fetchError ? (
          <div className="text-center py-12">
            <AlertTriangle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <p className="text-red-600 font-medium mb-2">Error Loading Agents</p>
            <p className="text-gray-500 mb-4">{fetchError}</p>
            <button
              onClick={fetchAgents}
              className="btn btn-primary"
            >
              Try Again
            </button>
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No agents yet</p>
            <button
              onClick={openAddModal}
              className="btn btn-primary"
            >
              <Plus className="h-5 w-5 mr-2" />
              Add Your First Agent
            </button>
          </div>
        ) : (
          <table className="table">
            <thead className="bg-gray-50">
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>FID (Bill24)</th>
                <th>Zone</th>
                <th>Status</th>
                <th>Deep Link</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td className="font-mono text-sm text-gray-500">{agent.id}</td>
                  <td className="font-medium max-w-[200px] truncate" title={agent.name}>
                    <Link
                      to={`/agents/${agent.id}`}
                      className="text-primary-600 hover:text-primary-800 hover:underline"
                    >
                      {agent.name}
                    </Link>
                  </td>
                  <td className="font-mono text-sm">{agent.fid}</td>
                  <td>
                    <span className={`badge ${agent.zone === 'real' ? 'badge-success' : 'badge-warning'}`}>
                      {agent.zone}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${agent.is_active ? 'badge-success' : 'badge-danger'}`}>
                      {agent.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => copyDeepLink(agent)}
                      className="text-primary-600 hover:text-primary-800 inline-flex items-center"
                    >
                      <Copy className="h-4 w-4 mr-1" />
                      Copy
                    </button>
                  </td>
                  <td>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => viewAgentStats(agent)}
                        className="text-primary-600 hover:text-primary-800"
                        title="View stats"
                      >
                        <BarChart3 className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleEdit(agent)}
                        className="text-gray-600 hover:text-gray-800"
                        title="Edit agent"
                      >
                        <Edit className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(agent)}
                        className="text-danger-600 hover:text-danger-800"
                        title="Delete agent"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">
                {editingAgent ? 'Edit Agent' : 'Add New Agent'}
              </h2>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Name *
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="e.g., Main Ticket Office"
                  className="w-full"
                  required
                />
              </div>

              <div>
                <label htmlFor="fid" className="block text-sm font-medium text-gray-700 mb-1">
                  Bill24 FID *
                </label>
                <input
                  id="fid"
                  name="fid"
                  type="number"
                  value={formData.fid}
                  onChange={handleInputChange}
                  placeholder="e.g., 12345"
                  className="w-full"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Frontend ID from Bill24/TixGear platform
                </p>
              </div>

              <div>
                <label htmlFor="token" className="block text-sm font-medium text-gray-700 mb-1">
                  Bill24 Token *
                </label>
                <input
                  id="token"
                  name="token"
                  type="password"
                  value={formData.token}
                  onChange={handleInputChange}
                  placeholder="API token"
                  className="w-full"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  API token for Bill24 authentication
                </p>
              </div>

              <div>
                <label htmlFor="zone" className="block text-sm font-medium text-gray-700 mb-1">
                  Zone *
                </label>
                <select
                  id="zone"
                  name="zone"
                  value={formData.zone}
                  onChange={handleInputChange}
                  className="w-full"
                >
                  <option value="test">Test (Sandbox)</option>
                  <option value="real">Real (Production)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Use "Test" for development, "Real" for production
                </p>
              </div>

              <div className="flex items-center">
                <input
                  id="is_active"
                  name="is_active"
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={handleInputChange}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300"
                />
                <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
                  Active (agent can receive orders)
                </label>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={closeModal}
                  className="btn btn-secondary"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      {editingAgent ? 'Update' : 'Create'} Agent
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Agent Stats Modal */}
      {showStatsModal && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">
                Agent Statistics
              </h2>
              <button
                onClick={closeStatsModal}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4">
              <p className="text-lg font-medium text-gray-900">{selectedAgent.name}</p>
              <p className="text-sm text-gray-500">ID: {selectedAgent.id} | FID: {selectedAgent.fid}</p>
            </div>

            {loadingStats ? (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary-600" />
                <p className="text-gray-500 mt-2">Loading stats...</p>
              </div>
            ) : agentStats ? (
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <Users className="h-8 w-8 mx-auto text-blue-600 mb-2" />
                  <p className="text-2xl font-bold text-blue-900">{agentStats.users}</p>
                  <p className="text-sm text-blue-600">Users</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <ShoppingCart className="h-8 w-8 mx-auto text-green-600 mb-2" />
                  <p className="text-2xl font-bold text-green-900">{agentStats.orders}</p>
                  <p className="text-sm text-green-600">Orders</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 text-center">
                  <DollarSign className="h-8 w-8 mx-auto text-purple-600 mb-2" />
                  <p className="text-2xl font-bold text-purple-900">₽{agentStats.revenue.toLocaleString()}</p>
                  <p className="text-sm text-purple-600">Revenue</p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">Failed to load statistics</p>
            )}

            <div className="mt-6 flex justify-end">
              <button
                onClick={closeStatsModal}
                className="btn btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Unsaved Changes Warning Dialog (for modal close) */}
      {showUnsavedWarning && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <div className="flex items-center mb-4">
              <AlertTriangle className="h-6 w-6 text-amber-500 mr-3" />
              <h2 className="text-lg font-bold text-gray-900">Unsaved Changes</h2>
            </div>
            <p className="text-gray-600 mb-6">
              You have unsaved changes. Are you sure you want to discard them?
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowUnsavedWarning(false)}
                className="btn btn-secondary"
              >
                Stay
              </button>
              <button
                onClick={forceCloseModal}
                className="btn btn-danger"
              >
                Discard Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Blocker Dialog (for route change) */}
      {blocker.state === 'blocked' && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <div className="flex items-center mb-4">
              <AlertTriangle className="h-6 w-6 text-amber-500 mr-3" />
              <h2 className="text-lg font-bold text-gray-900">Unsaved Changes</h2>
            </div>
            <p className="text-gray-600 mb-6">
              You have unsaved changes. Are you sure you want to leave this page?
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => blocker.reset?.()}
                className="btn btn-secondary"
              >
                Stay
              </button>
              <button
                onClick={() => {
                  forceCloseModal()
                  blocker.proceed?.()
                }}
                className="btn btn-danger"
              >
                Leave Page
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
