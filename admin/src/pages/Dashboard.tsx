import { useState, useEffect } from 'react'
import { Users, ShoppingCart, DollarSign, Activity, Loader2 } from 'lucide-react'
import { useAuthStore } from '../store/auth'
import { apiUrl } from '../api'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DashboardStats {
  total_users: number
  total_orders: number
  total_revenue: number
  revenue_by_currency: CurrencyBreakdown[]
  active_agents: number
  orders_today: number
  revenue_today: number
  revenue_today_by_currency: CurrencyBreakdown[]
}

interface CurrencyBreakdown {
  currency: string
  amount: number
}

interface ChartDataPoint {
  date: string
  orders: number
  revenue: number
}

interface RecentOrder {
  id: number
  bil24_order_id: number
  user_name: string
  agent_name: string
  status: string
  total_sum: number
  currency: string
  ticket_count: number
  created_at: string
}

type ChartPeriod = 'week' | 'month' | 'year'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('week')
  const [chartLoading, setChartLoading] = useState(true)
  const [recentOrders, setRecentOrders] = useState<RecentOrder[]>([])
  const [ordersLoading, setOrdersLoading] = useState(true)
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

  const formatRevenueSummary = (breakdown: CurrencyBreakdown[]) => {
    if (!breakdown.length) return ['0']
    if (breakdown.length === 1) {
      const item = breakdown[0]
      return [formatCurrency(item.amount, item.currency)]
    }
    return breakdown.map((item) => formatCurrency(item.amount, item.currency))
  }

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch(apiUrl('/api/admin/dashboard/stats'), {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch dashboard stats')
        }

        const data = await response.json()
        setStats(data)
      } catch (err) {
        console.error('Error fetching stats:', err)
        setError('Failed to load dashboard statistics')
        setStats({
          total_users: 0,
          total_orders: 0,
          total_revenue: 0,
          revenue_by_currency: [],
          active_agents: 0,
          orders_today: 0,
          revenue_today: 0,
          revenue_today_by_currency: [],
        })
      } finally {
        setLoading(false)
      }
    }

    if (authToken) {
      fetchStats()
    }
  }, [authToken])

  useEffect(() => {
    const fetchRecentOrders = async () => {
      try {
        setOrdersLoading(true)
        const response = await fetch(apiUrl('/api/admin/dashboard/recent-orders?limit=5'), {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          setRecentOrders(data)
        }
      } catch (err) {
        console.error('Error fetching recent orders:', err)
      } finally {
        setOrdersLoading(false)
      }
    }

    if (authToken) {
      fetchRecentOrders()
    }
  }, [authToken])

  useEffect(() => {
    const fetchChartData = async () => {
      try {
        setChartLoading(true)
        const response = await fetch(apiUrl(`/api/admin/dashboard/sales-chart?period=${chartPeriod}`), {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          if (data.labels && data.data) {
            const chartPoints = data.labels.map((label: string, index: number) => ({
              date: label,
              orders: data.data[index]?.orders || 0,
              revenue: data.data[index]?.revenue || 0,
            }))
            setChartData(chartPoints)
          } else {
            setChartData(generateSampleData(chartPeriod))
          }
        } else {
          setChartData(generateSampleData(chartPeriod))
        }
      } catch (err) {
        console.error('Error fetching chart data:', err)
        setChartData(generateSampleData(chartPeriod))
      } finally {
        setChartLoading(false)
      }
    }

    if (authToken) {
      fetchChartData()
    }
  }, [authToken, chartPeriod])

  const generateSampleData = (period: ChartPeriod): ChartDataPoint[] => {
    const now = new Date()
    const data: ChartDataPoint[] = []

    const days = period === 'week' ? 7 : period === 'month' ? 30 : 12
    const format = period === 'year' ? 'month' : 'day'

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now)
      if (format === 'day') {
        date.setDate(date.getDate() - i)
        data.push({
          date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          orders: 0,
          revenue: 0,
        })
      } else {
        date.setMonth(date.getMonth() - i)
        data.push({
          date: date.toLocaleDateString('en-US', { month: 'short' }),
          orders: 0,
          revenue: 0,
        })
      }
    }

    return data
  }

  const statsConfig = [
    { name: 'Total Users', value: stats?.total_users ?? 0, icon: Users, color: 'bg-blue-500' },
    { name: 'Total Orders', value: stats?.total_orders ?? 0, icon: ShoppingCart, color: 'bg-green-500' },
    { name: 'Revenue', value: formatRevenueSummary(stats?.revenue_by_currency ?? []), icon: DollarSign, color: 'bg-yellow-500' },
    { name: 'Active Agents', value: stats?.active_agents ?? 0, icon: Activity, color: 'bg-purple-500' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {statsConfig.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center">
              <div className={`${stat.color} rounded-lg p-3`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                {loading ? (
                  <Loader2 className="mt-1 h-6 w-6 animate-spin text-gray-400" />
                ) : Array.isArray(stat.value) ? (
                  <div className="space-y-1">
                    {stat.value.map((value) => (
                      <p key={value} className="text-lg font-semibold text-gray-900">
                        {value}
                      </p>
                    ))}
                  </div>
                ) : (
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          {error}
        </div>
      )}

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold">Recent Orders</h2>
        {ordersLoading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : recentOrders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Order ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {recentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">#{order.id}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">{order.user_name}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">{order.agent_name}</td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${
                          order.status === 'PAID'
                            ? 'bg-green-100 text-green-800'
                            : order.status === 'CANCELLED'
                              ? 'bg-red-100 text-red-800'
                              : order.status === 'PROCESSING'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {order.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {formatCurrency(order.total_sum, order.currency)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                      {new Date(order.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500">No orders yet.</p>
        )}
      </div>

      <div className="card">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Sales Overview</h2>
          <div className="flex space-x-2">
            <button
              onClick={() => setChartPeriod('week')}
              className={`rounded px-3 py-1 text-sm ${
                chartPeriod === 'week' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Week
            </button>
            <button
              onClick={() => setChartPeriod('month')}
              className={`rounded px-3 py-1 text-sm ${
                chartPeriod === 'month' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Month
            </button>
            <button
              onClick={() => setChartPeriod('year')}
              className={`rounded px-3 py-1 text-sm ${
                chartPeriod === 'year' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Year
            </button>
          </div>
        </div>
        <div className="h-64">
          {chartLoading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: '#e5e7eb' }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: '#e5e7eb' }}
                  label={{ value: 'Orders', angle: -90, position: 'insideLeft', fontSize: 12 }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: '#e5e7eb' }}
                  label={{ value: 'Revenue', angle: 90, position: 'insideRight', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => [
                    name === 'revenue' ? value.toLocaleString() : value,
                    name === 'revenue' ? 'Revenue' : 'Orders',
                  ]}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="orders"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Orders"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="revenue"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ fill: '#10b981', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Revenue"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-gray-500">
              No sales data available
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
