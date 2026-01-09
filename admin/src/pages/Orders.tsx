import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Filter, Download, Loader2 } from 'lucide-react'
import { useAuthStore } from '../store/auth'

interface Agent {
  id: number
  name: string
}

export default function Orders() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const { token } = useAuthStore()

  // Initialize state from URL params
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [agentId, setAgentId] = useState(searchParams.get('agent_id') || '')
  const [fromDate, setFromDate] = useState(searchParams.get('from') || '')
  const [toDate, setToDate] = useState(searchParams.get('to') || '')

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (status) params.set('status', status)
    if (agentId) params.set('agent_id', agentId)
    if (fromDate) params.set('from', fromDate)
    if (toDate) params.set('to', toDate)

    setSearchParams(params, { replace: true })
  }, [search, status, agentId, fromDate, toDate, setSearchParams])

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

  const getStatusBadgeClass = (statusValue: string) => {
    switch (statusValue) {
      case 'NEW':
        return 'badge-info'
      case 'PROCESSING':
        return 'badge-warning'
      case 'PAID':
        return 'badge-success'
      case 'CANCELLED':
        return 'badge-danger'
      default:
        return 'badge-secondary'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Orders</h1>
        <button className="btn btn-secondary">
          <Download className="h-5 w-5 mr-2" />
          Export
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search orders..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 w-full"
              />
            </div>
          </div>
          <select
            className="min-w-[150px]"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="NEW">New</option>
            <option value="PROCESSING">Processing</option>
            <option value="PAID">Paid</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
          <select
            className="min-w-[150px]"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
          >
            <option value="">All Agents</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
          <input
            type="date"
            className="min-w-[150px]"
            placeholder="From"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
          <input
            type="date"
            className="min-w-[150px]"
            placeholder="To"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>
      </div>

      {/* Orders Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary-600" />
            <p className="text-gray-500 mt-2">Loading orders...</p>
          </div>
        ) : (
          <table className="table">
            <thead className="bg-gray-50">
              <tr>
                <th>Order ID</th>
                <th>User</th>
                <th>Agent</th>
                <th>Status</th>
                <th>Tickets</th>
                <th>Total</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-500">
                  No orders yet
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* Current filters display for debugging/verification */}
      {(status || agentId || fromDate || toDate) && (
        <div className="text-sm text-gray-500">
          Active filters:
          {status && <span className="ml-2 badge badge-info">{status}</span>}
          {agentId && <span className="ml-2 badge badge-info">Agent: {agents.find(a => a.id === Number(agentId))?.name || agentId}</span>}
          {fromDate && <span className="ml-2 badge badge-info">From: {fromDate}</span>}
          {toDate && <span className="ml-2 badge badge-info">To: {toDate}</span>}
        </div>
      )}
    </div>
  )
}
