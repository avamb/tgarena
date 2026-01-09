import { createBrowserRouter, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from './store/auth'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import AgentDetails from './pages/AgentDetails'
import Users from './pages/Users'
import UserDetails from './pages/UserDetails'
import Orders from './pages/Orders'
import Webhooks from './pages/Webhooks'
import Settings from './pages/Settings'
import NotFound from './pages/NotFound'

// Components
import Layout from './components/Layout'

// Protected route wrapper component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    // Save the intended destination so we can redirect after login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
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
        path: 'agents/:id',
        element: <AgentDetails />,
      },
      {
        path: 'users',
        element: <Users />,
      },
      {
        path: 'users/:id',
        element: <UserDetails />,
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
