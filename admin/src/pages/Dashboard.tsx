import { Users, ShoppingCart, DollarSign, Activity } from 'lucide-react'

const stats = [
  { name: 'Total Users', value: '0', icon: Users, color: 'bg-blue-500' },
  { name: 'Total Orders', value: '0', icon: ShoppingCart, color: 'bg-green-500' },
  { name: 'Revenue', value: '₽0', icon: DollarSign, color: 'bg-yellow-500' },
  { name: 'Active Agents', value: '0', icon: Activity, color: 'bg-purple-500' },
]

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Orders */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Recent Orders</h2>
        <p className="text-gray-500">No orders yet.</p>
      </div>

      {/* Sales Chart */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Sales Overview</h2>
        <div className="h-64 flex items-center justify-center text-gray-500">
          Chart will be displayed here
        </div>
      </div>
    </div>
  )
}
