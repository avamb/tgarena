import { useState, useEffect, useCallback, useRef } from 'react'
import { Plus, Edit, Trash2, Copy, X, Save, Loader2, BarChart3, Users, ShoppingCart, DollarSign, AlertTriangle, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'
import { useBlocker, useNavigate, Link, useSearchParams } from 'react-router-dom'
import { apiUrl } from '../api'

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
  revenue_by_currency: CurrencyBreakdown[]
}

interface CurrencyBreakdown {
  currency: string
  amount: number
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
  const [searchParams, setSearchParams] = useSearchParams()
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

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1', 10))
  const [totalPages, setTotalPages] = useState(1)
  const [totalAgents, setTotalAgents] = useState(0)
  const pageSize = 10
  const isInitialMount = useRef(true)
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  const handleUnauthorized = useCallback(() => {
    toast.error('Session expired. Please login again.')
    logout()
    navigate('/login')
  }, [logout, navigate])

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

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges() && currentLocation.pathname !== nextLocation.pathname
  )

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    setCurrentPage(1)
  }, [search])

  useEffect(() => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (currentPage > 1) params.set('page', currentPage.toString())
    setSearchParams(params, { replace: true })
  }, [search, currentPage, setSearchParams])

  useEffect(() => {
    fetchAgents()
  }, [currentPage, search])

  const fetchAgents = async () => {
    setLoadingAgents(true)
    setFetchError(null)
    try {
      const params = new URLSearchParams()
      params.set('page', currentPage.toString())
      params.set('page_size', pageSize.toString())
      if (search) params.set('search', search)

      const response = await fetch(apiUrl(`/api/admin/agents?${params.toString()}`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setAgents(data.agents || [])
        setTotalPages(data.total_pages || 1)
        setTotalAgents(data.total || 0)
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

  const handleSearchChange = (value: string) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
    searchTimeoutRef.current = setTimeout(() => {
      setSearch(value)
    }, 300)
  }

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }

  const copyDeepLink = (agent: Agent) => {
    const link = agent.deep_link
    if (!link) {
      toast.error('Deep link is not available for this agent yet')
      return
    }
    navigator.clipboard.writeText(link)
    toast.success('Deep link copied!')
  }

  const viewAgentStats = async (agent: Agent) => {
    setSelectedAgent(agent)
    setShowStatsModal(true)
    setLoadingStats(true)
    setAgentStats(null)

    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${agent.id}/stats`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
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
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

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
        ? apiUrl(`/api/admin/agents/${editingAgent.id}`)
        : apiUrl('/api/admin/agents')

      const response = await fetch(url, {
        method: editingAgent ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
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
          setAgents((prev) => prev.map((agent) => (agent.id === savedAgent.id ? savedAgent : agent)))
          toast.success('Agent updated successfully!')
        } else {
          setAgents((prev) => [...prev, savedAgent])
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
      const response = await fetch(apiUrl(`/api/admin/agents/${agent.id}`), {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (response.ok) {
        setAgents((prev) => prev.filter((item) => item.id !== agent.id))
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        <button onClick={openAddModal} className="btn btn-primary">
          <Plus className="mr-2 h-5 w-5" />
          Add Agent
        </button>
      </div>

      <div className="card">
        <div className="flex items-center gap-4">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform text-gray-400" />
            <input
              type="text"
              placeholder="Search agents by name or FID..."
              defaultValue={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full pl-10"
            />
          </div>
          {search && (
            <button
              onClick={() => {
                setSearch('')
                const input = document.querySelector('input[placeholder*="Search agents"]') as HTMLInputElement
                if (input) input.value = ''
              }}
              className="btn btn-secondary text-sm"
            >
              <X className="mr-1 h-4 w-4" />
              Clear
            </button>
          )}
          <div className="text-sm text-gray-500">
            {totalAgents} agent{totalAgents !== 1 ? 's' : ''} total
          </div>
        </div>
      </div>

      <div className="card overflow-x-auto">
        {loadingAgents ? (
          <div className="py-12 text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary-600" />
            <p className="mt-2 text-gray-500">Loading agents...</p>
          </div>
        ) : fetchError ? (
          <div className="py-12 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-red-500" />
            <p className="mb-2 font-medium text-red-600">Error Loading Agents</p>
            <p className="mb-4 text-gray-500">{fetchError}</p>
            <button onClick={fetchAgents} className="btn btn-primary">
              Try Again
            </button>
          </div>
        ) : agents.length === 0 ? (
          <div className="py-12 text-center">
            <p className="mb-4 text-gray-500">No agents yet</p>
            <button onClick={openAddModal} className="btn btn-primary">
              <Plus className="mr-2 h-5 w-5" />
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
                  <td className="max-w-[200px] truncate font-medium" title={agent.name}>
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
                      className="inline-flex items-center text-primary-600 hover:text-primary-800"
                    >
                      <Copy className="mr-1 h-4 w-4" />
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

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="btn btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              Previous
            </button>
            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                let page: number
                if (totalPages <= 5) {
                  page = i + 1
                } else if (currentPage <= 3) {
                  page = i + 1
                } else if (currentPage >= totalPages - 2) {
                  page = totalPages - 4 + i
                } else {
                  page = currentPage - 2 + i
                }
                return (
                  <button
                    key={page}
                    onClick={() => goToPage(page)}
                    className={`rounded px-3 py-1 text-sm ${
                      page === currentPage
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {page}
                  </button>
                )
              })}
            </div>
            <button
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="btn btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
              <ChevronRight className="ml-1 h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="mx-4 w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">{editingAgent ? 'Edit Agent' : 'Add New Agent'}</h2>
              <button onClick={closeModal} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700">
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
                <label htmlFor="fid" className="mb-1 block text-sm font-medium text-gray-700">
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
                <p className="mt-1 text-xs text-gray-500">Frontend ID from Bill24/TixGear platform</p>
              </div>

              <div>
                <label htmlFor="token" className="mb-1 block text-sm font-medium text-gray-700">
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
                <p className="mt-1 text-xs text-gray-500">API token for Bill24 authentication</p>
              </div>

              <div>
                <label htmlFor="zone" className="mb-1 block text-sm font-medium text-gray-700">
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
                <p className="mt-1 text-xs text-gray-500">Use "Test" for development, "Real" for production</p>
              </div>

              <div className="flex items-center">
                <input
                  id="is_active"
                  name="is_active"
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={handleInputChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600"
                />
                <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
                  Active (agent can receive orders)
                </label>
              </div>

              <div className="flex justify-end space-x-3 border-t pt-4">
                <button type="button" onClick={closeModal} className="btn btn-secondary" disabled={loading}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      {editingAgent ? 'Update' : 'Create'} Agent
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showStatsModal && selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="mx-4 w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">Agent Statistics</h2>
              <button onClick={closeStatsModal} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4">
              <p className="text-lg font-medium text-gray-900">{selectedAgent.name}</p>
              <p className="text-sm text-gray-500">ID: {selectedAgent.id} | FID: {selectedAgent.fid}</p>
            </div>

            {loadingStats ? (
              <div className="py-8 text-center">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary-600" />
                <p className="mt-2 text-gray-500">Loading stats...</p>
              </div>
            ) : agentStats ? (
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-blue-50 p-4 text-center">
                  <Users className="mx-auto mb-2 h-8 w-8 text-blue-600" />
                  <p className="text-2xl font-bold text-blue-900">{agentStats.users}</p>
                  <p className="text-sm text-blue-600">Users</p>
                </div>
                <div className="rounded-lg bg-green-50 p-4 text-center">
                  <ShoppingCart className="mx-auto mb-2 h-8 w-8 text-green-600" />
                  <p className="text-2xl font-bold text-green-900">{agentStats.orders}</p>
                  <p className="text-sm text-green-600">Orders</p>
                </div>
                <div className="rounded-lg bg-purple-50 p-4 text-center">
                  <DollarSign className="mx-auto mb-2 h-8 w-8 text-purple-600" />
                  <div className="space-y-1 text-2xl font-bold text-purple-900">
                    {agentStats.revenue_by_currency?.length ? (
                      agentStats.revenue_by_currency.map((item) => (
                        <p key={item.currency}>{formatCurrency(item.amount, item.currency)}</p>
                      ))
                    ) : (
                      <p>0</p>
                    )}
                  </div>
                  <p className="text-sm text-purple-600">Revenue</p>
                </div>
              </div>
            ) : (
              <p className="py-4 text-center text-gray-500">Failed to load statistics</p>
            )}

            <div className="mt-6 flex justify-end">
              <button onClick={closeStatsModal} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {showUnsavedWarning && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50">
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center">
              <AlertTriangle className="mr-3 h-6 w-6 text-amber-500" />
              <h2 className="text-lg font-bold text-gray-900">Unsaved Changes</h2>
            </div>
            <p className="mb-6 text-gray-600">
              You have unsaved changes. Are you sure you want to discard them?
            </p>
            <div className="flex justify-end space-x-3">
              <button onClick={() => setShowUnsavedWarning(false)} className="btn btn-secondary">
                Stay
              </button>
              <button onClick={forceCloseModal} className="btn btn-danger">
                Discard Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {blocker.state === 'blocked' && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50">
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center">
              <AlertTriangle className="mr-3 h-6 w-6 text-amber-500" />
              <h2 className="text-lg font-bold text-gray-900">Unsaved Changes</h2>
            </div>
            <p className="mb-6 text-gray-600">
              You have unsaved changes. Are you sure you want to leave this page?
            </p>
            <div className="flex justify-end space-x-3">
              <button onClick={() => blocker.reset?.()} className="btn btn-secondary">
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
