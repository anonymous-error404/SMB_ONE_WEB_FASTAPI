import { DollarSign, Package, FileText, TrendingUp, Wallet, Truck } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useEffect, useState } from 'react';
import { fetchDashboardStats, fetchMonthlyRevenue } from '@/services/api';

const Dashboard = () => {
  const [stats, setStats] = useState<any>(null);
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [statsData, revData] = await Promise.all([
          fetchDashboardStats(),
          fetchMonthlyRevenue(6),
        ]);
        console.log('DEBUG: Dashboard stats received from API:', statsData);
        setStats(statsData || {});
        setRevenueData(revData || []);
      } catch (err) {
        console.error('Dashboard data loading error:', err);
        setError('Failed to load dashboard data');
        setStats(null);
        setRevenueData([]);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const formatChange = (value: number, suffix = '') => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%${suffix}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    );
  }

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

  const s = stats || {};

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Here's your business overview.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Total Revenue"
          value={formatCurrency(s.totalRevenue || 0)}
          change={formatChange(s.revenueChange || 0, ' from last month')}
          changeType={(s.revenueChange || 0) >= 0 ? 'positive' : 'negative'}
          icon={DollarSign}
        />
        <StatCard
          title="Inventory Value"
          value={formatCurrency(s.inventoryValue || 0)}
          change={formatChange(s.inventoryChange || 0, ' from last month')}
          changeType={(s.inventoryChange || 0) >= 0 ? 'positive' : 'negative'}
          icon={Package}
        />
        <StatCard
          title="Active Contracts"
          value={(s.activeContracts || 0).toString()}
          change={`${s.pendingSignatures || 0} pending`}
          changeType="neutral"
          icon={FileText}
        />
        <StatCard
          title="Cash Balance"
          value={formatCurrency(s.cashBalance || 0)}
          change={formatChange(s.cashBalanceChange || 0, ' from last month')}
          changeType={(s.cashBalanceChange || 0) >= 0 ? 'positive' : 'negative'}
          icon={Wallet}
        />
        <StatCard
          title="Cash Flow"
          value={formatCurrency(s.cashFlow || 0)}
          change={s.cashFlowPeriod || 'This month'}
          changeType={(s.cashFlow || 0) >= 0 ? 'positive' : 'negative'}
          icon={TrendingUp}
        />
        <StatCard
          title="Shipments"
          value={(s.shipments || 0).toString()}
          change={`${s.shipmentsInTransit || 0} in transit`}
          changeType="neutral"
          icon={Truck}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Revenue Trend">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
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
            <BarChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
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
