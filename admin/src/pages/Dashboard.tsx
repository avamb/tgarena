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
  active_agents: number
  orders_today: number
  revenue_today: number
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

  // Fetch dashboard stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch(apiUrl('/api/admin/dashboard/stats'), {
          headers: {
            'Authorization': `Bearer ${authToken}`,
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
        // Set default values on error
        setStats({
          total_users: 0,
          total_orders: 0,
          total_revenue: 0,
          active_agents: 0,
          orders_today: 0,
          revenue_today: 0,
        })
      } finally {
        setLoading(false)
      }
    }

    if (authToken) {
      fetchStats()
    }
  }, [authToken])

  // Fetch recent orders
  useEffect(() => {
    const fetchRecentOrders = async () => {
      try {
        setOrdersLoading(true)
        const response = await fetch(apiUrl('/api/admin/dashboard/recent-orders?limit=5'), {
          headers: {
            'Authorization': `Bearer ${authToken}`,
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

  // Fetch chart data
  useEffect(() => {
    const fetchChartData = async () => {
      try {
        setChartLoading(true)
        const response = await fetch(apiUrl(`/api/admin/dashboard/sales-chart?period=${chartPeriod}`), {
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          // Transform API data to chart format
          if (data.labels && data.data) {
            const chartPoints = data.labels.map((label: string, index: number) => ({
              date: label,
              orders: data.data[index]?.orders || 0,
              revenue: data.data[index]?.revenue || 0,
            }))
            setChartData(chartPoints)
          } else {
            // Generate sample data if API returns empty
            setChartData(generateSampleData(chartPeriod))
          }
        } else {
          // Use sample data on API error
          setChartData(generateSampleData(chartPeriod))
        }
      } catch (err) {
        console.error('Error fetching chart data:', err)
        // Use sample data on network error
        setChartData(generateSampleData(chartPeriod))
      } finally {
        setChartLoading(false)
      }
    }

    if (authToken) {
      fetchChartData()
    }
  }, [authToken, chartPeriod])

  // Generate sample data for the chart when no real data is available
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
    { name: 'Revenue', value: `₽${stats?.total_revenue ?? 0}`, icon: DollarSign, color: 'bg-yellow-500' },
    { name: 'Active Agents', value: stats?.active_agents ?? 0, icon: Activity, color: 'bg-purple-500' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsConfig.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                {loading ? (
                  <Loader2 className="h-6 w-6 text-gray-400 animate-spin mt-1" />
                ) : (
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Recent Orders */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Recent Orders</h2>
        {ordersLoading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="h-6 w-6 text-gray-400 animate-spin" />
          </div>
        ) : recentOrders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Order ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {recentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">#{order.id}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{order.user_name}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{order.agent_name}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        order.status === 'PAID' ? 'bg-green-100 text-green-800' :
                        order.status === 'CANCELLED' ? 'bg-red-100 text-red-800' :
                        order.status === 'PROCESSING' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">₽{order.total_sum.toLocaleString()}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {new Date(order.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
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

      {/* Sales Chart */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Sales Overview</h2>
          <div className="flex space-x-2">
            <button
              onClick={() => setChartPeriod('week')}
              className={`px-3 py-1 text-sm rounded ${
                chartPeriod === 'week'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Week
            </button>
            <button
              onClick={() => setChartPeriod('month')}
              className={`px-3 py-1 text-sm rounded ${
                chartPeriod === 'month'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Month
            </button>
            <button
              onClick={() => setChartPeriod('year')}
              className={`px-3 py-1 text-sm rounded ${
                chartPeriod === 'year'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Year
            </button>
          </div>
        </div>
        <div className="h-64">
          {chartLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 text-gray-400 animate-spin" />
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
                  label={{ value: 'Revenue (₽)', angle: 90, position: 'insideRight', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => [
                    name === 'revenue' ? `₽${value.toLocaleString()}` : value,
                    name === 'revenue' ? 'Revenue' : 'Orders'
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
            <div className="flex items-center justify-center h-full text-gray-500">
              No sales data available
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
