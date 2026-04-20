/* Layout with sidebar navigation - updated with Logs page */
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, Ticket, ShoppingCart, Webhook, Settings, ScrollText, LogOut, Menu, X, ChevronRight, Home } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/auth'
import { apiUrl } from '../api'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Agents', href: '/agents', icon: Ticket },
  { name: 'Users', href: '/users', icon: Users },
  { name: 'Orders', href: '/orders', icon: ShoppingCart },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Logs', href: '/logs', icon: ScrollText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

// Map route segments to display names
const routeNameMap: Record<string, string> = {
  dashboard: 'Dashboard',
  agents: 'Agents',
  users: 'Users',
  orders: 'Orders',
  webhooks: 'Webhooks',
  logs: 'Logs',
  settings: 'Settings',
}

interface BreadcrumbItem {
  name: string
  href: string
  isLast: boolean
}

function Breadcrumbs() {
  const location = useLocation()
  const [entityName, setEntityName] = useState<string | null>(null)
  const authToken = useAuthStore((state) => state.token)

  // Parse path segments
  const pathSegments = location.pathname.split('/').filter(Boolean)

  // Fetch entity name for detail pages (e.g., /agents/5 -> fetch agent name)
  useEffect(() => {
    const fetchEntityName = async () => {
      if (pathSegments.length >= 2) {
        const entityType = pathSegments[0] // 'agents' or 'users'
        const entityId = pathSegments[1]

        // Check if ID is numeric
        if (!isNaN(Number(entityId))) {
          try {
            const response = await fetch(apiUrl(`/api/admin/${entityType}/${entityId}`), {
              headers: {
                'Authorization': `Bearer ${authToken}`,
              },
            })
            if (response.ok) {
              const data = await response.json()
              // Set name based on entity type
              if (entityType === 'agents') {
                setEntityName(data.name)
              } else if (entityType === 'users') {
                setEntityName(data.telegram_username || data.telegram_first_name || `User ${entityId}`)
              }
            }
          } catch (err) {
            console.error('Failed to fetch entity name:', err)
            setEntityName(`#${entityId}`)
          }
        }
      } else {
        setEntityName(null)
      }
    }

    fetchEntityName()
  }, [location.pathname, authToken])

  // Build breadcrumb items
  const breadcrumbs: BreadcrumbItem[] = [
    { name: 'Dashboard', href: '/dashboard', isLast: pathSegments.length === 0 || (pathSegments.length === 1 && pathSegments[0] === 'dashboard') },
  ]

  let currentPath = ''
  pathSegments.forEach((segment, index) => {
    currentPath += `/${segment}`
    const isLast = index === pathSegments.length - 1

    // Skip 'dashboard' as it's already in breadcrumbs as home
    if (segment === 'dashboard' && index === 0) {
      breadcrumbs[0].isLast = isLast
      return
    }

    // Check if this is a numeric ID (detail page)
    if (!isNaN(Number(segment))) {
      breadcrumbs.push({
        name: entityName || `#${segment}`,
        href: currentPath,
        isLast,
      })
    } else {
      breadcrumbs.push({
        name: routeNameMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
        href: currentPath,
        isLast,
      })
    }
  })

  // Don't show breadcrumbs on dashboard (home) page alone
  if (breadcrumbs.length <= 1) {
    return null
  }

  return (
    <nav className="flex items-center space-x-1 text-sm" aria-label="Breadcrumb">
      {breadcrumbs.map((crumb, index) => (
        <div key={crumb.href} className="flex items-center">
          {index > 0 && (
            <ChevronRight className="h-4 w-4 text-gray-400 mx-1" />
          )}
          {crumb.isLast ? (
            <span className="text-gray-900 font-medium" aria-current="page">
              {crumb.name}
            </span>
          ) : (
            <Link
              to={crumb.href}
              className="text-gray-500 hover:text-primary-600 transition-colors"
            >
              {index === 0 ? (
                <span className="flex items-center">
                  <Home className="h-4 w-4" />
                  <span className="sr-only">{crumb.name}</span>
                </span>
              ) : (
                crumb.name
              )}
            </Link>
          )}
        </div>
      ))}
    </nav>
  )
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Skip to main content link for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:bg-primary-600 focus:text-white focus:px-4 focus:py-2 focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"
      >
        Skip to main content
      </a>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="h-16 flex items-center justify-between px-4 border-b">
            <span className="text-xl font-bold text-primary-600">TG-Ticket-Agent</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-600'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <item.icon className="h-5 w-5 mr-3" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User section */}
          <div className="p-4 border-t">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{user?.username}</p>
                <p className="text-xs text-gray-500">{user?.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                title="Logout"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="h-16 bg-white shadow-sm flex items-center px-4 lg:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="ml-4 lg:ml-0 flex-1">
            <Breadcrumbs />
            {/* Show simple title when no breadcrumbs (dashboard only) */}
            {location.pathname === '/dashboard' && (
              <h2 className="text-lg font-semibold text-gray-900">Dashboard</h2>
            )}
          </div>
        </header>

        {/* Page content */}
        <main id="main-content" className="p-4 lg:p-6" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
