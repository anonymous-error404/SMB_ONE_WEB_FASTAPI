// API service layer - Connected to Python FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

// Helper function to make API calls
const apiCall = async (endpoint: string, method: string = 'GET') => {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // Add Authorization header if token exists
    const authData = localStorage.getItem('auth');
    if (authData) {
      const { token } = JSON.parse(authData);
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }
    
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error(`Error calling ${endpoint}:`, error);
    // Return null if API fails - no fallback data
    return null;
  }
};

// Simulated API delay to mimic real network requests (for fallback data)
const simulateDelay = (ms: number = 300) => 
  new Promise(resolve => setTimeout(resolve, ms));

// ============= Dashboard APIs =============

export const fetchDashboardStats = async () => {
  const data = await apiCall('/api/dashboard/stats');
  return data; // Return actual data or null, no fallback to dummy data
};

export const fetchMonthlyRevenue = async (months: number = 6) => {
  const data = await apiCall(`/api/dashboard/revenue?months=${months}`);
  return data; // Return actual data or null, no fallback to dummy data
};

// ============= Inventory APIs =============

export const fetchInventoryStats = async () => {
  const data = await apiCall('/api/inventory/stats');
  return data; // Return actual data or null
};

export const fetchCategoryData = async () => {
  const data = await apiCall('/api/inventory/categories');
  return data; // Return actual data or null
};

export const fetchStockData = async () => {
  const data = await apiCall('/api/inventory/stock-levels');
  return data; // Return actual data or null
};

export const fetchLowStockItems = async () => {
  const data = await apiCall('/api/inventory/low-stock');
  return data; // Return actual data or null
};

export const fetchAllInventoryItems = async () => {
  const data = await apiCall('/api/inventory/items');
  return data; // Return actual data or null
};

// Helper function for POST requests with data
const apiCallWithData = async (endpoint: string, method: string = 'POST', data: any = null) => {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // Add Authorization header if token exists
    const authData = localStorage.getItem('auth');
    if (authData) {
      const { token } = JSON.parse(authData);
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });
    
    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error(`Error calling ${endpoint}:`, error);
    throw error;
  }
};

export const addInventoryItem = async (itemData: {
  name: string;
  category: string;
  sku?: string;
  price: number;
  cost: number;
  stock: number;
  reorderLevel: number;
}) => {
  const result = await apiCallWithData('/api/inventory/items', 'POST', itemData);
  return result;
};

// ============= Financial APIs =============

export const fetchCashFlowData = async (months: number = 6) => {
  const data = await apiCall(`/api/financial/cash-flow?months=${months}`);
  return data; // Return actual data or null
};

export const fetchDailyCashFlowData = async (days: number = 7) => {
  const data = await apiCall(`/api/financial/cash-flow-daily?days=${days}`);
  return data; // Return actual data or null
};

export const fetchTransactions = async (count: number = 10) => {
  const data = await apiCall(`/api/financial/transactions?limit=${count}`);
  return data; // Return actual data or null
};

// ============= Insights APIs =============

export const fetchInsightsStats = async () => {
  const data = await apiCall('/api/insights/stats');
  return data; // Return actual data or null
};

export const fetchPerformanceData = async (months: number = 6) => {
  const data = await apiCall(`/api/insights/performance?months=${months}`);
  return data; // Return actual data or null
};

export const fetchBusinessMetrics = async () => {
  const data = await apiCall('/api/insights/business-metrics', 'GET');
  return data; // Return actual data or null
};

export const fetchSalesForecast = async (days: number = 7) => {
  const data = await apiCall(`/api/insights/sales-forecast?days=${days}`);
  return data; // Return actual data or null
};

export const fetchKeyInsights = async () => {
  const data = await apiCall('/api/insights/key-insights');
  return data; // Return actual data or null
};

export const fetchQuickStats = async () => {
  const data = await apiCall('/api/insights/quick-stats');
  return data; // Return actual data or null
};

// ============= Contracts APIs =============

export const fetchContracts = async () => {
  const data = await apiCall('/api/contracts');
  return data; // Return actual data or null
};

// ============= Product Forecasting APIs =============

export const fetchProductsList = async () => {
  const data = await apiCall('/api/insights/products-list');
  return data; // Return actual data or null
};

export const fetchProductForecast = async (productId: number, days: number = 7) => {
  console.log(`Calling API: /api/insights/product-forecast?product_id=${productId}&days=${days}`);
  const data = await apiCall(`/api/insights/product-forecast?product_id=${productId}&days=${days}`);
  console.log('API returned data:', data);
  return data; // Return actual data or null
};

export const fetchRestockRecommendations = async () => {
  const data = await apiCall('/api/inventory/restock-recommendations');
  return data; // Return actual data or null
};

// ============= Auth APIs =============
export const registerUser = async (payload: { 
  name: string; 
  email: string; 
  password: string;
  securityQuestion: string;
  securityAnswer: string;
}) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed');
    }
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error('registerUser error:', error);
    return null;
  }
};

export const loginUser = async (payload: { email: string; password: string }) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error('loginUser error:', error);
    return null;
  }
};

export const forgotPassword = async (payload: { email: string; securityAnswer: string; newPassword: string }) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Password reset failed');
    }
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error('forgotPassword error:', error);
    return null;
  }
};

export const getSecurityQuestion = async (email: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/security-question?email=${encodeURIComponent(email)}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to get security question');
    }
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error('getSecurityQuestion error:', error);
    return null;
  }
};

// ============= Example: Real API Implementation =============
// Uncomment and modify when ready to connect to Python backend:

/*
const API_BASE_URL = 'http://localhost:8000/api';

export const fetchDashboardStats = async () => {
  const response = await fetch(`${API_BASE_URL}/dashboard/stats`);
  if (!response.ok) throw new Error('Failed to fetch dashboard stats');
  return response.json();
};

export const fetchMonthlyRevenue = async (months: number = 6) => {
  const response = await fetch(`${API_BASE_URL}/dashboard/revenue?months=${months}`);
  if (!response.ok) throw new Error('Failed to fetch revenue data');
  return response.json();
};

// ... and so on for other endpoints
*/
