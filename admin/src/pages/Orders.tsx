import { useState, useEffect, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Search, Download, Loader2, X, ChevronLeft, ChevronRight, AlertCircle, ShoppingCart } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'
import { apiUrl } from '../api'

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
  bil24_order_id: number
  status: string
  ticket_count: number
  total_sum: number
  currency: string
  created_at: string
  paid_at: string | null
}

interface PaginatedOrdersResponse {
  orders: Order[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function Orders() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [agents, setAgents] = useState<Agent[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const { token } = useAuthStore()

  // Initialize state from URL params
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [agentId, setAgentId] = useState(searchParams.get('agent_id') || '')
  const [fromDate, setFromDate] = useState(searchParams.get('from') || '')
  const [toDate, setToDate] = useState(searchParams.get('to') || '')

  // Pagination state
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1', 10))
  const [totalPages, setTotalPages] = useState(1)
  const pageSize = 20
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
        const response = await fetch(apiUrl('/api/admin/agents'), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })
        if (response.ok) {
          const data = await response.json()
          setAgents(data.agents || [])
        }
      } catch (error) {
        console.error('Failed to fetch agents:', error)
      }
    }

    if (token) {
      fetchAgents()
    }
  }, [token])

  // Fetch orders
  useEffect(() => {
    const fetchOrders = async () => {
      setLoading(true)
      setFetchError(null)
      try {
        const params = new URLSearchParams()
        if (status) params.set('order_status', status)
        if (agentId) params.set('agent_id', agentId)
        if (fromDate) params.set('start_date', fromDate)
        if (toDate) params.set('end_date', toDate)
        if (search) params.set('search', search)
        params.set('page', currentPage.toString())
        params.set('page_size', pageSize.toString())

        const response = await fetch(apiUrl(`/api/admin/orders?${params.toString()}`), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data: PaginatedOrdersResponse = await response.json()
          setOrders(data.orders)
          setTotal(data.total)
          setTotalPages(data.total_pages)
        } else if (response.status === 401) {
          setFetchError('Session expired. Please login again.')
        } else {
          setFetchError('Failed to load orders')
        }
      } catch (error) {
        console.error('Failed to fetch orders:', error)
        setFetchError('Unable to connect to server. Please check your network connection.')
      } finally {
        setLoading(false)
      }
    }

    if (token) {
      fetchOrders()
    }
  }, [token, status, agentId, fromDate, toDate, search, currentPage])

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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

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

  // Export orders to CSV
  const exportOrders = async () => {
    try {
      // Fetch all orders with current filters (no pagination limit)
      const params = new URLSearchParams()
      if (status) params.set('order_status', status)
      if (agentId) params.set('agent_id', agentId)
      if (fromDate) params.set('start_date', fromDate)
      if (toDate) params.set('end_date', toDate)
      if (search) params.set('search', search)
      params.set('page_size', '1000') // Get more orders for export

      const response = await fetch(apiUrl(`/api/admin/orders?${params.toString()}`), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      let ordersToExport: Order[] = []
      if (response.ok) {
        const data = await response.json()
        ordersToExport = data.orders || []
      }

      // Generate CSV content
      const headers = ['Order ID', 'Bill24 ID', 'User ID', 'User Name', 'Agent ID', 'Agent Name', 'Status', 'Tickets', 'Total Amount', 'Currency', 'Date', 'Paid At']
      const csvRows = [headers.join(',')]

      ordersToExport.forEach((order: Order) => {
        const row = [
          order.id,
          order.bil24_order_id,
          order.user_id,
          `"${order.user_name || ''}"`,
          order.agent_id,
          `"${order.agent_name || ''}"`,
          order.status,
          order.ticket_count,
          order.total_sum,
          order.currency,
          order.created_at,
          order.paid_at || ''
        ]
        csvRows.push(row.join(','))
      })

      // If no orders, add a note
      if (ordersToExport.length === 0) {
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

      toast.success(`Exported ${ordersToExport.length} orders to CSV`)
    } catch (error) {
      console.error('Failed to export orders:', error)
      toast.error('Failed to export orders')
    }
  }

  // Retry function for error state
  const retryFetch = () => {
    setFetchError(null)
    setLoading(true)
    // Trigger refetch by setting a new currentPage value then back
    setCurrentPage(prev => prev)
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
                placeholder="Search by order ID..."
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
        {fetchError ? (
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Orders</h3>
            <p className="text-gray-500 mb-4">{fetchError}</p>
            <button onClick={retryFetch} className="btn btn-primary">
              Try Again
            </button>
          </div>
        ) : loading ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary-600" />
            <p className="text-gray-500 mt-2">Loading orders...</p>
          </div>
        ) : orders.length === 0 ? (
          <div className="text-center py-12">
            <ShoppingCart className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No orders yet</h3>
            <p className="text-gray-500">
              {hasActiveFilters
                ? 'No orders match your filters. Try adjusting your search criteria.'
                : 'Orders will appear here when customers make purchases.'}
            </p>
          </div>
        ) : (
          <>
            <div className="text-sm text-gray-500 mb-4">
              {total} order{total !== 1 ? 's' : ''} total
            </div>
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
                {orders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td>
                      <Link
                        to={`/orders/${order.id}`}
                        className="text-primary-600 hover:text-primary-800 font-medium"
                      >
                        #{order.id}
                      </Link>
                      <div className="text-xs text-gray-400">Bill24: {order.bil24_order_id}</div>
                    </td>
                    <td>
                      <Link
                        to={`/users/${order.user_id}`}
                        className="text-gray-900 hover:text-primary-600"
                      >
                        {order.user_name}
                      </Link>
                    </td>
                    <td>
                      <Link
                        to={`/agents/${order.agent_id}`}
                        className="text-gray-900 hover:text-primary-600"
                      >
                        {order.agent_name}
                      </Link>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(order.status)}`}>
                        {order.status}
                      </span>
                    </td>
                    <td>{order.ticket_count}</td>
                    <td>{formatCurrency(order.total_sum, order.currency)}</td>
                    <td className="text-sm text-gray-500">{formatDate(order.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && !loading && !fetchError && (
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
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                // Show pages around current page
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
                    className={`px-3 py-1 text-sm rounded ${
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
