import { Routes, Route, Navigate } from 'react-router-dom'
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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="agents" element={<Agents />} />
        <Route path="agents/:id" element={<AgentDetails />} />
        <Route path="users" element={<Users />} />
        <Route path="users/:id" element={<UserDetails />} />
        <Route path="orders" element={<Orders />} />
        <Route path="webhooks" element={<Webhooks />} />
        <Route path="settings" element={<Settings />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default App
