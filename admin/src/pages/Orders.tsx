import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Filter, Download, Loader2, X, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'

interface Agent {
  id: number
  name: string
}

interface Order {
  id: number
  user_id: number
  user_name: string
  agent_id: number
  agent_name: string
  status: string
  ticket_count: number
  total_amount: number
  created_at: string
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

  // Pagination state
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1', 10))
  const [totalPages, setTotalPages] = useState(5) // Mock total pages for testing
  const isInitialMount = useRef(true)

  // Reset page to 1 when filters change (but not on initial mount)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    setCurrentPage(1)
  }, [search, status, agentId, fromDate, toDate])

  // Update URL when filters or page change
  useEffect(() => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (status) params.set('status', status)
    if (agentId) params.set('agent_id', agentId)
    if (fromDate) params.set('from', fromDate)
    if (toDate) params.set('to', toDate)
    if (currentPage > 1) params.set('page', currentPage.toString())

    setSearchParams(params, { replace: true })
  }, [search, status, agentId, fromDate, toDate, currentPage, setSearchParams])

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

  // Check if any filters are active
  const hasActiveFilters = search || status || agentId || fromDate || toDate

  // Clear all filters (also resets page)
  const clearFilters = () => {
    setSearch('')
    setStatus('')
    setAgentId('')
    setFromDate('')
    setToDate('')
    setCurrentPage(1)
  }

  // Pagination handlers
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }

  // Export orders to CSV
  const exportOrders = async () => {
    try {
      // Fetch orders from API (with current filters)
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      if (agentId) params.set('agent_id', agentId)
      if (fromDate) params.set('from_date', fromDate)
      if (toDate) params.set('to_date', toDate)
      if (search) params.set('search', search)

      const response = await fetch(`http://localhost:8000/api/admin/orders?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      let orders: Order[] = []
      if (response.ok) {
        const data = await response.json()
        orders = data.orders || data || []
      }

      // Generate CSV content
      const headers = ['Order ID', 'User ID', 'User Name', 'Agent ID', 'Agent Name', 'Status', 'Tickets', 'Total Amount', 'Date']
      const csvRows = [headers.join(',')]

      orders.forEach((order: Order) => {
        const row = [
          order.id,
          order.user_id,
          `"${order.user_name || ''}"`,
          order.agent_id,
          `"${order.agent_name || ''}"`,
          order.status,
          order.ticket_count,
          order.total_amount,
          order.created_at
        ]
        csvRows.push(row.join(','))
      })

      // If no orders, add a note
      if (orders.length === 0) {
        csvRows.push('No orders found with current filters')
      }

      const csvContent = csvRows.join('\n')

      // Create and download the file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.setAttribute('href', url)
      link.setAttribute('download', `orders_export_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.success(`Exported ${orders.length} orders to CSV`)
    } catch (error) {
      console.error('Failed to export orders:', error)
      toast.error('Failed to export orders')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Orders</h1>
        <button onClick={exportOrders} className="btn btn-secondary">
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
            max={toDate || new Date().toISOString().split('T')[0]}
          />
          <input
            type="date"
            className="min-w-[150px]"
            placeholder="To"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            min={fromDate || undefined}
            max={new Date().toISOString().split('T')[0]}
          />
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="btn btn-secondary text-sm"
              title="Clear all filters"
            >
              <X className="h-4 w-4 mr-1" />
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Orders Table */}
      <div className="card overflow-x-auto">
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </button>
            {/* Page numbers */}
            <div className="flex items-center space-x-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  onClick={() => goToPage(page)}
                  className={`px-3 py-1 text-sm rounded ${
                    page === currentPage
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {page}
                </button>
              ))}
            </div>
            <button
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </button>
          </div>
        </div>
      )}

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
