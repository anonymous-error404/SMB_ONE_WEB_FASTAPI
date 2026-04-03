import { TrendingUp, TrendingDown, DollarSign, Package, AlertTriangle, AlertCircle, Activity, Star, Calendar, Info, Settings } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { Download } from 'lucide-react';
import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useEffect, useState } from 'react';
import { fetchInsightsStats, fetchPerformanceData, fetchBusinessMetrics, fetchSalesForecast, fetchKeyInsights } from '@/services/api';
import { formatIndianCurrency, formatIndianCurrencyFull, formatDate } from '@/lib/utils';
import BusinessHealthDashboard from '@/components/dashboard/BusinessHealthDashboard';
import ProductForecast from '@/components/dashboard/ProductForecast';

const Insights = () => {
  // Fetch dynamic data from simulated API
  const [stats, setStats] = useState<any>(null);
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  const [businessMetrics, setBusinessMetrics] = useState<any[]>([]);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [keyInsights, setKeyInsights] = useState<any[]>([]);
  const [hasData, setHasData] = useState<boolean>(true);

  useEffect(() => {
    const loadPriorityData = async () => {
      // Load critical data first for fast initial render
      const [statsData, performance, metrics] = await Promise.all([
        fetchInsightsStats(),
        fetchPerformanceData(6),
        fetchBusinessMetrics(),
      ]);
      
      // Check if user has data
      if (statsData && statsData.has_data === false) {
        setHasData(false);
      } else {
        setHasData(true);
      }
      
      setStats(statsData || {});
      setPerformanceData(performance || []);
      setBusinessMetrics(metrics || []);
    };
    
    const loadSecondaryData = async () => {
      // Load charts and insights next
      const [forecast, insights] = await Promise.all([
        fetchSalesForecast(7),
        fetchKeyInsights(),
      ]);
      setForecastData(forecast || []);
      setKeyInsights(insights || []);
    };
    
    // Load in stages for progressive rendering
    loadPriorityData().then(() => {
      if (hasData) {
        loadSecondaryData();
      }
    });
  }, [hasData]);

  // Show loading state while critical data is being fetched
  if (!stats) {
    return <div className="flex items-center justify-center h-96">Loading insights...</div>;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Business Insights</h1>
          <p className="text-muted-foreground">Comprehensive analytics and KPIs for your business</p>
        </div>
      </div>

      {/* No Data State */}
      {!hasData && (
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <div className="w-24 h-24 bg-muted rounded-full flex items-center justify-center">
            <AlertCircle className="w-12 h-12 text-muted-foreground" />
          </div>
          <h2 className="text-2xl font-semibold">No Business Data Available</h2>
          <p className="text-muted-foreground text-center max-w-md">
            Start by adding your sales, products, and customer data to see powerful insights and analytics.
          </p>
        </div>
      )}

      {/* Data Available State */}
      {hasData && (
        <>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Revenue Growth"
          value={`${(stats.revenueGrowth || 0) > 0 ? '+' : ''}${(stats.revenueGrowth || 0).toFixed(1)}%`}
          change={stats.growthPeriod || 'N/A'}
          changeType={(stats.revenueGrowth || 0) > 0 ? "positive" : "negative"}
          icon={TrendingUp}
        />
        <StatCard
          title="Operating Margin"
          value={`${(stats.operatingMargin || 0).toFixed(1)}%`}
          change={`${(stats.marginImprovement || 0) > 0 ? '+' : ''}${(stats.marginImprovement || 0).toFixed(1)}% improvement`}
          changeType={(stats.marginImprovement || 0) > 0 ? "positive" : "negative"}
          icon={DollarSign}
        />
        <StatCard
          title="Customer Retention"
          value={`${(stats.customerRetention || 0).toFixed(1)}%`}
          change={`${(stats.retentionChange || 0) > 0 ? '+' : ''}${(stats.retentionChange || 0).toFixed(1)}% change`}
          changeType={(stats.retentionChange || 0) > 0 ? "positive" : "negative"}
          icon={Package}
        />
        <StatCard
          title="Profit Trend"
          value={`${(stats.profitTrend || 0) > 0 ? '+' : ''}${(stats.profitTrend || 0).toFixed(1)}%`}
          change={stats.trendPeriod || 'N/A'}
          changeType={(stats.profitTrend || 0) > 0 ? "positive" : "negative"}
          icon={TrendingUp}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Revenue vs Profit Analysis">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={performanceData || []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Bar dataKey="revenue" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
              <Bar dataKey="costs" fill="hsl(var(--destructive))" radius={[8, 8, 0, 0]} />
              <Line 
                type="monotone" 
                dataKey="profit" 
                stroke="hsl(var(--success))" 
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--success))' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Business Health Metrics">
          <BusinessHealthDashboard metrics={businessMetrics} />
        </ChartCard>
      </div>

      {/* Sales Forecast Section */}
      <ChartCard title="7-Day Sales Forecast">
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={forecastData || []}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="day" 
              className="text-xs"
              label={{ value: 'Day of Week', position: 'insideBottom', offset: -5 }}
            />
            <YAxis 
              className="text-xs"
              label={{ value: 'Revenue (₹)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px'
              }}
              formatter={(value: number) => `₹${value.toLocaleString('en-IN')}`}
              labelFormatter={(label, payload) => {
                if (payload && payload.length > 0) {
                  const data = payload[0].payload;
                  let labelText = `${data.day} (${data.date})`;
                  if (data.special_event) {
                    labelText += ` - ${data.special_event}`;
                  }
                  return labelText;
                }
                return label;
              }}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="predicted_revenue" 
              stroke="hsl(var(--primary))" 
              strokeWidth={3}
              dot={(props: any) => {
                const { cx, cy, payload } = props;
                // Highlight special days with a larger, different colored dot
                if (payload.is_special_day) {
                  return (
                    <circle 
                      cx={cx} 
                      cy={cy} 
                      r={6} 
                      fill="#f59e0b" 
                      stroke="#dc2626" 
                      strokeWidth={2}
                    />
                  );
                }
                return <circle cx={cx} cy={cy} r={4} fill="hsl(var(--primary))" />;
              }}
              name="Predicted Revenue"
            />
            <Line 
              type="monotone" 
              dataKey="lower_bound" 
              stroke="hsl(var(--muted-foreground))" 
              strokeWidth={1}
              strokeDasharray="5 5"
              dot={false}
              name="Lower Bound"
            />
            <Line 
              type="monotone" 
              dataKey="upper_bound" 
              stroke="hsl(var(--muted-foreground))" 
              strokeWidth={1}
              strokeDasharray="5 5"
              dot={false}
              name="Upper Bound"
            />
          </ComposedChart>
        </ResponsiveContainer>
        {/* Special events section */}
        {forecastData && forecastData.some((d: any) => d.special_event) && (
          <div className="mt-4">
            <div className="bg-muted/30 rounded-lg p-3 text-xs">
              <p className="font-semibold mb-1">Upcoming Special Days:</p>
              <ul className="space-y-1">
                {forecastData
                  .filter((d: any) => d.special_event)
                  .map((d: any, idx: number) => (
                    <li key={idx} className="text-muted-foreground">
                      <span className="font-medium">{d.day}, {d.date}:</span> {d.special_event}
                    </li>
                  ))
                }
              </ul>
            </div>
          </div>
        )}
      </ChartCard>

      {/* Product-Level Forecasting Section */}
      <ProductForecast />

      {/* Business Insights Section - Full Width */}
      <div className="p-6 rounded-lg bg-card border border-border">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          Business Insights
        </h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {keyInsights.length > 0 ? (
            keyInsights.map((insight, index) => {
                const IconComponent = {
                  TrendingUp,
                  TrendingDown,
                  Package,
                  DollarSign,
                  AlertTriangle,
                  AlertCircle,
                  Activity,
                  Star,
                  Calendar,
                  Info
                }[insight.icon] || Info;
                
                const severityColors = {
                  positive: 'text-success',
                  warning: 'text-warning',
                  critical: 'text-destructive',
                  info: 'text-primary'
                };

                return (
                  <div key={index} className="space-y-1 p-4 rounded-lg bg-muted/30">
                    <div className="flex items-start gap-2">
                      <IconComponent className={`w-4 h-4 mt-0.5 flex-shrink-0 ${severityColors[insight.severity as keyof typeof severityColors]}`} />
                      <div>
                        <p className="text-sm font-semibold">{insight.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{insight.message}</p>
                        <p className="text-xs text-primary mt-1">→ {insight.action}</p>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-muted-foreground">Loading insights...</p>
            )}
        </div>
      </div>
        </>
      )}
    </div>
  );
};

export default Insights;
