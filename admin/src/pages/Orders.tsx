import { useState } from 'react'
import { Search, Filter, Download } from 'lucide-react'

export default function Orders() {
  const [search, setSearch] = useState('')

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
          <select className="min-w-[150px]">
            <option value="">All Statuses</option>
            <option value="NEW">New</option>
            <option value="PROCESSING">Processing</option>
            <option value="PAID">Paid</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
          <select className="min-w-[150px]">
            <option value="">All Agents</option>
          </select>
          <input type="date" className="min-w-[150px]" placeholder="From" />
          <input type="date" className="min-w-[150px]" placeholder="To" />
        </div>
      </div>

      {/* Orders Table */}
      <div className="card overflow-hidden">
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
      </div>
    </div>
  )
}
