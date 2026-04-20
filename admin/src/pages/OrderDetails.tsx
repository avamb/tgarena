import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Ticket, User, Building, Calendar, MapPin, DollarSign, Loader2, AlertCircle, CheckCircle, XCircle, Clock, Trash2, Ban } from 'lucide-react'
import { useAuthStore } from '../store/auth'
import toast from 'react-hot-toast'
import { apiUrl } from '../api'

interface TicketData {
  id: number
  order_id: number
  bil24_ticket_id: number
  event_name: string
  event_date: string
  venue_name: string
  sector: string | null
  row: string | null
  seat: string | null
  price: number
  barcode_number: string | null
  status: string
  sent_to_user: boolean
  sent_at: string | null
}

interface OrderDetail {
  id: number
  user_id: number
  user_name: string
  agent_id: number
  agent_name: string
  bil24_order_id: number
  status: string
  total_sum: number
  currency: string
  ticket_count: number
  created_at: string
  updated_at: string
  paid_at: string | null
  tickets: TicketData[]
}

export default function OrderDetails() {
  console.log('[OrderDetails] Component mounted')
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  console.log('[OrderDetails] Order ID from params:', id)
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const authToken = useAuthStore((state) => state.token)

  useEffect(() => {
    if (id) {
      fetchOrder()
    }
  }, [id])

  const fetchOrder = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(apiUrl(`/api/admin/orders/${id}`), {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setOrder(data)
      } else if (response.status === 404) {
        setError('Order not found')
      } else if (response.status === 401) {
        setError('Session expired. Please login again.')
      } else {
        setError('Failed to load order details')
      }
    } catch (err) {
      console.error('Failed to fetch order:', err)
      setError('Failed to load order details. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'NEW':
        return (
          <span className="badge badge-info flex items-center gap-1">
            <Clock className="h-3 w-3" />
            New
          </span>
        )
      case 'PROCESSING':
        return (
          <span className="badge badge-warning flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Processing
          </span>
        )
      case 'PAID':
        return (
          <span className="badge badge-success flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Paid
          </span>
        )
      case 'CANCELLED':
        return (
          <span className="badge badge-danger flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Cancelled
          </span>
        )
      default:
        return <span className="badge badge-secondary">{status}</span>
    }
  }

  const getTicketStatusBadge = (status: string, sentToUser: boolean) => {
    if (status === 'VALID') {
      return sentToUser ? (
        <span className="badge badge-success">Sent</span>
      ) : (
        <span className="badge badge-warning">Pending Delivery</span>
      )
    }
    return <span className="badge badge-danger">{status}</span>
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

  const formatCurrency = (amount: number, currency: string = 'RUB') => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: currency,
    }).format(amount)
  }

  const handleCancelOrder = async () => {
    if (!order || order.status === 'CANCELLED') return

    const confirmed = window.confirm(
      `Are you sure you want to cancel Order #${order.id}?\n\nThis will also mark all ${order.ticket_count} ticket(s) as cancelled.`
    )
    if (!confirmed) return

    setActionLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/orders/${order.id}/cancel`), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        toast.success(data.message || 'Order cancelled successfully')
        // Refresh order data
        fetchOrder()
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to cancel order')
      }
    } catch (err) {
      console.error('Failed to cancel order:', err)
      toast.error('Failed to cancel order. Check your connection.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteOrder = async () => {
    if (!order) return

    const confirmed = window.confirm(
      `Are you sure you want to DELETE Order #${order.id}?\n\nThis will permanently delete the order and all ${order.ticket_count} ticket(s). This action cannot be undone.`
    )
    if (!confirmed) return

    setActionLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/orders/${order.id}`), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        toast.success(data.message || 'Order deleted successfully')
        // Navigate back to orders list
        navigate('/orders')
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to delete order')
      }
    } catch (err) {
      console.error('Failed to delete order:', err)
      toast.error('Failed to delete order. Check your connection.')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <span className="ml-2 text-gray-500">Loading order details...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/orders" className="inline-flex items-center text-primary-600 hover:text-primary-800">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Orders
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

  if (!order) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/orders" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Order #{order.id}</h1>
          {getStatusBadge(order.status)}
        </div>
        <div className="flex items-center space-x-2">
          {order.status !== 'CANCELLED' && (
            <button
              onClick={handleCancelOrder}
              disabled={actionLoading}
              className="btn btn-secondary text-amber-600 hover:text-amber-700 hover:bg-amber-50 border-amber-300"
            >
              {actionLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Ban className="h-4 w-4 mr-2" />
              )}
              Cancel Order
            </button>
          )}
          <button
            onClick={handleDeleteOrder}
            disabled={actionLoading}
            className="btn btn-secondary text-red-600 hover:text-red-700 hover:bg-red-50 border-red-300"
          >
            {actionLoading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Trash2 className="h-4 w-4 mr-2" />
            )}
            Delete
          </button>
        </div>
      </div>

      {/* Order Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-center">
            <DollarSign className="h-10 w-10 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-blue-600">Total Amount</p>
              <p className="text-2xl font-bold text-blue-900">
                {formatCurrency(order.total_sum, order.currency)}
              </p>
            </div>
          </div>
        </div>
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center">
            <Ticket className="h-10 w-10 text-green-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-green-600">Tickets</p>
              <p className="text-2xl font-bold text-green-900">{order.ticket_count}</p>
            </div>
          </div>
        </div>
        <div className="card bg-purple-50 border-purple-200">
          <div className="flex items-center">
            <User className="h-10 w-10 text-purple-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-purple-600">Customer</p>
              <Link
                to={`/users/${order.user_id}`}
                className="text-lg font-bold text-purple-900 hover:underline"
              >
                {order.user_name}
              </Link>
            </div>
          </div>
        </div>
        <div className="card bg-amber-50 border-amber-200">
          <div className="flex items-center">
            <Building className="h-10 w-10 text-amber-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-amber-600">Agent</p>
              <Link
                to={`/agents/${order.agent_id}`}
                className="text-lg font-bold text-amber-900 hover:underline"
              >
                {order.agent_name}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Order Info Card */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Order Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-500">Order ID</label>
            <p className="mt-1 text-sm text-gray-900 font-mono">{order.id}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Bill24 Order ID</label>
            <p className="mt-1 text-sm text-gray-900 font-mono">{order.bil24_order_id}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Status</label>
            <div className="mt-1">{getStatusBadge(order.status)}</div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Created At</label>
            <p className="mt-1 text-sm text-gray-900">{formatDate(order.created_at)}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Updated At</label>
            <p className="mt-1 text-sm text-gray-900">{formatDate(order.updated_at)}</p>
          </div>
          {order.paid_at && (
            <div>
              <label className="block text-sm font-medium text-gray-500">Paid At</label>
              <p className="mt-1 text-sm text-gray-900">{formatDate(order.paid_at)}</p>
            </div>
          )}
        </div>
      </div>

      {/* Tickets */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">
          Tickets ({order.tickets.length})
        </h2>
        {order.tickets.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Ticket className="h-12 w-12 mx-auto text-gray-400 mb-2" />
            <p>No tickets in this order</p>
          </div>
        ) : (
          <div className="space-y-4">
            {order.tickets.map((ticket) => (
              <div key={ticket.id} className="border rounded-lg p-4 hover:bg-gray-50">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">{ticket.event_name}</h3>
                    <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {formatDate(ticket.event_date)}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {ticket.venue_name}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {getTicketStatusBadge(ticket.status, ticket.sent_to_user)}
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  {ticket.sector && (
                    <div>
                      <span className="text-gray-500">Sector:</span>{' '}
                      <span className="font-medium">{ticket.sector}</span>
                    </div>
                  )}
                  {ticket.row && (
                    <div>
                      <span className="text-gray-500">Row:</span>{' '}
                      <span className="font-medium">{ticket.row}</span>
                    </div>
                  )}
                  {ticket.seat && (
                    <div>
                      <span className="text-gray-500">Seat:</span>{' '}
                      <span className="font-medium">{ticket.seat}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-500">Price:</span>{' '}
                    <span className="font-medium">{formatCurrency(ticket.price, order.currency)}</span>
                  </div>
                  {ticket.barcode_number && (
                    <div className="md:col-span-2">
                      <span className="text-gray-500">Barcode:</span>{' '}
                      <span className="font-mono">{ticket.barcode_number}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
