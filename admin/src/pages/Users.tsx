import { useState } from 'react'
import { Search, Filter } from 'lucide-react'

export default function Users() {
  const [search, setSearch] = useState('')

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
          <select className="min-w-[150px]">
            <option value="">All Agents</option>
          </select>
          <button className="btn btn-secondary">
            <Filter className="h-5 w-5 mr-2" />
            More Filters
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="card overflow-hidden">
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
            <tr>
              <td colSpan={6} className="text-center py-8 text-gray-500">
                No users yet
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
