import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpCircle,
  Ban,
  Calculator,
  Copy,
  CreditCard,
  DollarSign,
  Edit,
  ExternalLink,
  FileText,
  Loader2,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShoppingCart,
  Users,
  Wallet,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'
import { apiUrl } from '../api'

interface Agent {
  id: number
  name: string
  fid: number
  zone: string
  is_active: boolean
  payment_type: string
  agent_operational_status: string
  stripe_account_id?: string | null
  stripe_account_status?: string | null
  stripe_charges_enabled: boolean
  stripe_payouts_enabled: boolean
  created_at: string
  deep_link: string
}

interface AgentStats {
  users: number
  orders: number
  revenue: number
  revenue_by_currency: CurrencyBreakdown[]
}

interface CurrencyBreakdown {
  currency: string
  amount: number
}

interface StripeAccountState {
  agent_id: number
  payment_type: string
  stripe_account_id?: string | null
  stripe_account_status?: string | null
  stripe_charges_enabled: boolean
  stripe_payouts_enabled: boolean
}

interface AgentWallet {
  id: number
  agent_id: number
  currency: string
  reserve_balance_minor: number
  credit_limit_minor: number
  negative_exposure_minor: number
  warning_threshold_minor: number
  block_threshold_minor: number
  status: string
  remaining_risk_capacity_minor: number
  top_up_required_minor: number
  last_warning_at?: string | null
  last_blocked_at?: string | null
  created_at: string
  updated_at: string
}

interface AgentWalletListResponse {
  agent_id: number
  agent_operational_status: string
  wallets: AgentWallet[]
}

interface AgentRiskPolicy {
  agent_id: number
  allow_negative_balance: boolean
  auto_block_enabled: boolean
  refund_window_days: number
  refund_event_warning_count: number
  refund_event_block_count: number
  rolling_reserve_percent_bps: number
  min_reserve_balance_minor: number
  manual_override_status?: string | null
  current_refund_event_count: number
  created_at: string
  updated_at: string
}

interface AgentLedgerEntry {
  id: number
  wallet_id: number
  order_id?: number | null
  refund_case_id?: number | null
  currency: string
  amount_minor: number
  direction: string
  entry_type: string
  source: string
  source_id?: string | null
  description?: string | null
  metadata_json: Record<string, unknown>
  created_at: string
}

interface AgentLedgerResponse {
  agent_id: number
  entries: AgentLedgerEntry[]
}

interface AgentRiskIncident {
  id: number
  incident_type: string
  status: string
  currency: string
  amount_minor: number
  order_id?: number | null
  refund_case_id?: number | null
  reason?: string | null
  created_at: string
}

interface AgentRiskIncidentListResponse {
  agent_id: number
  refund_event_count: number
  incidents: AgentRiskIncident[]
}

interface RefundCalculation {
  order_id: number
  agent_id: number
  currency: string
  customer_refund_amount_minor: number
  ticket_refund_amount_minor: number
  service_fee_refund_amount_minor: number
  platform_cost_amount_minor: number
  agent_debit_amount_minor: number
  post_refund_status: string
  top_up_required_minor: number
}

interface RefundCaseResponse {
  id: number
  order_id: number
  agent_id: number
  currency: string
  customer_refund_amount_minor: number
  ticket_refund_amount_minor: number
  service_fee_refund_amount_minor: number
  platform_cost_amount_minor: number
  agent_debit_amount_minor: number
  stripe_refund_id?: string | null
  status: string
  policy_applied?: string | null
  reason?: string | null
  created_at: string
  completed_at?: string | null
}

interface RefundExecuteResponse {
  refund_case: RefundCaseResponse
  stripe_refund_status?: string | null
}

const defaultPolicy: AgentRiskPolicy = {
  agent_id: 0,
  allow_negative_balance: true,
  auto_block_enabled: true,
  refund_window_days: 30,
  refund_event_warning_count: 3,
  refund_event_block_count: 7,
  rolling_reserve_percent_bps: 0,
  min_reserve_balance_minor: 0,
  manual_override_status: null,
  current_refund_event_count: 0,
  created_at: '',
  updated_at: '',
}

export default function AgentDetails() {
  const { id } = useParams<{ id: string }>()
  const authToken = useAuthStore((state) => state.token)

  const [agent, setAgent] = useState<Agent | null>(null)
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [wallets, setWallets] = useState<AgentWallet[]>([])
  const [riskPolicy, setRiskPolicy] = useState<AgentRiskPolicy>(defaultPolicy)
  const [ledgerEntries, setLedgerEntries] = useState<AgentLedgerEntry[]>([])
  const [incidents, setIncidents] = useState<AgentRiskIncident[]>([])
  const [refundPreview, setRefundPreview] = useState<RefundCalculation | null>(null)

  const [walletsLoading, setWalletsLoading] = useState(false)
  const [operationsLoading, setOperationsLoading] = useState(false)
  const [policySaving, setPolicySaving] = useState(false)
  const [stripeLoading, setStripeLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [refundLoading, setRefundLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [topUpCurrency, setTopUpCurrency] = useState('USD')
  const [topUpAmount, setTopUpAmount] = useState('')
  const [topUpDescription, setTopUpDescription] = useState('')
  const [refundOrderId, setRefundOrderId] = useState('')
  const [refundMode, setRefundMode] = useState('full_refund')
  const [refundAmount, setRefundAmount] = useState('')
  const [refundReason, setRefundReason] = useState('')

  useEffect(() => {
    if (!id) {
      return
    }

    void loadPage()
  }, [id])

  useEffect(() => {
    if (wallets.length > 0) {
      setTopUpCurrency((current) => current || wallets[0].currency)
    }
  }, [wallets])

  const formatCurrency = (amount: number, currency: string) => {
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
      }).format(amount)
    } catch {
      return `${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
  }

  const formatMinor = (amountMinor: number, currency: string) => formatCurrency(amountMinor / 100, currency)

  const getOperationalBadgeClass = (status: string) => {
    switch (status) {
      case 'blocked':
      case 'force_blocked':
        return 'badge-danger'
      case 'warning':
      case 'restricted':
        return 'badge-warning'
      default:
        return 'badge-success'
    }
  }

  const getWalletBadgeClass = (status: string) => {
    switch (status) {
      case 'blocked':
        return 'badge-danger'
      case 'warning':
      case 'restricted':
        return 'badge-warning'
      default:
        return 'badge-success'
    }
  }

  const applyStripeState = (stripeState: StripeAccountState) => {
    setAgent((current) =>
      current
        ? {
            ...current,
            payment_type: stripeState.payment_type,
            stripe_account_id: stripeState.stripe_account_id,
            stripe_account_status: stripeState.stripe_account_status,
            stripe_charges_enabled: stripeState.stripe_charges_enabled,
            stripe_payouts_enabled: stripeState.stripe_payouts_enabled,
          }
        : current,
    )
  }

  const parseMinorInput = (value: string) => {
    const normalized = value.replace(',', '.').trim()
    if (!normalized) {
      return null
    }
    const parsed = Number.parseFloat(normalized)
    if (Number.isNaN(parsed) || parsed <= 0) {
      return null
    }
    return Math.round(parsed * 100)
  }

  const loadPage = async () => {
    setLoading(true)
    setError(null)
    try {
      await Promise.all([
        fetchAgent(true),
        fetchStats(),
        fetchWallets(),
        fetchRiskPolicy(),
        fetchLedgerAndIncidents(),
      ])
    } catch (loadError) {
      console.error('Failed to load agent page:', loadError)
      setError('Failed to load agent details')
    } finally {
      setLoading(false)
    }
  }

  const fetchAgent = async (isInitial = false) => {
    if (isInitial) {
      setError(null)
    }
    const response = await fetch(apiUrl(`/api/admin/agents/${id}`), {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    })

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Agent not found')
      }
      throw new Error('Failed to load agent')
    }

    const data = await response.json()
    setAgent(data)
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/stats`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (fetchError) {
      console.error('Failed to fetch agent stats:', fetchError)
    }
  }

  const fetchWallets = async () => {
    setWalletsLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/wallets`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data: AgentWalletListResponse = await response.json()
        setWallets(data.wallets || [])
      }
    } catch (fetchError) {
      console.error('Failed to fetch wallets:', fetchError)
    } finally {
      setWalletsLoading(false)
    }
  }

  const fetchRiskPolicy = async () => {
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/risk-policy`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })
      if (response.ok) {
        const data: AgentRiskPolicy = await response.json()
        setRiskPolicy(data)
      }
    } catch (fetchError) {
      console.error('Failed to fetch risk policy:', fetchError)
    }
  }

  const fetchLedgerAndIncidents = async () => {
    setOperationsLoading(true)
    try {
      const [ledgerResponse, incidentsResponse] = await Promise.all([
        fetch(apiUrl(`/api/admin/agents/${id}/ledger?limit=20`), {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        }),
        fetch(apiUrl(`/api/admin/agents/${id}/risk-incidents?limit=20`), {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        }),
      ])

      if (ledgerResponse.ok) {
        const ledgerPayload: AgentLedgerResponse = await ledgerResponse.json()
        setLedgerEntries(ledgerPayload.entries || [])
      }

      if (incidentsResponse.ok) {
        const incidentsPayload: AgentRiskIncidentListResponse = await incidentsResponse.json()
        setIncidents(incidentsPayload.incidents || [])
      }
    } catch (fetchError) {
      console.error('Failed to fetch operations data:', fetchError)
    } finally {
      setOperationsLoading(false)
    }
  }

  const refreshOperations = async () => {
    await Promise.all([fetchAgent(), fetchWallets(), fetchRiskPolicy(), fetchLedgerAndIncidents()])
  }

  const createOrRefreshStripe = async () => {
    if (!agent) return

    setStripeLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${agent.id}/stripe/account`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Failed to update Stripe account')
      }

      const stripeState: StripeAccountState = await response.json()
      applyStripeState(stripeState)
      toast.success(agent.stripe_account_id ? 'Stripe status refreshed' : 'Stripe account created')
    } catch (actionError) {
      console.error('Failed to update Stripe account:', actionError)
      toast.error(actionError instanceof Error ? actionError.message : 'Failed to update Stripe account')
    } finally {
      setStripeLoading(false)
    }
  }

  const openStripeOnboarding = async () => {
    if (!agent?.stripe_account_id) return

    setStripeLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${agent.id}/stripe/onboarding-link`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({}),
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Failed to create onboarding link')
      }

      const payload = await response.json()
      applyStripeState(payload)
      window.open(payload.onboarding_url, '_blank', 'noopener,noreferrer')
    } catch (actionError) {
      console.error('Failed to open Stripe onboarding:', actionError)
      toast.error(actionError instanceof Error ? actionError.message : 'Failed to create onboarding link')
    } finally {
      setStripeLoading(false)
    }
  }

  const copyDeepLink = () => {
    if (agent?.deep_link) {
      navigator.clipboard.writeText(agent.deep_link)
      toast.success('Deep link copied')
    }
  }

  const saveRiskPolicy = async () => {
    setPolicySaving(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/risk-policy`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          allow_negative_balance: riskPolicy.allow_negative_balance,
          auto_block_enabled: riskPolicy.auto_block_enabled,
          refund_window_days: riskPolicy.refund_window_days,
          refund_event_warning_count: riskPolicy.refund_event_warning_count,
          refund_event_block_count: riskPolicy.refund_event_block_count,
          rolling_reserve_percent_bps: riskPolicy.rolling_reserve_percent_bps,
          min_reserve_balance_minor: riskPolicy.min_reserve_balance_minor,
        }),
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Failed to save risk policy')
      }

      const data: AgentRiskPolicy = await response.json()
      setRiskPolicy(data)
      toast.success('Risk policy updated')
      await refreshOperations()
    } catch (actionError) {
      console.error('Failed to save risk policy:', actionError)
      toast.error(actionError instanceof Error ? actionError.message : 'Failed to save risk policy')
    } finally {
      setPolicySaving(false)
    }
  }

  const submitTopUp = async () => {
    const amountMinor = parseMinorInput(topUpAmount)
    if (!amountMinor) {
      toast.error('Enter a valid top-up amount')
      return
    }

    setActionLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/topup`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          currency: topUpCurrency,
          amount_minor: amountMinor,
          description: topUpDescription || undefined,
        }),
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Failed to top up wallet')
      }

      setTopUpAmount('')
      setTopUpDescription('')
      toast.success('Top-up recorded')
      await refreshOperations()
    } catch (actionError) {
      console.error('Failed to top up wallet:', actionError)
      toast.error(actionError instanceof Error ? actionError.message : 'Failed to top up wallet')
    } finally {
      setActionLoading(false)
    }
  }

  const updateAgentOverride = async (path: 'block' | 'unblock') => {
    setActionLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/agents/${id}/${path}`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || `Failed to ${path} agent`)
      }

      toast.success(path === 'block' ? 'Agent force-blocked' : 'Agent unblocked')
      await refreshOperations()
    } catch (actionError) {
      console.error(`Failed to ${path} agent:`, actionError)
      toast.error(actionError instanceof Error ? actionError.message : `Failed to ${path} agent`)
    } finally {
      setActionLoading(false)
    }
  }

  const calculateRefund = async () => {
    if (!refundOrderId.trim()) {
      toast.error('Enter an order ID')
      return
    }

    const amountMinor = refundMode === 'custom_partial_refund' ? parseMinorInput(refundAmount) : null
    if (refundMode === 'custom_partial_refund' && !amountMinor) {
      toast.error('Enter a valid partial refund amount')
      return
    }

    setRefundLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/orders/${refundOrderId}/refund/calculate`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          mode: refundMode,
          amount_minor: amountMinor ?? undefined,
          reason: refundReason || undefined,
        }),
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Failed to calculate refund')
      }

      const data: RefundCalculation = await response.json()
      setRefundPreview(data)
      toast.success('Refund calculation ready')
    } catch (actionError) {
      console.error('Failed to calculate refund:', actionError)
      toast.error(actionError instanceof Error ? actionError.message : 'Failed to calculate refund')
    } finally {
      setRefundLoading(false)
    }
  }

  const executeRefund = async () => {
    if (!refundOrderId.trim()) {
      toast.error('Enter an order ID')
      return
    }

    const amountMinor = refundMode === 'custom_partial_refund' ? parseMinorInput(refundAmount) : null
    if (refundMode === 'custom_partial_refund' && !amountMinor) {
      toast.error('Enter a valid partial refund amount')
      return
    }

    setRefundLoading(true)
    try {
      const response = await fetch(apiUrl(`/api/admin/orders/${refundOrderId}/refund/execute`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          mode: refundMode,
          amount_minor: amountMinor ?? undefined,
          reason: refundReason || undefined,
          reverse_transfer: true,
          refund_application_fee: false,
        }),
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Failed to execute refund')
      }

      const data: RefundExecuteResponse = await response.json()
      toast.success(`Refund submitted (${data.stripe_refund_status || 'processing'})`)
      await refreshOperations()
      setRefundPreview(null)
    } catch (actionError) {
      console.error('Failed to execute refund:', actionError)
      toast.error(actionError instanceof Error ? actionError.message : 'Failed to execute refund')
    } finally {
      setRefundLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <span className="ml-2 text-gray-500">Loading agent details...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/agents" className="inline-flex items-center text-primary-600 hover:text-primary-800">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agents
        </Link>
        <div className="card">
          <div className="flex h-64 items-center justify-center">
            <AlertCircle className="mr-3 h-8 w-8 text-red-500" />
            <span className="text-gray-700">{error}</span>
          </div>
        </div>
      </div>
    )
  }

  if (!agent) {
    return null
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/agents" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{agent.name}</h1>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className={`badge ${agent.is_active ? getOperationalBadgeClass(agent.agent_operational_status) : 'badge-danger'}`}>
                {agent.is_active ? agent.agent_operational_status : 'inactive'}
              </span>
              {riskPolicy.manual_override_status && (
                <span className="badge badge-warning">override: {riskPolicy.manual_override_status}</span>
              )}
            </div>
          </div>
        </div>
        <Link to="/agents" className="btn btn-secondary">
          <Edit className="mr-2 h-4 w-4" />
          Edit
        </Link>
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold">Agent Information</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-500">ID</label>
            <p className="mt-1 font-mono text-sm text-gray-900">{agent.id}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Bill24 FID</label>
            <p className="mt-1 font-mono text-sm text-gray-900">{agent.fid}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Zone</label>
            <p className="mt-1">
              <span className={`badge ${agent.zone === 'real' ? 'badge-success' : 'badge-warning'}`}>{agent.zone}</span>
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Payment Type</label>
            <p className="mt-1">
              <span className={`badge ${agent.payment_type === 'stripe_connect' ? 'badge-success' : 'badge-info'}`}>{agent.payment_type}</span>
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500">Created</label>
            <p className="mt-1 text-sm text-gray-900">
              {new Date(agent.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-500">Deep Link</label>
            <div className="mt-1 flex items-center space-x-2">
              <code className="flex-1 overflow-hidden text-ellipsis rounded bg-gray-100 px-3 py-1 text-sm">{agent.deep_link}</code>
              <button onClick={copyDeepLink} className="btn btn-secondary text-sm">
                <Copy className="mr-1 h-4 w-4" />
                Copy
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Stripe Connect</h2>
            <p className="text-sm text-gray-500">Connected account state, capabilities, and onboarding actions.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={createOrRefreshStripe} className="btn btn-secondary" disabled={stripeLoading}>
              {stripeLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : agent.stripe_account_id ? (
                <RefreshCw className="mr-2 h-4 w-4" />
              ) : (
                <CreditCard className="mr-2 h-4 w-4" />
              )}
              {agent.stripe_account_id ? 'Refresh Status' : 'Create Account'}
            </button>
            {agent.stripe_account_id && !(agent.stripe_charges_enabled && agent.stripe_payouts_enabled) && (
              <button onClick={openStripeOnboarding} className="btn btn-primary" disabled={stripeLoading}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Continue Onboarding
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-500">Account</p>
            <p className="mt-2 font-mono text-sm text-gray-900">{agent.stripe_account_id || 'Not created'}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-500">Stripe Status</p>
            <p className="mt-2 text-sm font-semibold capitalize text-gray-900">{agent.stripe_account_status || 'not_connected'}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-500">Charges</p>
            <p className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-sm font-medium ${agent.stripe_charges_enabled ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
              {agent.stripe_charges_enabled ? 'Enabled' : 'Not ready'}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-500">Payouts</p>
            <p className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-sm font-medium ${agent.stripe_payouts_enabled ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
              {agent.stripe_payouts_enabled ? 'Enabled' : 'Not ready'}
            </p>
          </div>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="card border-blue-200 bg-blue-50">
            <div className="flex items-center">
              <Users className="h-10 w-10 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-blue-600">Total Users</p>
                <p className="text-2xl font-bold text-blue-900">{stats.users}</p>
              </div>
            </div>
          </div>
          <div className="card border-green-200 bg-green-50">
            <div className="flex items-center">
              <ShoppingCart className="h-10 w-10 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-green-600">Total Orders</p>
                <p className="text-2xl font-bold text-green-900">{stats.orders}</p>
              </div>
            </div>
          </div>
          <div className="card border-purple-200 bg-purple-50">
            <div className="flex items-center">
              <DollarSign className="h-10 w-10 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-purple-600">Revenue</p>
                <div className="text-2xl font-bold text-purple-900">
                  {stats.revenue_by_currency?.length ? (
                    stats.revenue_by_currency.map((item) => <p key={item.currency}>{formatCurrency(item.amount, item.currency)}</p>)
                  ) : (
                    <p>0</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Risk Wallets</h2>
            <p className="text-sm text-gray-500">Reserve, exposure, capacity, and top-up need per currency.</p>
          </div>
          <button onClick={fetchWallets} className="btn btn-secondary text-sm" disabled={walletsLoading}>
            {walletsLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Refresh
          </button>
        </div>

        {walletsLoading ? (
          <div className="flex items-center justify-center py-10 text-gray-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading wallets...
          </div>
        ) : wallets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-sm text-gray-500">
            Wallets will appear after settlement ledger activity starts for this agent.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {wallets.map((wallet) => (
              <div key={wallet.id} className="rounded-xl border border-gray-200 p-5">
                <div className="mb-4 flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-gray-100 p-2 text-gray-700">
                      <Wallet className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-gray-900">{wallet.currency}</p>
                      <p className="text-sm text-gray-500">Wallet #{wallet.id}</p>
                    </div>
                  </div>
                  <span className={`badge ${getWalletBadgeClass(wallet.status)}`}>{wallet.status}</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-emerald-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">Reserve</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-900">{formatMinor(wallet.reserve_balance_minor, wallet.currency)}</p>
                  </div>
                  <div className="rounded-lg bg-rose-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-rose-700">Exposure</p>
                    <p className="mt-1 text-sm font-semibold text-rose-900">{formatMinor(wallet.negative_exposure_minor, wallet.currency)}</p>
                  </div>
                  <div className="rounded-lg bg-blue-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Capacity</p>
                    <p className="mt-1 text-sm font-semibold text-blue-900">{formatMinor(wallet.remaining_risk_capacity_minor, wallet.currency)}</p>
                  </div>
                  <div className="rounded-lg bg-amber-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-amber-700">Top-Up Required</p>
                    <p className="mt-1 text-sm font-semibold text-amber-900">{formatMinor(wallet.top_up_required_minor, wallet.currency)}</p>
                  </div>
                </div>

                <div className="mt-4 flex items-start gap-2 rounded-lg bg-gray-50 p-3 text-sm text-gray-600">
                  <ShieldAlert className="mt-0.5 h-4 w-4 flex-none text-gray-400" />
                  <div>
                    Warning threshold: {formatMinor(wallet.warning_threshold_minor, wallet.currency)}. Block threshold: {formatMinor(wallet.block_threshold_minor, wallet.currency)}.
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card space-y-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-2 text-amber-700">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Risk Policy</h2>
              <p className="text-sm text-gray-500">Per-agent thresholds and policy switches.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">Allow negative balance</span>
              <input
                type="checkbox"
                checked={riskPolicy.allow_negative_balance}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, allow_negative_balance: e.target.checked }))}
              />
            </label>
            <label className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">Auto-block enabled</span>
              <input
                type="checkbox"
                checked={riskPolicy.auto_block_enabled}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, auto_block_enabled: e.target.checked }))}
              />
            </label>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Refund window (days)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={riskPolicy.refund_window_days}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, refund_window_days: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Refund events currently counted</label>
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700">
                {riskPolicy.current_refund_event_count}
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Warning count</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={riskPolicy.refund_event_warning_count}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, refund_event_warning_count: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Block count</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={riskPolicy.refund_event_block_count}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, refund_event_block_count: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Rolling reserve (bps)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={riskPolicy.rolling_reserve_percent_bps}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, rolling_reserve_percent_bps: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Min reserve balance (minor)</label>
              <input
                type="number"
                min={0}
                className="w-full"
                value={riskPolicy.min_reserve_balance_minor}
                onChange={(e) => setRiskPolicy((prev) => ({ ...prev, min_reserve_balance_minor: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
          </div>

          <button onClick={saveRiskPolicy} className="btn btn-primary" disabled={policySaving}>
            {policySaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Shield className="mr-2 h-4 w-4" />}
            Save Risk Policy
          </button>
        </div>

        <div className="card space-y-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
              <ArrowUpCircle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Admin Operations</h2>
              <p className="text-sm text-gray-500">Top up, force block, or release the agent after review.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Currency</label>
              <select className="w-full" value={topUpCurrency} onChange={(e) => setTopUpCurrency(e.target.value)}>
                {[...new Set(wallets.map((wallet) => wallet.currency).concat(topUpCurrency || 'USD'))].map((currency) => (
                  <option key={currency} value={currency}>
                    {currency}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Top-up amount</label>
              <input
                type="number"
                min={0}
                step="0.01"
                className="w-full"
                placeholder="100.00"
                value={topUpAmount}
                onChange={(e) => setTopUpAmount(e.target.value)}
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-gray-700">Description</label>
              <input
                type="text"
                className="w-full"
                placeholder="Admin recovery top-up"
                value={topUpDescription}
                onChange={(e) => setTopUpDescription(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button onClick={submitTopUp} className="btn btn-primary" disabled={actionLoading}>
              {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowUpCircle className="mr-2 h-4 w-4" />}
              Record Top-Up
            </button>
            <button onClick={() => updateAgentOverride('block')} className="btn btn-secondary" disabled={actionLoading}>
              <Ban className="mr-2 h-4 w-4" />
              Force Block
            </button>
            <button onClick={() => updateAgentOverride('unblock')} className="btn btn-secondary" disabled={actionLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Unblock
            </button>
          </div>
        </div>
      </div>

      <div className="card space-y-5">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-rose-100 p-2 text-rose-700">
            <Calculator className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Refund Operations</h2>
            <p className="text-sm text-gray-500">Calculate and submit admin refunds through existing backend endpoints.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Order ID</label>
            <input className="w-full" type="number" min={1} value={refundOrderId} onChange={(e) => setRefundOrderId(e.target.value)} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Mode</label>
            <select className="w-full" value={refundMode} onChange={(e) => setRefundMode(e.target.value)}>
              <option value="full_refund">Full refund</option>
              <option value="ticket_only_refund">Ticket only</option>
              <option value="custom_partial_refund">Custom partial</option>
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Partial amount</label>
            <input
              className="w-full"
              type="number"
              min={0}
              step="0.01"
              placeholder="25.00"
              disabled={refundMode !== 'custom_partial_refund'}
              value={refundAmount}
              onChange={(e) => setRefundAmount(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Reason</label>
            <input className="w-full" type="text" placeholder="customer_request" value={refundReason} onChange={(e) => setRefundReason(e.target.value)} />
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button onClick={calculateRefund} className="btn btn-secondary" disabled={refundLoading}>
            {refundLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Calculator className="mr-2 h-4 w-4" />}
            Calculate
          </button>
          <button onClick={executeRefund} className="btn btn-primary" disabled={refundLoading}>
            <FileText className="mr-2 h-4 w-4" />
            Execute Refund
          </button>
        </div>

        {refundPreview && (
          <div className="grid grid-cols-1 gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4 md:grid-cols-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Customer refund</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">{formatMinor(refundPreview.customer_refund_amount_minor, refundPreview.currency)}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Agent debit</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">{formatMinor(refundPreview.agent_debit_amount_minor, refundPreview.currency)}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Top-up required</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">{formatMinor(refundPreview.top_up_required_minor, refundPreview.currency)}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Ticket refund</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">{formatMinor(refundPreview.ticket_refund_amount_minor, refundPreview.currency)}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Service fee refund</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">{formatMinor(refundPreview.service_fee_refund_amount_minor, refundPreview.currency)}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Post-refund status</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">{refundPreview.post_refund_status}</p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Ledger</h2>
              <p className="text-sm text-gray-500">Most recent ledger activity for this agent.</p>
            </div>
            <button onClick={fetchLedgerAndIncidents} className="btn btn-secondary text-sm" disabled={operationsLoading}>
              {operationsLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="table">
              <thead className="bg-gray-50">
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Direction</th>
                  <th>Amount</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {ledgerEntries.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-sm text-gray-500">
                      No ledger entries yet.
                    </td>
                  </tr>
                ) : (
                  ledgerEntries.map((entry) => (
                    <tr key={entry.id}>
                      <td className="text-sm text-gray-600">{new Date(entry.created_at).toLocaleString()}</td>
                      <td className="text-sm font-medium text-gray-900">{entry.entry_type}</td>
                      <td className="text-sm text-gray-600">{entry.direction}</td>
                      <td className="text-sm text-gray-900">{formatMinor(entry.amount_minor, entry.currency)}</td>
                      <td className="text-sm text-gray-600">{entry.description || entry.source}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Risk Incidents</h2>
              <p className="text-sm text-gray-500">Refund-driven incidents currently visible to the risk engine.</p>
            </div>
            <span className="badge badge-warning">{riskPolicy.current_refund_event_count} events</span>
          </div>

          <div className="space-y-3">
            {incidents.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-sm text-gray-500">
                No incidents recorded for this agent.
              </div>
            ) : (
              incidents.map((incident) => (
                <div key={incident.id} className="rounded-xl border border-gray-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-gray-900">
                        {incident.incident_type} #{incident.id}
                      </p>
                      <p className="mt-1 text-sm text-gray-500">
                        Order #{incident.order_id || 'n/a'} • {new Date(incident.created_at).toLocaleString()}
                      </p>
                      {incident.reason && <p className="mt-2 text-sm text-gray-600">{incident.reason}</p>}
                    </div>
                    <div className="text-right">
                      <span className={`badge ${getOperationalBadgeClass(incident.status)}`}>{incident.status}</span>
                      <p className="mt-2 text-sm font-semibold text-gray-900">{formatMinor(incident.amount_minor, incident.currency)}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
