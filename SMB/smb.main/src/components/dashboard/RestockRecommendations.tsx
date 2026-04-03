import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Package, RefreshCw, CheckCircle, AlertCircle, ChevronDown, ChevronRight, TrendingDown, Calendar, ShoppingCart } from "lucide-react";
import { fetchRestockRecommendations } from '@/services/api';

interface RestockRecommendation {
  product_id: number;
  product_name: string;
  category: string;
  current_stock: number;
  avg_daily_sales: number;
  days_until_stockout: number;
  recommended_restock_quantity: number;
  urgency: 'Critical' | 'High' | 'Medium';
  stock_status: string;
}

const RestockRecommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<RestockRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 6;

  const loadRecommendations = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchRestockRecommendations();
      if (data) {
        setRecommendations(data);
        setLastUpdated(new Date());
      } else {
        setRecommendations([]);
      }
    } catch (err) {
      console.error('Failed to load restock recommendations:', err);
      setError('Failed to load restock recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, []);

  const toggleRowExpansion = (productId: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(productId)) {
      newExpanded.delete(productId);
    } else {
      newExpanded.add(productId);
    }
    setExpandedRows(newExpanded);
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'Critical': return 'destructive';
      case 'High': return 'destructive';
      case 'Medium': return 'outline';
      default: return 'secondary';
    }
  };

  const getUrgencyIcon = (urgency: string) => {
    switch (urgency) {
      case 'Critical': return <AlertTriangle className="w-4 h-4" />;
      case 'High': return <AlertCircle className="w-4 h-4" />;
      case 'Medium': return <Package className="w-4 h-4" />;
      default: return <Package className="w-4 h-4" />;
    }
  };

  const getDetailedExplanation = (item: RestockRecommendation) => {
    const dailySales = item.avg_daily_sales;
    const currentStock = item.current_stock;
    const daysLeft = item.days_until_stockout;
    const recommendedQty = item.recommended_restock_quantity;
    
    // Calculate when stockout will occur
    const stockoutDate = new Date();
    stockoutDate.setDate(stockoutDate.getDate() + daysLeft);
    
    // Calculate why this quantity is recommended (30 days worth)
    const daysOfStock = Math.floor(recommendedQty / dailySales);
    
    return {
      stockoutDate: stockoutDate.toLocaleDateString('en-GB'),
      daysOfStock,
      explanation: item.urgency === 'Critical' 
        ? `Stock will run out in ${daysLeft} days (${stockoutDate.toLocaleDateString('en-GB')}). Immediate restocking required to avoid sales disruption.`
        : `Stock will run out in ${daysLeft} days (${stockoutDate.toLocaleDateString('en-GB')}). Restock soon to maintain healthy inventory levels.`,
      quantityReason: `Based on average daily sales of ${dailySales} units, the recommended ${recommendedQty} units will provide approximately ${daysOfStock} days of stock coverage.`
    };
  };

  // Group by urgency for summary
  const criticalItems = recommendations.filter(item => item.urgency === 'Critical');
  const highItems = recommendations.filter(item => item.urgency === 'High');

  // Pagination logic
  const totalPages = Math.ceil(recommendations.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentItems = recommendations.slice(startIndex, endIndex);

  const goToPage = (page: number) => {
    setCurrentPage(page);
    setExpandedRows(new Set()); // Collapse all rows when changing pages
  };

  return (
    <div className="space-y-6">
      {/* Error Display */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Stats - Single Consolidated Box */}
      {recommendations.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <span className="text-lg font-semibold">Inventory Stock Alert</span>
              </div>
              <Button 
                onClick={loadRecommendations}
                disabled={loading}
                variant="outline"
                size="sm"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-sm font-medium text-red-600">Critical</span>
                </div>
                <p className="text-3xl font-bold text-red-600">{criticalItems.length}</p>
                <p className="text-xs text-muted-foreground">immediate restock needed</p>
              </div>

              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4 text-orange-500" />
                  <span className="text-sm font-medium text-orange-600">High Priority</span>
                </div>
                <p className="text-3xl font-bold text-orange-600">{highItems.length}</p>
                <p className="text-xs text-muted-foreground">restock within week</p>
              </div>

              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Package className="w-4 h-4 text-blue-500" />
                  <span className="text-sm font-medium text-blue-600">Total Items</span>
                </div>
                <p className="text-3xl font-bold text-blue-600">{recommendations.length}</p>
                <p className="text-xs text-muted-foreground">requiring attention</p>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  Last updated: {lastUpdated?.toLocaleString()} • Showing {recommendations.length} items requiring attention
                </span>
                <Badge variant="outline" className="text-xs">
                  {criticalItems.length + highItems.length} urgent items
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Paginated Table */}
      {loading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-6 h-6 animate-spin mr-2" />
              <span>Loading recommendations...</span>
            </div>
          </CardContent>
        </Card>
      ) : recommendations.length > 0 ? (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>Action Required</CardTitle>
              <div className="text-sm text-muted-foreground">
                Page {currentPage} of {totalPages} • {recommendations.length} total items
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-2 font-medium w-8"></th>
                    <th className="text-left py-3 px-2 font-medium">Product</th>
                    <th className="text-left py-3 px-2 font-medium">Current Stock</th>
                    <th className="text-left py-3 px-2 font-medium">Days Left</th>
                    <th className="text-left py-3 px-2 font-medium">Restock Qty</th>
                    <th className="text-left py-3 px-2 font-medium">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {currentItems.map((item) => {
                    const isExpanded = expandedRows.has(item.product_id);
                    const details = getDetailedExplanation(item);
                    
                    return (
                      <React.Fragment key={item.product_id}>
                        <tr 
                          className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
                          onClick={() => toggleRowExpansion(item.product_id)}
                        >
                          <td className="py-3 px-2">
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-muted-foreground" />
                            )}
                          </td>
                          <td className="py-3 px-2">
                            <div>
                              <p className="font-medium text-sm">{item.product_name}</p>
                              <p className="text-xs text-muted-foreground">{item.category}</p>
                            </div>
                          </td>
                          <td className="py-3 px-2">
                            <span className="font-medium">{item.current_stock}</span>
                            <span className="text-xs text-muted-foreground ml-1">units</span>
                          </td>
                          <td className="py-3 px-2">
                            <span className={`font-medium ${item.days_until_stockout < 7 ? 'text-red-600' : 'text-orange-600'}`}>
                              {item.days_until_stockout}
                            </span>
                            <span className="text-xs text-muted-foreground ml-1">days</span>
                          </td>
                          <td className="py-3 px-2">
                            <span className="font-medium text-green-600">+{item.recommended_restock_quantity}</span>
                            <span className="text-xs text-muted-foreground ml-1">units</span>
                          </td>
                          <td className="py-3 px-2">
                            <Badge variant={getUrgencyColor(item.urgency)} className="flex items-center gap-1 w-fit">
                              {getUrgencyIcon(item.urgency)}
                              <span className="text-xs">{item.urgency}</span>
                            </Badge>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="border-b bg-muted/20">
                            <td colSpan={6} className="py-4 px-2">
                              <div className="bg-white rounded-lg p-4 border">
                                <h4 className="font-semibold mb-3 flex items-center gap-2">
                                  <TrendingDown className="w-4 h-4" />
                                  Detailed Analysis for {item.product_name}
                                </h4>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                  <div className="space-y-3">
                                    <div className="flex items-start gap-3">
                                      <Calendar className="w-4 h-4 text-red-500 mt-0.5" />
                                      <div>
                                        <p className="font-medium text-sm">Stockout Risk</p>
                                        <p className="text-sm text-muted-foreground">{details.explanation}</p>
                                      </div>
                                    </div>
                                    
                                    <div className="flex items-start gap-3">
                                      <ShoppingCart className="w-4 h-4 text-blue-500 mt-0.5" />
                                      <div>
                                        <p className="font-medium text-sm">Sales Pattern</p>
                                        <p className="text-sm text-muted-foreground">
                                          Average daily sales: {item.avg_daily_sales} units/day
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                  
                                  <div className="space-y-3">
                                    <div className="flex items-start gap-3">
                                      <Package className="w-4 h-4 text-green-500 mt-0.5" />
                                      <div>
                                        <p className="font-medium text-sm">Recommended Quantity</p>
                                        <p className="text-sm text-muted-foreground">{details.quantityReason}</p>
                                      </div>
                                    </div>
                                    
                                    <div className="bg-muted/50 rounded-lg p-3">
                                      <p className="text-sm font-medium mb-1">Quick Stats</p>
                                      <div className="text-xs text-muted-foreground space-y-1">
                                        <p>• Expected stockout: {details.stockoutDate}</p>
                                        <p>• Restock coverage: ~{details.daysOfStock} days</p>
                                        <p>• Category: {item.category}</p>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center justify-between pt-3 border-t">
                                  <div className="text-xs text-muted-foreground">
                                    Click outside to collapse • Data updated: {lastUpdated?.toLocaleTimeString()}
                                  </div>
                                  <Badge variant={getUrgencyColor(item.urgency)} className="text-xs">
                                    {item.urgency} Priority
                                  </Badge>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  Showing {startIndex + 1}-{Math.min(endIndex, recommendations.length)} of {recommendations.length} items
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <div className="flex gap-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <Button
                        key={page}
                        variant={currentPage === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => goToPage(page)}
                        className="w-8 h-8 p-0"
                      >
                        {page}
                      </Button>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center h-32 flex items-center justify-center">
              <div>
                <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-muted-foreground">All inventory levels are optimal!</p>
                <p className="text-sm text-muted-foreground mt-1">No immediate restocking needed</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default RestockRecommendations;