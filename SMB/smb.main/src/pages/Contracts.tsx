import {
  Shield,
  Link2,
  CheckCircle2,
  Clock,
  AlertCircle,
  Copy,
  ExternalLink,
  ArrowRight,
  Lock,
  FileCheck,
  Wallet,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useEffect, useState, useCallback } from 'react';
import {
  fetchBlockchainAnalytics,
  fetchEscrowContracts,
  fetchBlockchainTransactions,
} from '@/services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Analytics {
  totalContracts: number;
  activeContracts: number;
  completedContracts: number;
  pendingContracts: number;
  totalVolume: number;
  completionRate: number;
}

interface EscrowContract {
  escrow_id: string;
  buyer_wallet: string;
  seller_wallet: string;
  amount: number;
  status: string;
  initiator_wallet: string | null;
  deadline: string | null;
  blockchain_deal_id: string | null;
  blockchain_tx: string | null;
  created_at: string | null;
}

interface BlockchainTx {
  id: number;
  razorpay_payment_id: string | null;
  from_wallet: string;
  to_wallet: string;
  amount: number;
  metadata_hash: string | null;
  blockchain_tx: string | null;
  created_at: string | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SEPOLIA_TX_URL = 'https://sepolia.etherscan.io/tx/';

function truncateHash(hash: string | null, front = 6, back = 4): string {
  if (!hash) return '—';
  if (hash.length <= front + back + 3) return hash;
  return `${hash.slice(0, front)}...${hash.slice(-back)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => undefined);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, { label: string; classes: string; icon: React.ReactNode }> = {
    COMPLETED: {
      label: 'Completed',
      classes: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    LOCKED_ON_CHAIN: {
      label: 'Locked On-Chain',
      classes: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
      icon: <Lock className="w-3 h-3" />,
    },
    PENDING_PAYMENT: {
      label: 'Pending Payment',
      classes: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
      icon: <Clock className="w-3 h-3" />,
    },
  };
  const cfg = map[status] ?? {
    label: status,
    classes: 'bg-muted text-muted-foreground border-border',
    icon: <AlertCircle className="w-3 h-3" />,
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.classes}`}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  );
};

const WalletCell = ({ address }: { address: string | null }) => {
  const [copied, setCopied] = useState(false);
  if (!address) return <span className="text-muted-foreground">—</span>;
  const handle = () => {
    copyToClipboard(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={handle}
      title={address}
      className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-foreground transition-colors group"
    >
      <span>{truncateHash(address, 8, 6)}</span>
      <Copy className={`w-3 h-3 flex-shrink-0 ${copied ? 'text-emerald-400' : 'opacity-0 group-hover:opacity-100'} transition-opacity`} />
    </button>
  );
};

const TxLink = ({ hash }: { hash: string | null }) => {
  if (!hash) return <span className="text-muted-foreground text-xs">—</span>;
  return (
    <a
      href={`${SEPOLIA_TX_URL}${hash}`}
      target="_blank"
      rel="noopener noreferrer"
      title={hash}
      className="inline-flex items-center gap-1.5 font-mono text-xs text-blue-400 hover:text-blue-300 transition-colors"
    >
      {truncateHash(hash)}
      <ExternalLink className="w-3 h-3 flex-shrink-0" />
    </a>
  );
};

const StatCard = ({
  title,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  title: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent: string;
}) => (
  <div className="rounded-xl border border-border bg-card p-5 flex items-start gap-4 hover:shadow-lg transition-shadow">
    <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${accent}`}>
      <Icon className="w-5 h-5 text-white" />
    </div>
    <div className="min-w-0">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="text-2xl font-bold mt-0.5 truncate">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  </div>
);

// ─── Onboarding Gate ──────────────────────────────────────────────────────────

const OnboardingGate = () => (
  <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 animate-fade-in">
    {/* Hero icon */}
    <div className="relative">
      <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center shadow-2xl">
        <Shield className="w-12 h-12 text-white" />
      </div>
      <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-amber-400 flex items-center justify-center shadow-lg">
        <Lock className="w-4 h-4 text-amber-900" />
      </div>
    </div>

    {/* Copy */}
    <div className="text-center space-y-3 max-w-md">
      <h2 className="text-3xl font-bold">Smart Contracts & Blockchain</h2>
      <p className="text-muted-foreground text-base leading-relaxed">
        Your account hasn't been onboarded to the blockchain network yet. Enable blockchain to get
        immutable escrow contracts, on-chain payment proofs, and full audit traceability via the
        Sepolia testnet.
      </p>
    </div>

    {/* Feature pills */}
    <div className="flex flex-wrap justify-center gap-3">
      {[
        { icon: FileCheck, label: 'Escrow Contracts' },
        { icon: Link2, label: 'On-Chain Proofs' },
        { icon: Wallet, label: 'Custodial Wallets' },
        { icon: TrendingUp, label: 'Audit Trail' },
      ].map(({ icon: Icon, label }) => (
        <span
          key={label}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-muted/50 text-sm font-medium"
        >
          <Icon className="w-4 h-4 text-violet-500" />
          {label}
        </span>
      ))}
    </div>

    {/* CTA */}
    <Button
      size="lg"
      className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white px-8 py-3 rounded-xl shadow-lg transition-all hover:shadow-xl hover:scale-105"
      onClick={() => window.open('http://localhost:5173', '_blank')}
    >
      Onboard to Blockchain
      <ArrowRight className="w-5 h-5 ml-2" />
    </Button>

    <p className="text-xs text-muted-foreground">
      Powered by Sepolia Testnet · OpsHub Blockchain Network
    </p>
  </div>
);

// ─── Main Page ────────────────────────────────────────────────────────────────

type Tab = 'contracts' | 'transactions';

const Contracts = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [blockchainEnabled, setBlockchainEnabled] = useState<boolean | null>(null);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [contracts, setContracts] = useState<EscrowContract[]>([]);
  const [txns, setTxns] = useState<BlockchainTx[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('contracts');

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);

    try {
      const [analyticsRes, contractsRes, txnsRes] = await Promise.all([
        fetchBlockchainAnalytics(),
        fetchEscrowContracts(),
        fetchBlockchainTransactions(),
      ]);

      // All three endpoints agree on blockchain_enabled
      const enabled = analyticsRes?.blockchain_enabled === true;
      setBlockchainEnabled(enabled);

      if (enabled) {
        setWalletAddress(analyticsRes?.wallet_address ?? null);
        setAnalytics(analyticsRes?.data ?? null);
        setContracts(contractsRes?.data ?? []);
        setTxns(txnsRes?.data ?? []);
      }
    } catch (err) {
      console.error('Failed to load blockchain data:', err);
      setBlockchainEnabled(false);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Loading skeleton ─────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-8 w-48 bg-muted rounded-lg animate-pulse" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-muted rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-muted rounded-xl animate-pulse" />
      </div>
    );
  }

  // ── Not onboarded ────────────────────────────────────────────────────────
  if (!blockchainEnabled) {
    return <OnboardingGate />;
  }

  // ── Onboarded dashboard ──────────────────────────────────────────────────
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center shadow">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold">Smart Contracts</h1>
          </div>
          <p className="text-muted-foreground text-sm ml-12">
            Blockchain-backed escrow contracts &amp; payment proofs · Sepolia Testnet
          </p>
          {walletAddress && (
            <button
              onClick={() => copyToClipboard(walletAddress)}
              title={walletAddress}
              className="flex items-center gap-2 mt-2 ml-12 font-mono text-xs text-violet-400 hover:text-violet-300 transition-colors group"
            >
              <Wallet className="w-3.5 h-3.5" />
              <span>{truncateHash(walletAddress, 10, 8)}</span>
              <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          className="flex items-center gap-2 flex-shrink-0"
          onClick={() => loadData(true)}
          disabled={refreshing}
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats row */}
      {analytics && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Contracts"
            value={analytics.totalContracts}
            sub="All escrow deals"
            icon={FileCheck}
            accent="bg-gradient-to-br from-violet-600 to-violet-700"
          />
          <StatCard
            title="Active (On-Chain)"
            value={analytics.activeContracts}
            sub="Locked & awaiting completion"
            icon={Lock}
            accent="bg-gradient-to-br from-blue-600 to-blue-700"
          />
          <StatCard
            title="Completed"
            value={analytics.completedContracts}
            sub={`${analytics.completionRate}% completion rate`}
            icon={CheckCircle2}
            accent="bg-gradient-to-br from-emerald-600 to-emerald-700"
          />
          <StatCard
            title="Total Volume"
            value={formatAmount(analytics.totalVolume)}
            sub="Across all escrows"
            icon={TrendingUp}
            accent="bg-gradient-to-br from-amber-500 to-orange-600"
          />
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-1">
          {(
            [
              { key: 'contracts', label: `Escrow Contracts (${contracts.length})` },
              { key: 'transactions', label: `Payment Proofs (${txns.length})` },
            ] as { key: Tab; label: string }[]
          ).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === key
                  ? 'border-violet-500 text-violet-400'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab panels */}
      {activeTab === 'contracts' && (
        <ContractsTable contracts={contracts} />
      )}
      {activeTab === 'transactions' && (
        <TransactionsTable txns={txns} />
      )}
    </div>
  );
};

// ─── Escrow Contracts Table ───────────────────────────────────────────────────

const ContractsTable = ({ contracts }: { contracts: EscrowContract[] }) => {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (contracts.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center gap-3 text-center">
        <FileCheck className="w-10 h-10 text-muted-foreground" />
        <p className="font-medium">No Escrow Contracts Yet</p>
        <p className="text-sm text-muted-foreground max-w-sm">
          Escrow contracts will appear here once a deal is initiated via OpsHub.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {['Escrow ID', 'Counterparty', 'Direction', 'Amount', 'Status', 'Deadline', 'Created', ''].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {contracts.map((c) => (
              <>
                <tr
                  key={c.escrow_id}
                  className="hover:bg-muted/30 transition-colors cursor-pointer"
                  onClick={() => setExpanded(expanded === c.escrow_id ? null : c.escrow_id)}
                >
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {truncateHash(c.escrow_id, 8, 6)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-semibold text-foreground">
                        {c.counterparty_name || 'Unknown'}
                      </span>
                      <WalletCell address={c.counterparty_wallet || c.buyer_wallet} />
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      c.direction === 'inflow' 
                        ? 'bg-emerald-500/10 text-emerald-500' 
                        : 'bg-rose-500/10 text-rose-500'
                    }`}>
                      {c.direction === 'inflow' ? 'Inflow' : 'Outflow'}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-semibold whitespace-nowrap">
                    {formatAmount(c.amount)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(c.deadline)}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(c.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-xs text-violet-400">
                      {expanded === c.escrow_id ? '▲' : '▼'}
                    </span>
                  </td>
                </tr>
                {expanded === c.escrow_id && (
                  <tr key={`${c.escrow_id}-detail`} className="bg-muted/20">
                    <td colSpan={8} className="px-6 py-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="space-y-2">
                          <p className="text-muted-foreground font-semibold uppercase tracking-wide">
                            Full Escrow ID
                          </p>
                          <button
                            onClick={() => copyToClipboard(c.escrow_id)}
                            className="font-mono text-foreground hover:text-violet-400 transition-colors break-all text-left"
                          >
                            {c.escrow_id}
                          </button>
                        </div>
                        {c.blockchain_deal_id && (
                          <div className="space-y-2">
                            <p className="text-muted-foreground font-semibold uppercase tracking-wide">
                              Blockchain Deal ID
                            </p>
                            <p className="font-mono text-foreground">{c.blockchain_deal_id}</p>
                          </div>
                        )}
                        {c.blockchain_tx && (
                          <div className="space-y-2">
                            <p className="text-muted-foreground font-semibold uppercase tracking-wide">
                              Blockchain TX
                            </p>
                            <TxLink hash={c.blockchain_tx} />
                          </div>
                        )}
                        {c.initiator_wallet && (
                          <div className="space-y-2">
                            <p className="text-muted-foreground font-semibold uppercase tracking-wide">
                              Initiator Wallet
                            </p>
                            <WalletCell address={c.initiator_wallet} />
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ─── Blockchain Transactions Table ────────────────────────────────────────────

const TransactionsTable = ({ txns }: { txns: BlockchainTx[] }) => {
  if (txns.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center gap-3 text-center">
        <Link2 className="w-10 h-10 text-muted-foreground" />
        <p className="font-medium">No Payment Proofs Yet</p>
        <p className="text-sm text-muted-foreground max-w-sm">
          Blockchain payment proofs will appear here after escrow payments are processed.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {[
                'Payment ID',
                'From Wallet',
                'To Wallet',
                'Amount',
                'Blockchain TX',
                'Metadata Hash',
                'Date',
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {txns.map((tx) => (
              <tr key={tx.id} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {tx.razorpay_payment_id
                    ? truncateHash(tx.razorpay_payment_id, 8, 4)
                    : <span className="italic">—</span>}
                </td>
                <td className="px-4 py-3">
                  <WalletCell address={tx.from_wallet} />
                </td>
                <td className="px-4 py-3">
                  <WalletCell address={tx.to_wallet} />
                </td>
                <td className="px-4 py-3 font-semibold whitespace-nowrap">
                  {formatAmount(tx.amount)}
                </td>
                <td className="px-4 py-3">
                  <TxLink hash={tx.blockchain_tx} />
                </td>
                <td className="px-4 py-3">
                  {tx.metadata_hash ? (
                    <button
                      onClick={() => copyToClipboard(tx.metadata_hash!)}
                      title={tx.metadata_hash}
                      className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-foreground transition-colors group"
                    >
                      {truncateHash(tx.metadata_hash, 6, 4)}
                      <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                  {formatDate(tx.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Footer badge */}
      <div className="px-4 py-3 border-t border-border bg-muted/20 flex items-center gap-2 text-xs text-muted-foreground">
        <Shield className="w-3.5 h-3.5 text-violet-400" />
        All hashes immutably recorded on Sepolia Testnet · Click TX links to verify on Etherscan
      </div>
    </div>
  );
};

export default Contracts;
