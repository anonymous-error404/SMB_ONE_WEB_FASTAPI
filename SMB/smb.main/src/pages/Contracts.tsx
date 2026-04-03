import { Plus, FileText, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatCard } from '@/components/dashboard/StatCard';
import { DataTable } from '@/components/dashboard/DataTable';
import { useEffect, useState } from 'react';
import { fetchContracts } from '@/services/api';

const Contracts = () => {
  // Fetch dynamic data from simulated API
  const [contracts, setContracts] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      const contractsData = await fetchContracts();
      setContracts(contractsData || []);
    };
    loadData();
  }, []);
  const columns = [
    { key: 'id', header: 'Contract ID' },
    { key: 'client', header: 'Client' },
    { key: 'value', header: 'Value' },
    { 
      key: 'status', 
      header: 'Status',
      render: (value: string) => {
        const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
          Active: 'default',
          Pending: 'secondary',
          Expired: 'destructive',
        };
        return <Badge variant={variants[value] || 'default'}>{value}</Badge>;
      }
    },
    { key: 'startDate', header: 'Start Date' },
    { key: 'endDate', header: 'End Date' },
  ];

  const statusCounts = {
    active: contracts.filter(c => c.status === 'Active').length,
    pending: contracts.filter(c => c.status === 'Pending').length,
    expired: contracts.filter(c => c.status === 'Expired').length,
    total: contracts.length,
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Contracts</h1>
          <p className="text-muted-foreground">Manage and track your business contracts</p>
        </div>
        <Button className="gradient-primary text-white">
          <Plus className="w-4 h-4 mr-2" />
          New Contract
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Contracts"
          value={statusCounts.total.toString()}
          change="All contracts"
          changeType="neutral"
          icon={FileText}
        />
        <StatCard
          title="Active"
          value={statusCounts.active.toString()}
          change="Currently running"
          changeType="positive"
          icon={CheckCircle}
        />
        <StatCard
          title="Pending"
          value={statusCounts.pending.toString()}
          change="Awaiting approval"
          changeType="neutral"
          icon={Clock}
        />
        <StatCard
          title="Expired"
          value={statusCounts.expired.toString()}
          change="Need renewal"
          changeType="negative"
          icon={AlertTriangle}
        />
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">All Contracts</h2>
        <DataTable columns={columns} data={contracts || []} />
      </div>
    </div>
  );
};

export default Contracts;
