import { DollarSign, Package, FileText, TrendingUp, Wallet, Truck } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useEffect, useState } from 'react';
import { fetchDashboardStats, fetchMonthlyRevenue } from '@/services/api';

const Dashboard = () => {
  // Fetch dynamic data from simulated API
  const [stats, setStats] = useState<any>(null);
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [statsData, revenueData] = await Promise.all([
          fetchDashboardStats(),
          fetchMonthlyRevenue(6)
        ]);
        setStats(statsData || {});
        setRevenueData(revenueData || []);
      } catch (err) {
        console.error('Dashboard data loading error:', err);
        setError('Failed to load dashboard data');
        setStats(null);
        setRevenueData(null);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatChange = (value: number, suffix: string = '') => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%${suffix}`;
  };

  // Show loading state while data is being fetched
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    );
  }

  // Show error state if data loading failed
  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-lg text-red-600 mb-2">⚠️ {error}</div>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/80"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Use stats directly without defaults
  const safeStats = stats || {};

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Here's your business overview.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Total Revenue"
          value={formatCurrency(safeStats.totalRevenue || 0)}
          change={formatChange(safeStats.revenueChange || 0, ' from last month')}
          changeType={(safeStats.revenueChange || 0) >= 0 ? 'positive' : 'negative'}
          icon={DollarSign}
        />
        <StatCard
          title="Inventory Value"
          value={formatCurrency(safeStats.inventoryValue || 0)}
          change={formatChange(safeStats.inventoryChange || 0, ' from last month')}
          changeType={(safeStats.inventoryChange || 0) >= 0 ? 'positive' : 'negative'}
          icon={Package}
        />
        <StatCard
          title="Active Contracts"
          value={(safeStats.activeContracts || 0).toString()}
          change={`${safeStats.pendingSignatures || 0} pending signatures`}
          changeType="neutral"
          icon={FileText}
        />
        <StatCard
          title="Cash Balance"
          value={formatCurrency(safeStats.cashBalance || 0)}
          change={formatChange(safeStats.cashBalanceChange || 0, ' from last month')}
          changeType={(safeStats.cashBalanceChange || 0) >= 0 ? 'positive' : 'negative'}
          icon={Wallet}
        />
        <StatCard
          title="Cash Flow"
          value={formatCurrency(safeStats.cashFlow || 0)}
          change={safeStats.cashFlowPeriod || 'This month'}
          changeType={(safeStats.cashFlow || 0) >= 0 ? 'positive' : 'negative'}
          icon={TrendingUp}
        />
        <StatCard
          title="Shipments"
          value={(safeStats.shipments || 0).toString()}
          change={`${safeStats.shipmentsInTransit || 0} in transit`}
          changeType="neutral"
          icon={Truck}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Revenue Trend">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={revenueData || []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: number) => [formatCurrency(value), 'Revenue']}
              />
              <Line 
                type="monotone" 
                dataKey="revenue" 
                stroke="hsl(var(--primary))" 
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Monthly Comparison">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={revenueData || []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: number) => [formatCurrency(value), 'Revenue']}
              />
              <Bar dataKey="revenue" fill="hsl(var(--accent))" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
};

export default Dashboard;
