import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Package, AlertCircle, BarChart3, RefreshCw } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Bar } from 'recharts';
import { fetchProductsList, fetchProductForecast } from '@/services/api';

interface Product {
  id: number;
  name: string;
  category: string;
  current_stock: number;
  total_sales: number;
}

interface ForecastData {
  date: string;
  quantity: number;
  revenue: number;
  confidence: string;
  day: string;
  product_id: number;
}

const ProductForecast: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [forecastData, setForecastData] = useState<ForecastData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Load products list on component mount
  useEffect(() => {
    const loadProducts = async () => {
      try {
        const data = await fetchProductsList();
        if (data) {
          setProducts(data);
        }
      } catch (err) {
        console.error('Failed to load products:', err);
        setError('Failed to load products list');
      }
    };

    loadProducts();
  }, []);

  // Generate forecast when product changes (always 7 days)
  const generateForecast = async () => {
    if (!selectedProductId) return;

    setLoading(true);
    setError(null);

    try {
      console.log('Generating forecast for product ID:', selectedProductId);
      const data = await fetchProductForecast(selectedProductId, 7);
      console.log('Received forecast data:', data);
      
      if (data && Array.isArray(data) && data.length > 0) {
        setForecastData(data);
        console.log('Forecast data set successfully');
      } else {
        console.log('No valid forecast data received:', data);
        setError('No forecast data available for this product');
      }
    } catch (err) {
      console.error('Failed to generate forecast:', err);
      setError(`Failed to generate product forecast: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  // Get selected product details
  const selectedProduct = products.find(p => p.id === selectedProductId);

  // Calculate forecast summary
  const forecastSummary = forecastData.reduce((acc, day) => ({
    totalQuantity: acc.totalQuantity + day.quantity,
    totalRevenue: acc.totalRevenue + day.revenue,
    avgDaily: acc.avgDaily + day.quantity / forecastData.length
  }), { totalQuantity: 0, totalRevenue: 0, avgDaily: 0 });

  return (
    <div className="space-y-4">
      {/* Single Consolidated Product Forecasting Box */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Individual Product Sales Forecast (Next 7 Days)
              </CardTitle>
              <CardDescription>
                Analyze sales patterns and forecast demand for specific products over the next week
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Product Selection and Controls - Compact Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className="text-sm font-medium mb-1 block">Select Product</label>
              <Select 
                value={selectedProductId?.toString() || ""} 
                onValueChange={(value) => setSelectedProductId(parseInt(value))}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="Choose a product..." />
                </SelectTrigger>
                <SelectContent>
                  {products.map((product) => (
                    <SelectItem key={product.id} value={product.id.toString()}>
                      <div className="flex items-center gap-2">
                        <Package className="w-3 h-3" />
                        <span className="text-sm">{product.name}</span>
                        <Badge variant="secondary" className="text-xs">{product.category}</Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button 
                onClick={generateForecast}
                disabled={!selectedProductId || loading}
                className="w-full h-9"
                size="sm"
              >
                {loading ? 'Generating...' : 'Generate 7-Day Forecast'}
              </Button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="flex items-center gap-2 text-destructive bg-destructive/10 p-3 rounded-lg">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Product Details - Compact */}
          {selectedProduct && (
            <div className="bg-muted/30 rounded-lg p-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground text-xs">Product:</span>
                  <p className="font-medium">{selectedProduct.name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Category:</span>
                  <p className="font-medium">{selectedProduct.category}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Current Stock:</span>
                  <p className="font-medium">{selectedProduct.current_stock || 0} units</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Total Sales:</span>
                  <p className="font-medium">{selectedProduct.total_sales || 0} units</p>
                </div>
              </div>
            </div>
          )}

          {/* Forecast Results - Integrated Summary and Chart */}
          {forecastData.length > 0 && !loading && (
            <>
              {/* Compact Summary Row */}
              <div className="grid grid-cols-3 gap-4 py-3 bg-muted/20 rounded-lg px-4">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <TrendingUp className="w-3 h-3 text-blue-500" />
                    <span className="text-xs font-medium">Total Forecast</span>
                  </div>
                  <p className="text-lg font-bold">{Math.round(forecastSummary.totalQuantity)}</p>
                  <p className="text-xs text-muted-foreground">units over 7 days</p>
                </div>

                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Package className="w-3 h-3 text-green-500" />
                    <span className="text-xs font-medium">Daily Average</span>
                  </div>
                  <p className="text-lg font-bold">{Math.round(forecastSummary.avgDaily)}</p>
                  <p className="text-xs text-muted-foreground">units per day</p>
                </div>

                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <TrendingUp className="w-3 h-3 text-purple-500" />
                    <span className="text-xs font-medium">Revenue</span>
                  </div>
                  <p className="text-lg font-bold">₹{Math.round(forecastSummary.totalRevenue / 1000)}K</p>
                  <p className="text-xs text-muted-foreground">estimated revenue</p>
                </div>
              </div>

              {/* Compact Chart */}
              <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Sales & Revenue Forecast for {selectedProduct?.name}
                </h4>
                <ResponsiveContainer width="100%" height={250}>
                  <ComposedChart data={forecastData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="day" 
                      fontSize={10}
                    />
                    <YAxis yAxisId="quantity" orientation="left" fontSize={10} />
                    <YAxis yAxisId="revenue" orientation="right" fontSize={10} />
                    <Tooltip
                      formatter={(value, name) => [
                        name === 'quantity' ? `${Math.round(Number(value))} units` : `₹${Math.round(Number(value))}`,
                        name === 'quantity' ? 'Quantity' : 'Revenue'
                      ]}
                      labelFormatter={(value) => `Day: ${value}`}
                    />
                    <Bar 
                      yAxisId="quantity"
                      dataKey="quantity" 
                      fill="#3b82f6" 
                      name="quantity"
                      opacity={0.8}
                    />
                    <Line 
                      yAxisId="revenue"
                      type="monotone" 
                      dataKey="revenue" 
                      stroke="#10b981" 
                      strokeWidth={2}
                      name="revenue"
                      dot={{ fill: '#10b981', strokeWidth: 1, r: 3 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Error State */}
          {error && (
            <div className="flex items-center justify-center h-32 text-center">
              <div>
                <AlertCircle className="w-6 h-6 text-destructive mx-auto mb-2" />
                <p className="text-sm text-destructive">{error}</p>
              </div>
            </div>
          )}

          {/* Loading State */}
          {loading && selectedProductId && (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" />
              <span className="text-sm">Generating forecast...</span>
            </div>
          )}

          {/* Empty State */}
          {!selectedProductId && (
            <div className="text-center h-24 flex items-center justify-center">
              <div>
                <Package className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">Select a product to view forecast</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ProductForecast;