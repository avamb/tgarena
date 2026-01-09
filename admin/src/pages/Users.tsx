import { useState, useEffect, useCallback } from 'react'
import { Search, Filter, Loader2 } from 'lucide-react'
import { useAuthStore } from '../store/auth'

interface Agent {
  id: number
  name: string
  fid: number
  zone: string
  is_active: boolean
}

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

export default function Users() {
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [agents, setAgents] = useState<Agent[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const { token } = useAuthStore()

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  // Fetch agents for dropdown
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/admin/agents', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })
        if (response.ok) {
          const data = await response.json()
          setAgents(data)
        }
      } catch (error) {
        console.error('Failed to fetch agents:', error)
      }
    }

    if (token) {
      fetchAgents()
    }
  }, [token])

  // Fetch users with search and filter
  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (debouncedSearch) {
        params.append('search', debouncedSearch)
      }
      if (selectedAgentId) {
        params.append('agent_id', selectedAgentId)
      }

      const url = `http://localhost:8000/api/admin/users${params.toString() ? '?' + params.toString() : ''}`
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      }
    } catch (error) {
      console.error('Failed to fetch users:', error)
    } finally {
      setLoading(false)
    }
  }, [token, debouncedSearch, selectedAgentId])

  useEffect(() => {
    if (token) {
      fetchUsers()
    }
  }, [token, fetchUsers])

  const getAgentName = (agentId: number | null) => {
    if (!agentId) return '-'
    const agent = agents.find(a => a.id === agentId)
    return agent ? agent.name : `Agent #${agentId}`
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Users</h1>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search users..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 w-full"
              />
            </div>
          </div>
          <select
            className="min-w-[150px]"
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
          >
            <option value="">All Agents</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
          <button className="btn btn-secondary">
            <Filter className="h-5 w-5 mr-2" />
            More Filters
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary-600" />
            <p className="text-gray-500 mt-2">Loading users...</p>
          </div>
        ) : (
          <table className="table">
            <thead className="bg-gray-50">
              <tr>
                <th>Chat ID</th>
                <th>Username</th>
                <th>Name</th>
                <th>Agent</th>
                <th>Language</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500">
                    {debouncedSearch || selectedAgentId ? 'No users found matching your criteria' : 'No users yet'}
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id}>
                    <td className="font-mono text-sm">{user.telegram_chat_id}</td>
                    <td>
                      {user.telegram_username ? (
                        <span className="text-primary-600">@{user.telegram_username}</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="font-medium">
                      {user.telegram_first_name}
                      {user.telegram_last_name && ` ${user.telegram_last_name}`}
                    </td>
                    <td>{getAgentName(user.current_agent_id)}</td>
                    <td>
                      <span className={`badge ${user.preferred_language === 'ru' ? 'badge-primary' : 'badge-secondary'}`}>
                        {user.preferred_language.toUpperCase()}
                      </span>
                    </td>
                    <td className="text-gray-500 text-sm">{formatDate(user.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
