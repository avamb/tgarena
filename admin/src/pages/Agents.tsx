import { useState } from 'react'
import { Plus, Edit, Trash2, Copy, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'

interface Agent {
  id: number
  name: string
  fid: number
  zone: string
  is_active: boolean
  created_at: string
}

export default function Agents() {
  const [agents] = useState<Agent[]>([])
  const [showModal, setShowModal] = useState(false)

  const copyDeepLink = (fid: number) => {
    const link = `https://t.me/YourBotUsername?start=agent_${fid}`
    navigator.clipboard.writeText(link)
    toast.success('Deep link copied!')
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        <button
          onClick={() => setShowModal(true)}
          className="btn btn-primary"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Agent
        </button>
      </div>

      <div className="card overflow-hidden">
        {agents.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No agents yet</p>
            <button
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
            >
              <Plus className="h-5 w-5 mr-2" />
              Add Your First Agent
            </button>
          </div>
        ) : (
          <table className="table">
            <thead className="bg-gray-50">
              <tr>
                <th>Name</th>
                <th>FID</th>
                <th>Zone</th>
                <th>Status</th>
                <th>Deep Link</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td className="font-medium">{agent.name}</td>
                  <td className="font-mono">{agent.fid}</td>
                  <td>
                    <span className={`badge ${agent.zone === 'real' ? 'badge-success' : 'badge-warning'}`}>
                      {agent.zone}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${agent.is_active ? 'badge-success' : 'badge-danger'}`}>
                      {agent.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => copyDeepLink(agent.fid)}
                      className="text-primary-600 hover:text-primary-800 inline-flex items-center"
                    >
                      <Copy className="h-4 w-4 mr-1" />
                      Copy
                    </button>
                  </td>
                  <td>
                    <div className="flex space-x-2">
                      <button className="text-gray-600 hover:text-gray-800">
                        <Edit className="h-5 w-5" />
                      </button>
                      <button className="text-danger-600 hover:text-danger-800">
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add/Edit Modal (placeholder) */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Add Agent</h2>
            <p className="text-gray-500 mb-4">Agent form will be implemented here.</p>
            <div className="flex justify-end">
              <button
                onClick={() => setShowModal(false)}
                className="btn btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
