import { ChartCard } from '@/components/dashboard/ChartCard';
import { DataTable } from '@/components/dashboard/DataTable';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useEffect, useState } from 'react';
import { fetchCashFlowData, fetchDailyCashFlowData, fetchTransactions } from '@/services/api';
import { formatIndianCurrencyFull, formatDate } from '@/lib/utils';

const Financial = () => {
  // Fetch dynamic data from simulated API
  const [cashFlowData, setCashFlowData] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      const [cashFlow, trans] = await Promise.all([
        fetchDailyCashFlowData(7),
        fetchTransactions(10)
      ]);
      setCashFlowData(cashFlow || []);
      setTransactions(trans || []);
    };
    loadData();
  }, []);

  // Format transactions for display
  const formattedTransactions = transactions.map(t => ({
    ...t,
    amount: `${formatIndianCurrencyFull(Math.abs(t.amount))}${t.amount < 0 ? ' (-)' : ''}`,
  }));

  const columns = [
    { key: 'id', header: 'Transaction ID' },
    { key: 'date', header: 'Date' },
    { key: 'description', header: 'Description' },
    { 
      key: 'amount', 
      header: 'Amount',
      render: (value: string, row: any) => (
        <span className={row.type === 'Expense' ? 'text-destructive' : 'text-success font-medium'}>
          {value}
        </span>
      )
    },
    { key: 'type', header: 'Type' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Financial</h1>
          <p className="text-muted-foreground">Track your business finances and cash flow</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Cash Flow Trend">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={cashFlowData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="date" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Area 
                type="monotone" 
                dataKey="income" 
                stackId="1"
                stroke="hsl(var(--success))" 
                fill="hsl(var(--success))"
                fillOpacity={0.6}
              />
              <Area 
                type="monotone" 
                dataKey="expenses" 
                stackId="2"
                stroke="hsl(var(--destructive))" 
                fill="hsl(var(--destructive))"
                fillOpacity={0.6}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Net Profit Margin">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={cashFlowData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="date" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Line 
                type="monotone" 
                dataKey="income" 
                stroke="hsl(var(--primary))" 
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Recent Transactions</h2>
        <DataTable columns={columns} data={formattedTransactions} />
      </div>
    </div>
  );
};

export default Financial;
