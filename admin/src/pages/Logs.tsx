/* Logs page - application log viewer */
import { useState, useEffect, useRef, useCallback } from 'react'
import { RefreshCw, Search, Filter, Download, Pause, Play } from 'lucide-react'
import { useAuthStore } from '../store/auth'
import { apiUrl } from '../api'

interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
  module?: string
  function?: string
  line?: number
  component?: string
  exception?: string
}

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'text-gray-500 bg-gray-100',
  INFO: 'text-blue-700 bg-blue-100',
  WARNING: 'text-amber-700 bg-amber-100',
  ERROR: 'text-red-700 bg-red-100',
  CRITICAL: 'text-white bg-red-600',
}

const COMPONENT_COLORS: Record<string, string> = {
  bot: 'text-purple-700 bg-purple-100',
  api: 'text-green-700 bg-green-100',
  bill24: 'text-orange-700 bg-orange-100',
  system: 'text-gray-700 bg-gray-100',
}

export default function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [lines, setLines] = useState(200)
  const [levelFilter, setLevelFilter] = useState('')
  const [componentFilter, setComponentFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const token = useAuthStore((state) => state.token)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<number | null>(null)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('lines', String(lines))
      if (levelFilter) params.set('level', levelFilter)
      if (componentFilter) params.set('component', componentFilter)
      if (searchQuery) params.set('search', searchQuery)

      const response = await fetch(apiUrl(`/api/admin/logs?${params}`), {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      setLoading(false)
    }
  }, [token, lines, levelFilter, componentFilter, searchQuery])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = window.setInterval(fetchLogs, 3000)
    } else if (intervalRef.current) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current)
    }
  }, [autoRefresh, fetchLogs])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(searchInput)
  }

  const handleDownload = () => {
    const text = logs
      .map(
        (log) =>
          `[${log.timestamp}] [${log.level}] [${log.component || 'system'}] ${log.logger}: ${log.message}${log.exception ? '\n' + log.exception : ''}`
      )
      .join('\n')

    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${new Date().toISOString().slice(0, 19)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts)
      return d.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }) + '.' + String(d.getMilliseconds()).padStart(3, '0')
    } catch {
      return ts
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Logs</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              autoRefresh
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title={autoRefresh ? 'Pause auto-refresh' : 'Start auto-refresh'}
          >
            {autoRefresh ? (
              <>
                <Pause className="h-4 w-4" /> Live
              </>
            ) : (
              <>
                <Play className="h-4 w-4" /> Paused
              </>
            )}
          </button>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="flex items-center gap-1 px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={handleDownload}
            disabled={logs.length === 0}
            className="flex items-center gap-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search logs..."
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </form>

          {/* Level filter */}
          <div className="flex items-center gap-1">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="border border-gray-300 rounded-lg text-sm py-2 px-2 focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Levels</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          {/* Component filter */}
          <select
            value={componentFilter}
            onChange={(e) => setComponentFilter(e.target.value)}
            className="border border-gray-300 rounded-lg text-sm py-2 px-2 focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Components</option>
            <option value="bot">Bot</option>
            <option value="api">API</option>
            <option value="bill24">Bill24</option>
            <option value="system">System</option>
          </select>

          {/* Lines */}
          <select
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
            className="border border-gray-300 rounded-lg text-sm py-2 px-2 focus:ring-2 focus:ring-primary-500"
          >
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
            <option value={1000}>1000 lines</option>
          </select>
        </div>
      </div>

      {/* Log entries */}
      <div className="bg-gray-900 rounded-lg shadow-sm overflow-hidden">
        <div className="p-2 text-xs text-gray-400 border-b border-gray-700 flex justify-between">
          <span>
            {logs.length} log entries
            {levelFilter && ` (level: ${levelFilter})`}
            {componentFilter && ` (component: ${componentFilter})`}
          </span>
          {autoRefresh && (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              Auto-refreshing every 3s
            </span>
          )}
        </div>
        <div
          className="overflow-auto font-mono text-xs leading-relaxed"
          style={{ maxHeight: 'calc(100vh - 340px)' }}
        >
          {logs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {loading ? 'Loading logs...' : 'No log entries found'}
            </div>
          ) : (
            <table className="w-full">
              <tbody>
                {logs.map((log, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-gray-800 border-b border-gray-800"
                  >
                    <td className="px-2 py-1 text-gray-500 whitespace-nowrap align-top">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-1 py-1 whitespace-nowrap align-top">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          LEVEL_COLORS[log.level] || 'text-gray-400 bg-gray-800'
                        }`}
                      >
                        {log.level}
                      </span>
                    </td>
                    <td className="px-1 py-1 whitespace-nowrap align-top">
                      {log.component && (
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            COMPONENT_COLORS[log.component] || 'text-gray-400 bg-gray-800'
                          }`}
                        >
                          {log.component}
                        </span>
                      )}
                    </td>
                    <td className="px-2 py-1 text-gray-300 align-top">
                      <div>
                        <span className="text-gray-500">{log.logger}: </span>
                        {log.message}
                      </div>
                      {log.exception && (
                        <pre className="mt-1 text-red-400 whitespace-pre-wrap break-all">
                          {log.exception}
                        </pre>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  )
}
