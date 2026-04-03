import { Package, DollarSign, AlertTriangle, ShoppingCart, Users, Plus } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { DataTable } from '@/components/dashboard/DataTable';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useEffect, useState } from 'react';
import { fetchInventoryStats, fetchCategoryData, fetchStockData, addInventoryItem, fetchAllInventoryItems } from '../services/api';
import { formatIndianCurrencyFull } from '@/lib/utils';
import RestockRecommendations from '@/components/dashboard/RestockRecommendations';

const COLORS = ['hsl(var(--primary))', 'hsl(var(--accent))', 'hsl(var(--success))', 'hsl(var(--warning))'];

const Inventory = () => {
  // Fetch dynamic data from simulated API
  const [stats, setStats] = useState<any>(null);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [stockData, setStockData] = useState<any[]>([]);
  
  // Add item modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [inventoryItems, setInventoryItems] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    sku: '',
    price: '',
    cost: '',
    stock: '',
    reorderLevel: ''
  });

  const loadData = async () => {
    const [statsData, category, stock, allItems] = await Promise.all([
      fetchInventoryStats(),
      fetchCategoryData(),
      fetchStockData(),
      fetchAllInventoryItems()
    ]);
    setStats(statsData || {});
    setCategoryData(category || []);
    setStockData(stock || []);
    setInventoryItems(allItems || []);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      
      // Validate required fields
      if (!formData.name || !formData.category || !formData.price || !formData.cost || !formData.stock) {
        alert('Please fill in all required fields');
        return;
      }

      const itemData = {
        name: formData.name,
        category: formData.category,
        sku: formData.sku,
        price: parseFloat(formData.price),
        cost: parseFloat(formData.cost),
        stock: parseInt(formData.stock),
        reorderLevel: parseInt(formData.reorderLevel) || 10
      };

      await addInventoryItem(itemData);
      
      // Reset form and close modal
      setFormData({
        name: '',
        category: '',
        sku: '',
        price: '',
        cost: '',
        stock: '',
        reorderLevel: ''
      });
      setIsAddModalOpen(false);
      
      // Reload data to show the new item
      await loadData();
      
      alert('Item added successfully!');
    } catch (error) {
      console.error('Error adding item:', error);
      alert('Failed to add item. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  const columns = [
    { key: 'id', header: 'Product ID' },
    { key: 'name', header: 'Product Name' },
    { key: 'category', header: 'Category' },
    { 
      key: 'stock', 
      header: 'Current Stock',
      render: (value: number, row: any) => (
        <span className={value < row.reorderLevel ? 'text-destructive font-medium' : ''}>
          {value}
        </span>
      )
    },
    { key: 'reorderLevel', header: 'Reorder Level' },
  ];

  // Use stats directly without defaults
  const safeStats = stats || {};

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-2">Inventory Management</h1>
          <p className="text-muted-foreground">Monitor stock levels and manage your inventory</p>
        </div>
        
        <div className="flex gap-2">
          <Dialog open={isViewModalOpen} onOpenChange={setIsViewModalOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="flex items-center gap-2">
                <Package size={16} />
                View Inventory
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[800px] max-h-[600px]">
              <DialogHeader>
                <DialogTitle>Current Inventory</DialogTitle>
                <DialogDescription>
                  View all items in your inventory
                </DialogDescription>
              </DialogHeader>
              
              <div className="max-h-[400px] overflow-y-auto">
                {inventoryItems.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Package size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No inventory items found</p>
                    <p className="text-sm">Add some items to get started</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {inventoryItems.map((item: any, index: number) => (
                      <div key={item.id || index} className="border rounded-lg p-4 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="font-semibold">{item.name}</h3>
                            <p className="text-sm text-muted-foreground">{item.category}</p>
                            {item.sku && <p className="text-xs text-muted-foreground">SKU: {item.sku}</p>}
                          </div>
                          <div className="text-right">
                            <p className="font-semibold">₹{item.price}</p>
                            <p className="text-sm text-muted-foreground">Cost: ₹{item.cost}</p>
                          </div>
                        </div>
                        <div className="flex justify-between items-center">
                          <div className="flex gap-4 text-sm">
                            <span>Stock: <strong>{item.stock}</strong></span>
                            <span>Reorder: <strong>{item.reorder_level}</strong></span>
                          </div>
                          <div className={`px-2 py-1 rounded text-xs ${
                            item.stock <= item.reorder_level 
                              ? 'bg-red-100 text-red-800' 
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {item.stock <= item.reorder_level ? 'Low Stock' : 'In Stock'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="flex justify-end">
                <Button variant="outline" onClick={() => setIsViewModalOpen(false)}>
                  Close
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          
          <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
            <DialogTrigger asChild>
              <Button className="flex items-center gap-2">
                <Plus size={16} />
                Add Item(s)
              </Button>
            </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Add New Inventory Item</DialogTitle>
              <DialogDescription>
                Add a new product to your inventory. All fields marked with * are required.
              </DialogDescription>
            </DialogHeader>
            
                    <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">Item Name *</label>
              <Input 
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="category" className="text-sm font-medium">Category *</label>
              <Input 
                id="category"
                name="category"
                value={formData.category}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="sku" className="text-sm font-medium">SKU</label>
              <Input 
                id="sku"
                name="sku"
                value={formData.sku}
                onChange={handleInputChange}
                placeholder="Auto-generated if empty"
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="price" className="text-sm font-medium">Selling Price *</label>
              <Input 
                id="price"
                name="price"
                type="number"
                step="0.01"
                value={formData.price}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="cost" className="text-sm font-medium">Cost Price *</label>
              <Input 
                id="cost"
                name="cost"
                type="number"
                step="0.01"
                value={formData.cost}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="stock" className="text-sm font-medium">Stock Quantity *</label>
              <Input 
                id="stock"
                name="stock"
                type="number"
                value={formData.stock}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="reorderLevel" className="text-sm font-medium">Reorder Level</label>
              <Input 
                id="reorderLevel"
                name="reorderLevel"
                type="number"
                value={formData.reorderLevel}
                onChange={handleInputChange}
                placeholder="10"
              />
            </div>
          </div>
            
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsAddModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Adding...' : 'Add Item'}
              </Button>
            </div>
          </form>
          </DialogContent>
        </Dialog>
        </div>
      </div>
        
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Products"
          value={(safeStats.totalProducts || 0).toString()}
          change={`+${safeStats.newItems || 0} new items`}
          changeType="positive"
          icon={Package}
        />
        <StatCard
          title="Stock Value"
          value={formatIndianCurrencyFull(safeStats.stockValue || 0)}
          change="Total inventory worth"
          changeType="neutral"
          icon={DollarSign}
        />
        <StatCard
          title="Pending Orders"
          value={(safeStats.pendingOrders || 0).toString()}
          change="Orders to fulfill"
          changeType="neutral"
          icon={ShoppingCart}
        />
        <StatCard
          title="Total Suppliers"
          value={(safeStats.totalSuppliers || 0).toString()}
          change="Active suppliers"
          changeType="neutral"
          icon={Users}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Stock vs Sales">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stockData || []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="product" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Bar dataKey="stock" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
              <Bar dataKey="sales" fill="hsl(var(--accent))" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Category Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoryData || []}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.category} ${(entry.value).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
                nameKey="category"
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value: any) => `${Number(value).toFixed(1)}%`}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Intelligent Restock Recommendations */}
      <RestockRecommendations />
    </div>
  );
};

export default Inventory;
