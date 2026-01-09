import { createBrowserRouter, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Users from './pages/Users'
import Orders from './pages/Orders'
import Webhooks from './pages/Webhooks'
import Settings from './pages/Settings'
import NotFound from './pages/NotFound'

// Components
import Layout from './components/Layout'

// Protected route wrapper component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'agents',
        element: <Agents />,
      },
      {
        path: 'users',
        element: <Users />,
      },
      {
        path: 'orders',
        element: <Orders />,
      },
      {
        path: 'webhooks',
        element: <Webhooks />,
      },
      {
        path: 'settings',
        element: <Settings />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFound />,
  },
])
