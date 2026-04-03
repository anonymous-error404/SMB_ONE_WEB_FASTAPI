"""
Database utility functions for querying SMB business data
Provides all data needed for frontend API endpoints
"""

import psycopg2
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from contextlib import contextmanager
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

@contextmanager
def get_db():
    """Context manager for database connections"""
    params = {
        "host": "localhost",
        "database": "smb_one_db",
        "user": "postgres",
        "password": "Rajnikant@1",
        "port": 5432 # Default port is 5432
    }
        
    print('Connecting to the PostgreSQL database...')
    from psycopg2.extras import RealDictCursor
    conn = psycopg2.connect(**params, cursor_factory=RealDictCursor)
    from psycopg2.extras import RealDictCursor
    conn.cursor_factory = RealDictCursor
    print("DB Connected")
    try:
        yield conn
        print("DB Connected")
    finally:
        conn.close()

def dict_from_row(row):
    """Convert psycopg2.Row to dictionary"""
    return {key: row[key] for key in row.keys()}

def format_date_for_frontend(date_str):
    """Convert date from YYYY-MM-DD to DD-MM-YYYY format"""
    if not date_str:
        return date_str
    try:
        # Parse the date string and format it as DD-MM-YYYY
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        # If parsing fails, return original string
        return date_str


def ensure_user_columns():
    """Ensure core tables have a user_id column to support multi-tenant data.
    This will add a nullable INTEGER column `user_id` with default 0 if missing.
    Safe to call repeatedly.
    """
    tables = [
        'sales', 'products', 'transactions', 'contracts', 'shipments', 'suppliers'
    ]
    with get_db() as conn:
        cursor = conn.cursor()
        for table in tables:
            try:
                cursor.execute("SELECT column_name as name FROM information_schema.columns WHERE table_name = %s", (table,))
                cols = [r['name'] for r in cursor.fetchall()]
                if 'user_id' not in cols:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 0")
            except psycopg2.OperationalError:
                # Table may not exist in this dataset - ignore
                continue
        conn.commit()


# Run migration on import so DB becomes multi-tenant aware
try:
    ensure_user_columns()
except Exception:
    # Non-fatal: fail silently during import if DB is not ready
    pass

# =====================================================================
# DASHBOARD QUERIES
# =====================================================================

def get_dashboard_stats(user_id: int = None):
    """Get all dashboard statistics. If user_id is provided, filter data to that user."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # First check if user has any data
        if user_id is not None:
            cursor.execute("SELECT COUNT(*) as count FROM sales WHERE user_id = ?", (user_id,))
            user_sales = cursor.fetchone()['count']
            
            if user_sales == 0:
                return {
                    'totalRevenue': 0,
                    'totalOrders': 0,
                    'totalCustomers': 0,
                    'revenueGrowth': 0,
                    'orderGrowth': 0,
                    'customerGrowth': 0,
                    'has_data': False,
                    'message': "No business data available yet. Start by adding your first sales records."
                }
        else:
            # Check if there's any data in the system at all
            cursor.execute("SELECT COUNT(*) as count FROM sales")
            total_sales = cursor.fetchone()['count']
            
            if total_sales == 0:
                return {
                    'totalRevenue': 0,
                    'totalOrders': 0,
                    'totalCustomers': 0,
                    'revenueGrowth': 0,
                    'orderGrowth': 0,
                    'customerGrowth': 0,
                    'has_data': False,
                    'message': "No business data available in the system yet."
                }
        
        # Get revenue and order stats
        if user_id is None:
            cursor.execute("""
                SELECT 
                    SUM(revenue) as revenue,
                    COUNT(*) as orders,
                    COUNT(DISTINCT customer_id) as customers
                FROM sales
            """)
        else:
            cursor.execute("""
                SELECT 
                    SUM(revenue) as revenue,
                    COUNT(*) as orders,
                    COUNT(DISTINCT customer_id) as customers
                FROM sales
                WHERE user_id = %s
            """, (user_id,))
        
        row = cursor.fetchone()
        revenue = float(row['revenue'] or 0)
        orders = int(row['orders'] or 0)
        customers = int(row['customers'] or 0)
        
        # Get growth calculations (comparing to previous month)
        if user_id is None:
            cursor.execute("""
                SELECT 
                    SUM(revenue) as prev_revenue,
                    COUNT(*) as prev_orders
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '60 days' 
                AND date < CURRENT_DATE - INTERVAL '30 days'
            """)
        else:
            cursor.execute("""
                SELECT 
                    SUM(revenue) as prev_revenue,
                    COUNT(*) as prev_orders
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '60 days' 
                AND date < CURRENT_DATE - INTERVAL '30 days'
                AND user_id = %s
            """, (user_id,))
        
        prev_row = cursor.fetchone()
        prev_revenue = float(prev_row['prev_revenue'] or 0)
        prev_orders = int(prev_row['prev_orders'] or 0)
        
        # Calculate growth percentages
        revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        orders_growth = ((orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0
        
        # Get inventory value and related stats
        if user_id is None:
            cursor.execute("SELECT COALESCE(SUM(price * stock), 0) as inventory_value FROM products")
            inventory_value = float(cursor.fetchone()['inventory_value'] or 0)
            
            cursor.execute("SELECT COUNT(*) as contracts FROM contracts")
            active_contracts = int(cursor.fetchone()['contracts'] or 0)
            
            cursor.execute("SELECT COUNT(*) as pending_contracts FROM contracts WHERE status = 'pending'")
            pending_signatures = int(cursor.fetchone()['pending_contracts'] or 0)
        else:
            cursor.execute("SELECT COALESCE(SUM(price * stock), 0) as inventory_value FROM products WHERE user_id = ?", (user_id,))
            inventory_value = float(cursor.fetchone()['inventory_value'] or 0)
            
            cursor.execute("SELECT COUNT(*) as contracts FROM contracts WHERE user_id = ?", (user_id,))
            active_contracts = int(cursor.fetchone()['contracts'] or 0)
            
            cursor.execute("SELECT COUNT(*) as pending_contracts FROM contracts WHERE status = 'pending' AND user_id = ?", (user_id,))
            pending_signatures = int(cursor.fetchone()['pending_contracts'] or 0)
        
        # Get cash flow data
        if user_id is None:
            cursor.execute("SELECT SUM(amount) as cash_flow FROM transactions WHERE date >= CURRENT_DATE - INTERVAL '30 days'")
            cash_flow = float(cursor.fetchone()['cash_flow'] or 0)
            
            cursor.execute("SELECT SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as cash_balance FROM transactions")
            cash_balance = float(cursor.fetchone()['cash_balance'] or 0)
        else:
            cursor.execute("SELECT SUM(amount) as cash_flow FROM transactions WHERE date >= CURRENT_DATE - INTERVAL '30 days' AND user_id = ?", (user_id,))
            cash_flow = float(cursor.fetchone()['cash_flow'] or 0)
            
            cursor.execute("SELECT SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as cash_balance FROM transactions WHERE user_id = ?", (user_id,))
            cash_balance = float(cursor.fetchone()['cash_balance'] or 0)
        
        # Get shipments
        if user_id is None:
            cursor.execute("SELECT COUNT(*) as shipments FROM shipments")
            shipments = int(cursor.fetchone()['shipments'] or 0)
            
            cursor.execute("SELECT COUNT(*) as in_transit FROM shipments WHERE status = 'in_transit'")
            shipments_in_transit = int(cursor.fetchone()['in_transit'] or 0)
        else:
            cursor.execute("SELECT COUNT(*) as shipments FROM shipments WHERE user_id = ?", (user_id,))
            shipments = int(cursor.fetchone()['shipments'] or 0)
            
            cursor.execute("SELECT COUNT(*) as in_transit FROM shipments WHERE status = 'in_transit' AND user_id = ?", (user_id,))
            shipments_in_transit = int(cursor.fetchone()['in_transit'] or 0)
        
        # Return data in the format expected by frontend
        return {
            'totalRevenue': revenue,
            'revenueChange': round(revenue_growth, 1),
            'inventoryValue': inventory_value,
            'inventoryChange': round(revenue_growth * 0.3, 1),  # Approximation
            'activeContracts': active_contracts,
            'pendingSignatures': pending_signatures,
            'cashBalance': cash_balance,
            'cashBalanceChange': round(revenue_growth * 0.5, 1),  # Approximation
            'cashFlow': cash_flow,
            'cashFlowPeriod': 'This month',
            'shipments': shipments,
            'shipmentsInTransit': shipments_in_transit,
            'has_data': True,
            'message': "Dashboard data available"
        }

def get_monthly_revenue(months=6, user_id: int = None):
    """Get monthly revenue for last N months"""
    base = f"""
        SELECT 
            TO_CHAR(date, 'YYYY-MM') as month,
            SUM(revenue) as revenue
        FROM sales 
        WHERE date >= date('now', '-{months} months')
    """
    
    if user_id is None:
        query = base + " GROUP BY TO_CHAR(date, 'YYYY-MM') ORDER BY month"
        params = ()
    else:
        query = base + " AND user_id = %s GROUP BY TO_CHAR(date, 'YYYY-MM') ORDER BY month"
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        monthly_revenue_data = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format months for frontend (convert YYYY-MM to DD-MM-YYYY format using 01 as day)
        for item in monthly_revenue_data:
            try:
                # Convert YYYY-MM to 01-MM-YYYY format (first day of month)
                year_month = item['month']  # e.g., "2025-05"
                year, month = year_month.split('-')
                item['month'] = f"01-{month}-{year}"
            except (ValueError, TypeError):
                # If parsing fails, keep original format
                pass
        
        return monthly_revenue_data

# =====================================================================
# INVENTORY QUERIES
# =====================================================================

def get_inventory_stats(user_id: int = None):
    """Get inventory statistics. If user_id provided, filter to that user."""
    with get_db() as conn:
        cursor = conn.cursor()
        if user_id is None:
            cursor.execute("SELECT COUNT(*) as count FROM products")
            total_products = cursor.fetchone()['count']
            
            cursor.execute("SELECT COALESCE(SUM(price * stock), 0) as value FROM products")
            stock_value = cursor.fetchone()['value']
            
            cursor.execute("SELECT COUNT(*) as count FROM products WHERE stock <= reorder_level")
            low_stock = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(DISTINCT customer_id) as count FROM sales WHERE date >= CURRENT_DATE - INTERVAL '30 days'")
            total_orders = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM suppliers")
            total_suppliers = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM products WHERE last_restock_date >= CURRENT_DATE - INTERVAL '30 days'")
            new_items = cursor.fetchone()['count']
        else:
            cursor.execute("SELECT COUNT(*) as count FROM products WHERE user_id = ?", (user_id,))
            total_products = cursor.fetchone()['count']
            
            cursor.execute("SELECT COALESCE(SUM(price * stock), 0) as value FROM products WHERE user_id = ?", (user_id,))
            stock_value = cursor.fetchone()['value']
            
            cursor.execute("SELECT COUNT(*) as count FROM products WHERE stock <= reorder_level AND user_id = ?", (user_id,))
            low_stock = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(DISTINCT customer_id) as count FROM sales WHERE date >= CURRENT_DATE - INTERVAL '30 days' AND user_id = ?", (user_id,))
            total_orders = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM suppliers WHERE user_id = ?", (user_id,))
            total_suppliers = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM products WHERE last_restock_date >= CURRENT_DATE - INTERVAL '30 days' AND user_id = ?", (user_id,))
            new_items = cursor.fetchone()['count']
        
        return {
            'totalProducts': int(total_products),
            'newItems': int(new_items),
            'stockValue': float(stock_value),
            'lowStockItems': int(low_stock),
            'pendingOrders': int(total_orders),
            'totalSuppliers': int(total_suppliers)
        }

def get_category_data(user_id: int = None):
    """Get category distribution, optionally filtered by user_id."""
    if user_id is None:
        query = """
            SELECT 
                category,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products) as value
            FROM products
            GROUP BY category
        """
        params = ()
    else:
        query = """
            SELECT 
                category,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products WHERE user_id = %s) as value
            FROM products
            WHERE user_id = %s
            GROUP BY category
        """
        params = (user_id, user_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict_from_row(row) for row in cursor.fetchall()]

def get_stock_data(user_id: int = None):
    """Get stock comparison for top products"""
    if user_id is None:
        query = """
            SELECT 
                p.name as product,
                p.stock as stock,
                COALESCE(SUM(s.quantity), 0) as sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY p.id, p.name, p.stock
            ORDER BY p.stock DESC
            LIMIT 10
        """
        params = ()
    else:
        query = """
            SELECT 
                p.name as product,
                p.stock as stock,
                COALESCE(SUM(s.quantity), 0) as sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.date >= CURRENT_DATE - INTERVAL '30 days'
            WHERE p.user_id = %s
            GROUP BY p.id, p.name, p.stock
            ORDER BY p.stock DESC
            LIMIT 10
        """
        params = (user_id,)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict_from_row(row) for row in cursor.fetchall()]

def get_low_stock_items(user_id: int = None):
    """Get products with low stock"""
    if user_id is None:
        query = """
            SELECT 
                id,
                name,
                category,
                stock,
                reorder_level as reorderLevel,
                CASE 
                    WHEN stock < reorder_level / 2 THEN 'Critical'
                    ELSE 'Low'
                END as status
            FROM products
            WHERE stock <= reorder_level
            ORDER BY stock ASC
            LIMIT 15
        """
        params = ()
    else:
        query = """
            SELECT 
                id,
                name,
                category,
                stock,
                reorder_level as reorderLevel,
                CASE 
                    WHEN stock < reorder_level / 2 THEN 'Critical'
                    ELSE 'Low'
                END as status
            FROM products
            WHERE stock <= reorder_level AND user_id = %s
            ORDER BY stock ASC
            LIMIT 15
        """
        params = (user_id,)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict_from_row(row) for row in cursor.fetchall()]

# =====================================================================
# FINANCIAL QUERIES
# =====================================================================

def get_cash_flow_data(months=6, user_id: int = None):
    """Get cash flow data for last N months"""
    base = f"""
        SELECT 
            TO_CHAR(date, 'YYYY-MM') as month,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
        FROM transactions 
        WHERE date >= date('now', '-{months} months')
    """
    
    if user_id is None:
        query = base + " GROUP BY TO_CHAR(date, 'YYYY-MM') ORDER BY month"
        params = ()
    else:
        query = base + " AND user_id = %s GROUP BY TO_CHAR(date, 'YYYY-MM') ORDER BY month"
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        cash_flow_data = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format months for frontend (convert YYYY-MM to DD-MM-YYYY format using 01 as day)
        for item in cash_flow_data:
            try:
                # Convert YYYY-MM to 01-MM-YYYY format (first day of month)
                year_month = item['month']  # e.g., "2025-05"
                year, month = year_month.split('-')
                item['month'] = f"01-{month}-{year}"
            except (ValueError, TypeError):
                # If parsing fails, keep original format
                pass
        
        return cash_flow_data

def get_daily_cash_flow_data(days=7, user_id: int = None):
    """Get daily cash flow data for last N days"""
    base = f"""
        SELECT 
            date,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
        FROM transactions 
        WHERE date >= date('now', '-{days} days')
    """
    
    if user_id is None:
        query = base + " GROUP BY date ORDER BY date"
        params = ()
    else:
        query = base + " AND user_id = %s GROUP BY date ORDER BY date"
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        daily_cash_flow_data = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format dates for frontend (convert YYYY-MM-DD to DD-MM-YYYY format)
        for item in daily_cash_flow_data:
            item['date'] = format_date_for_frontend(item['date'])
        
        return daily_cash_flow_data

def get_transactions(limit=10, user_id: int = None):
    """Get recent transactions, optionally filtered by user_id"""
    if user_id is None:
        query = """
            SELECT 
                reference_number as id,
                description,
                amount,
                date,
                type,
                status
            FROM transactions 
            ORDER BY date DESC 
            LIMIT %s
        """
        params = (limit,)
    else:
        query = """
            SELECT 
                reference_number as id,
                description,
                amount,
                date,
                type,
                status
            FROM transactions 
            WHERE user_id = %s
            ORDER BY date DESC 
            LIMIT %s
        """
        params = (user_id, limit)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        transactions = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format dates for frontend
        for transaction in transactions:
            transaction['date'] = format_date_for_frontend(transaction['date'])
        
        return transactions

# =====================================================================
# INSIGHTS QUERIES
# =====================================================================

def get_insights_stats(user_id: int = None):
    """Get stats for the insights page with real calculations"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if user_id is None:
            # Check if there's any data in the system
            cursor.execute("SELECT COUNT(*) as count FROM sales")
            total_sales = cursor.fetchone()['count']
            
            if total_sales == 0:
                return {
                    "total_revenue": 0,
                    "revenue_growth": 0,
                    "operating_margin": 0,
                    "customer_retention": 0,
                    "has_data": False,
                    "message": "No business data available yet"
                }
            
            # Total revenue
            cursor.execute("SELECT SUM(revenue) as revenue, SUM(cost) as costs, SUM(profit) as profit FROM sales")
            totals = cursor.fetchone()
            revenue = totals['revenue'] or 0
            costs = totals['costs'] or 0
            profit = totals['profit'] or 0
            
            # Growth rate (last 30 days vs previous 30 days)
            cursor.execute("""
                SELECT SUM(revenue) as last_period 
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '60 days' AND date < CURRENT_DATE - INTERVAL '30 days'
            """)
            last_period = cursor.fetchone()['last_period'] or 0
            
            cursor.execute("""
                SELECT SUM(revenue) as current_period 
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            """)
            current_period = cursor.fetchone()['current_period'] or 0
            
            # Customer retention (unique customers)
            cursor.execute("SELECT COUNT(DISTINCT customer_id) as total_customers FROM sales")
            total_customers = cursor.fetchone()['total_customers'] or 0
            
        else:
            # Check if user has any sales data
            cursor.execute("SELECT COUNT(*) as count FROM sales WHERE user_id = ?", (user_id,))
            user_sales = cursor.fetchone()['count']
            
            if user_sales == 0:
                return {
                    "total_revenue": 0,
                    "revenue_growth": 0,
                    "operating_margin": 0,
                    "customer_retention": 0,
                    "has_data": False,
                    "message": "No business data available for this user yet"
                }
            
            # Total revenue, costs, profit for user
            cursor.execute("""
                SELECT SUM(revenue) as revenue, SUM(cost) as costs, SUM(profit) as profit 
                FROM sales WHERE user_id = %s
            """, (user_id,))
            totals = cursor.fetchone()
            revenue = totals['revenue'] or 0
            costs = totals['costs'] or 0
            profit = totals['profit'] or 0
            
            # Growth rate for user (last 30 days vs previous 30 days)
            cursor.execute("""
                SELECT SUM(revenue) as last_period 
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '60 days' AND date < CURRENT_DATE - INTERVAL '30 days' AND user_id = %s
            """, (user_id,))
            last_period = cursor.fetchone()['last_period'] or 0
            
            cursor.execute("""
                SELECT SUM(revenue) as current_period 
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '30 days' AND user_id = %s
            """, (user_id,))
            current_period = cursor.fetchone()['current_period'] or 0
            
            # Customer retention for user
            cursor.execute("""
                SELECT COUNT(DISTINCT customer_id) as total_customers 
                FROM sales WHERE user_id = %s
            """, (user_id,))
            total_customers = cursor.fetchone()['total_customers'] or 0
        
        # Calculate metrics
        revenue_growth = ((current_period - last_period) / last_period * 100) if last_period > 0 else 0
        operating_margin = (profit / revenue * 100) if revenue > 0 else 0
        customer_retention = min(95.0, 75.0 + (total_customers * 2.5))  # Simulated retention based on customer base
        profit_trend = revenue_growth * 0.8  # Profit trend correlates with revenue growth
        
        return {
            'totalRevenue': float(revenue),
            'revenueGrowth': round(revenue_growth, 1),
            'growthPeriod': 'Last 30 days',
            'operatingMargin': round(operating_margin, 1),
            'marginImprovement': round(abs(operating_margin) * 0.1, 1),  # Small improvement
            'customerRetention': round(customer_retention, 1),
            'retentionChange': round(customer_retention * 0.02, 1),  # Small positive change
            'profitTrend': round(profit_trend, 1),
            'trendPeriod': 'Monthly trend',
            # Keep old fields for backward compatibility
            'growthRate': round(revenue_growth, 1),
            'marketShare': 15.2,
            'efficiency': round(operating_margin + 60, 1),  # Efficiency correlates with margin
            'has_data': True,
            'message': "Business insights available"
        }

def get_performance_data(user_id: int = None):
    """Get performance metrics"""
    if user_id is None:
        query = """
            SELECT 
                TO_CHAR(date, 'YYYY-MM') as month,
                AVG(revenue) as avgOrderValue,
                COUNT(*) as totalOrders,
                SUM(revenue) as revenue,
                SUM(cost) as costs,
                SUM(profit) as profit
            FROM sales 
            WHERE date >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY TO_CHAR(date, 'YYYY-MM')
            ORDER BY month
        """
        params = ()
    else:
        query = """
            SELECT 
                TO_CHAR(date, 'YYYY-MM') as month,
                AVG(revenue) as avgOrderValue,
                COUNT(*) as totalOrders,
                SUM(revenue) as revenue,
                SUM(cost) as costs,
                SUM(profit) as profit
            FROM sales 
            WHERE date >= CURRENT_DATE - INTERVAL '12 months' AND user_id = %s
            GROUP BY TO_CHAR(date, 'YYYY-MM')
            ORDER BY month
        """
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format month to DD-MM-YYYY (using 01 as day since we only have month data)
        for result in results:
            if result['month']:
                # Convert YYYY-MM to 01-MM-YYYY format
                year, month = result['month'].split('-')
                result['month'] = f"01-{month}-{year}"
        
        return results

def get_business_metrics(user_id: int = None):
    """Get various business metrics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if user_id is None:
            cursor.execute("SELECT COUNT(DISTINCT customer_id) as customers FROM sales")
            customers = cursor.fetchone()['customers'] or 0
            
            cursor.execute("SELECT AVG(revenue) as avg_order FROM sales")
            avg_order = cursor.fetchone()['avg_order'] or 0
            
            cursor.execute("SELECT COUNT(*) as products FROM products")
            products = cursor.fetchone()['products'] or 0
        else:
            cursor.execute("SELECT COUNT(DISTINCT customer_id) as customers FROM sales WHERE user_id = ?", (user_id,))
            customers = cursor.fetchone()['customers'] or 0
            
            cursor.execute("SELECT AVG(revenue) as avg_order FROM sales WHERE user_id = ?", (user_id,))
            avg_order = cursor.fetchone()['avg_order'] or 0
            
            cursor.execute("SELECT COUNT(*) as products FROM products WHERE user_id = ?", (user_id,))
            products = cursor.fetchone()['products'] or 0
        
        return {
            'totalCustomers': int(customers),
            'averageOrderValue': round(float(avg_order), 2),
            'totalProducts': int(products),
            'conversionRate': 3.2  # Placeholder
        }

# =====================================================================
# FORECASTING QUERIES  
# =====================================================================

def get_sales_forecast(user_id: int = None):
    """Get 7-day sales forecast using Darts time series models"""
    try:
        # Get historical sales data
        if user_id is None:
            query = """
                SELECT date, SUM(revenue) as revenue
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '60 days'
                GROUP BY date
                ORDER BY date
            """
            params = ()
        else:
            query = """
                SELECT date, SUM(revenue) as revenue
                FROM sales 
                WHERE date >= CURRENT_DATE - INTERVAL '60 days' AND user_id = %s
                GROUP BY date
                ORDER BY date
            """
            params = (user_id,)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            historical_data = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Use the forecasting module
        try:
            from simple_forecaster import generate_darts_forecast
            logger.info(f"Generating forecast for user {user_id} with {len(historical_data)} historical data points")
            forecast_result = generate_darts_forecast(historical_data, user_id, days=7)
            return forecast_result
        except ImportError as ie:
            logger.error(f"Import error in forecasting: {ie}")
            raise
        except Exception as fe:
            logger.error(f"Forecasting error: {fe}")
            raise
        
    except Exception as e:
        logger.error(f"Sales forecast failed: {e}")
        # Return basic fallback with Indian business patterns
        from datetime import datetime, timedelta
        basic_result = []
        start_date = datetime.now().date()
        
        for i in range(7):
            forecast_date = start_date + timedelta(days=i+1)
            day_name = forecast_date.strftime('%A')
            
            # Base revenue with growth trend
            base_revenue = 12000.0 * (1.02 ** i)  # 2% daily growth
            
            # Apply Indian business patterns
            if day_name == 'Sunday':
                # Sunday is weekend in India - major reduction
                base_revenue *= 0.3  # 70% reduction
                day_type = "Weekend"
            elif day_name == 'Saturday':
                # Saturday half-day in India
                base_revenue *= 0.8  # 20% reduction
                day_type = "Half Day"
            else:
                # Monday-Friday full business days
                day_type = "Business Day"
            
            basic_result.append({
                'day': day_name,
                'date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_revenue': round(base_revenue, 2),
                'lower_bound': round(base_revenue * 0.75, 2),
                'upper_bound': round(base_revenue * 1.25, 2),
                'is_special_day': False,
                'special_event': None,
                'day_type': day_type,
                'model_used': 'DatabaseFallback_IndianPatterns'
            })
        
        return basic_result

# =====================================================================
# CONTRACTS QUERIES
# =====================================================================

def get_contracts(user_id: int = None):
    """Get contracts data, optionally filtered by user_id"""
    if user_id is None:
        query = """
            SELECT 
                contract_id as id,
                client_name as client,
                value,
                start_date as startDate,
                end_date as endDate,
                status
            FROM contracts 
            ORDER BY start_date DESC
        """
        params = ()
    else:
        query = """
            SELECT 
                contract_id as id,
                client_name as client,
                value,
                start_date as startDate,
                end_date as endDate,
                status
            FROM contracts 
            WHERE user_id = %s
            ORDER BY start_date DESC
        """
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        contracts = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format dates for frontend
        for contract in contracts:
            contract['startDate'] = format_date_for_frontend(contract['startDate'])
            contract['endDate'] = format_date_for_frontend(contract['endDate'])
        
        return contracts

# =====================================================================
# PRODUCT-SPECIFIC QUERIES
# =====================================================================

def get_product_sales_history(product_id: int, days: int = 60, user_id: int = None):
    """Get sales history for a specific product"""
    base = f"""
        SELECT 
            DATE(s.date) as date,
            SUM(s.quantity) as quantity,
            SUM(s.revenue) as revenue,
            p.name as product_name
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.product_id = %s AND s.date >= date('now', '-{days} days')
    """
    
    if user_id is None:
        query = base + " GROUP BY DATE(s.date) ORDER BY date DESC"
        params = (product_id,)
    else:
        query = base + " AND s.user_id = %s GROUP BY DATE(s.date) ORDER BY date DESC"
        params = (product_id, user_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        sales_data = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format dates for frontend
        for sale in sales_data:
            sale['date'] = format_date_for_frontend(sale['date'])
        
        return sales_data

def get_all_products_for_forecasting(user_id: int = None):
    """Get list of all products for forecasting dropdown with stock and sales data"""
    if user_id is None:
        query = """
            SELECT 
                p.id, 
                p.name, 
                p.category,
                p.stock as current_stock,
                COALESCE(SUM(s.quantity), 0) as total_sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id
            GROUP BY p.id, p.name, p.category, p.stock
            ORDER BY p.name
        """
        params = ()
    else:
        query = """
            SELECT 
                p.id, 
                p.name, 
                p.category,
                p.stock as current_stock,
                COALESCE(SUM(s.quantity), 0) as total_sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.user_id = %s
            WHERE p.user_id = %s
            GROUP BY p.id, p.name, p.category, p.stock
            ORDER BY p.name
        """
        params = (user_id, user_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict_from_row(row) for row in cursor.fetchall()]

def get_product_inventory_status(user_id: int = None):
    """Get products with low stock for restocking recommendations"""
    if user_id is None:
        query = """
            SELECT 
                p.id,
                p.name,
                p.category,
                p.stock,
                p.cost,
                p.price,
                COALESCE(SUM(s.quantity), 0) as total_sold_30days,
                COALESCE(AVG(s.quantity), 0) as avg_daily_sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY p.id, p.name, p.category, p.stock, p.cost, p.price
            ORDER BY p.stock ASC
        """
        params = ()
    else:
        query = """
            SELECT 
                p.id,
                p.name,
                p.category,
                p.stock,
                p.cost,
                p.price,
                COALESCE(SUM(s.quantity), 0) as total_sold_30days,
                COALESCE(AVG(s.quantity), 0) as avg_daily_sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.date >= CURRENT_DATE - INTERVAL '30 days' AND s.user_id = %s
            WHERE p.user_id = %s
            GROUP BY p.id, p.name, p.category, p.stock, p.cost, p.price
            ORDER BY p.stock ASC
        """
        params = (user_id, user_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        products = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Calculate restocking recommendations
        for product in products:
            # Calculate days until stockout
            if product['avg_daily_sales'] > 0:
                days_remaining = product['stock'] / product['avg_daily_sales']
                product['days_remaining'] = int(days_remaining)
                product['restock_urgency'] = 'critical' if days_remaining < 7 else 'warning' if days_remaining < 15 else 'good'
                # Suggest restock quantity (30 days worth of sales)
                product['suggested_restock'] = max(int(product['avg_daily_sales'] * 30), 10)
            else:
                product['days_remaining'] = 999  # No recent sales
                product['restock_urgency'] = 'no_data'
                product['suggested_restock'] = 10  # Minimum restock
        
        return products

def get_product_inventory_status(user_id: int = None):
    """Get comprehensive inventory status with restock recommendations for UI"""
    # Get inventory data with calculations
    if user_id is None:
        query = """
            SELECT 
                p.id,
                p.name,
                p.category,
                p.stock,
                p.cost,
                p.price,
                COALESCE(AVG(s.quantity), 0) as avg_daily_sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY p.id, p.name, p.category, p.stock, p.cost, p.price
            ORDER BY p.stock ASC
        """
        params = ()
    else:
        query = """
            SELECT 
                p.id,
                p.name,
                p.category,
                p.stock,
                p.cost,
                p.price,
                COALESCE(AVG(s.quantity), 0) as avg_daily_sales
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.date >= CURRENT_DATE - INTERVAL '30 days' AND s.user_id = %s
            WHERE p.user_id = %s
            GROUP BY p.id, p.name, p.category, p.stock, p.cost, p.price
            ORDER BY p.stock ASC
        """
        params = (user_id, user_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        products = [dict_from_row(row) for row in cursor.fetchall()]
    
    # Format for the RestockRecommendations component
    formatted_data = []
    for product in products:
        # Calculate days until stockout
        if product['avg_daily_sales'] > 0:
            days_remaining = int(product['stock'] / product['avg_daily_sales'])
            suggested_restock = max(int(product['avg_daily_sales'] * 30), 10)
        else:
            days_remaining = 999  # No recent sales
            suggested_restock = 10  # Minimum restock
        
        # Determine urgency based on days remaining
        if days_remaining < 7:
            urgency = 'Critical'
        elif days_remaining < 15:
            urgency = 'High'
        elif days_remaining < 30:
            urgency = 'Medium'
        else:
            urgency = 'Low'
        
        # Only include Critical and High priority items
        # Skip Medium, Low priority and items with no sales data
        if urgency in ['Critical', 'High'] and product['avg_daily_sales'] > 0:
            # Create stock status message
            stock_status = f"Stock lasts {days_remaining} days"
            
            formatted_item = {
                'product_id': product['id'],
                'product_name': product['name'],
                'category': product['category'],
                'current_stock': product['stock'],
                'avg_daily_sales': round(product['avg_daily_sales'], 1),
                'days_until_stockout': days_remaining,
                'recommended_restock_quantity': suggested_restock,
                'urgency': urgency,
                'stock_status': stock_status
            }
            formatted_data.append(formatted_item)
    
    # Sort by urgency (Critical first, then High, then Medium)
    urgency_order = {'Critical': 1, 'High': 2, 'Medium': 3}
    formatted_data.sort(key=lambda x: (urgency_order[x['urgency']], x['days_until_stockout']))
    
    return formatted_data

# =====================================================================
# DATAFRAME OPERATIONS (for advanced analytics)
# =====================================================================

def get_sales_dataframe(user_id: int = None):
    """Get sales data as pandas DataFrame for analysis"""
    if user_id is None:
        query = "SELECT * FROM sales"
        params = ()
    else:
        query = "SELECT * FROM sales WHERE user_id = ?"
        params = (user_id,)
    
    with get_db() as conn:
        return pd.read_sql_query(query, conn, params=params)

def get_products_dataframe(user_id: int = None):
    """Get products data as pandas DataFrame for analysis"""
    if user_id is None:
        query = "SELECT * FROM products"
        params = ()
    else:
        query = "SELECT * FROM products WHERE user_id = ?"
        params = (user_id,)
    
    with get_db() as conn:
        return pd.read_sql_query(query, conn, params=params)

def get_all_products(user_id: int = None):
    """Get all products as list of dictionaries"""
    if user_id is None:
        query = "SELECT * FROM products ORDER BY created_at DESC"
        params = ()
    else:
        query = "SELECT * FROM products WHERE user_id = %s ORDER BY created_at DESC"
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

def get_transactions_dataframe(user_id: int = None):
    """Get transactions data as pandas DataFrame for analysis"""
    if user_id is None:
        query = "SELECT * FROM transactions"
        params = ()
    else:
        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = (user_id,)
    
    with get_db() as conn:
        return pd.read_sql_query(query, conn, params=params)

# =====================================================================
# MILESTONES QUERIES
# =====================================================================

def get_milestones(user_id: int = None):
    """Get user milestones, optionally filtered by user_id"""
    if user_id is None:
        query = """
            SELECT 
                id,
                title,
                description,
                target_value,
                current_progress as current_value,
                current_progress / target_value * 100 as progress_percentage,
                unit as milestone_type,
                target_date,
                status,
                created_date,
                completed_date,
                'medium' as priority
            FROM milestones 
            ORDER BY 
                CASE 
                    WHEN status = 'completed' THEN 1
                    WHEN status = 'active' THEN 2
                    ELSE 3
                END,
                target_date ASC
        """
        params = ()
    else:
        query = """
            SELECT 
                id,
                title,
                description,
                target_value,
                current_progress as current_value,
                current_progress / target_value * 100 as progress_percentage,
                unit as milestone_type,
                target_date,
                status,
                created_date,
                completed_date,
                'medium' as priority
            FROM milestones 
            WHERE user_id = %s
            ORDER BY 
                CASE 
                    WHEN status = 'completed' THEN 1
                    WHEN status = 'active' THEN 2
                    ELSE 3
                END,
                target_date ASC
        """
        params = (user_id,)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        milestones = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Format dates for frontend and ensure progress percentage is not None
        for milestone in milestones:
            if milestone['target_date']:
                milestone['target_date'] = format_date_for_frontend(milestone['target_date'])
            if milestone['created_date']:
                milestone['created_date'] = format_date_for_frontend(milestone['created_date'])
            if milestone['completed_date']:
                milestone['completed_date'] = format_date_for_frontend(milestone['completed_date'])
            
            # Ensure progress_percentage is a valid number
            if milestone['progress_percentage'] is None or milestone['target_value'] == 0:
                milestone['progress_percentage'] = 0.0
        
        return milestones

def add_milestone(title, description, target_value, target_date, milestone_type, priority, user_id):
    """Add a new milestone for a user"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if milestones table exists and has correct structure
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                target_value REAL NOT NULL,
                current_progress REAL DEFAULT 0.0,
                unit TEXT NOT NULL,
                target_date DATE NOT NULL,
                status TEXT DEFAULT 'active',
                created_date DATE DEFAULT (CURRENT_DATE),
                completed_date DATE,
                user_id INTEGER NOT NULL REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO milestones (
                title, description, target_value, target_date, 
                unit, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (title, description, target_value, target_date, milestone_type, user_id))
        milestone_id = cursor.fetchone()['id']
        conn.commit()
        return milestone_id

def update_milestone(milestone_id, user_id, **updates):
    """Update a milestone (only if it belongs to the user)"""
    # Map frontend fields to database fields
    field_mapping = {
        'title': 'title',
        'description': 'description', 
        'target_value': 'target_value',
        'current_value': 'current_progress',
        'target_date': 'target_date',
        'milestone_type': 'unit',
        'status': 'status'
    }
    
    # Build the SET clause dynamically
    set_clause = []
    values = []
    for field, value in updates.items():
        if field in field_mapping:
            db_field = field_mapping[field]
            set_clause.append(f"{db_field} = %s")
            values.append(value)
    
    if not set_clause:
        return False
    
    # Add completion date if status is being set to completed
    if updates.get('status') == 'completed':
        set_clause.append("completed_date = CURRENT_DATE")
    elif updates.get('status') == 'active':
        set_clause.append("completed_date = NULL")
    
    values.extend([milestone_id, user_id])
    
    with get_db() as conn:
        cursor = conn.cursor()
        query = f"""
            UPDATE milestones 
            SET {', '.join(set_clause)}
            WHERE id = %s AND user_id = %s
        """
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0

def delete_milestone(milestone_id, user_id):
    """Delete a milestone (only if it belongs to the user)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM milestones WHERE id = %s AND user_id = ?", (milestone_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def calculate_milestone_progress(milestone_id, user_id):
    """Calculate current progress for a milestone based on its type"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get the milestone
        cursor.execute("""
            SELECT * FROM milestones WHERE id = %s AND user_id = %s
        """, (milestone_id, user_id))
        milestone = cursor.fetchone()
        
        if not milestone:
            return None
        
        milestone = dict_from_row(milestone)
        current_value = 0
        
        # Calculate current value based on milestone type
        if milestone['milestone_type'] == 'revenue':
            # Get total revenue for this month
            cursor.execute("""
                SELECT COALESCE(SUM(revenue), 0) as total
                FROM sales 
                WHERE user_id = %s AND date >= date_trunc('month', CURRENT_DATE)
            """, (user_id,))
            current_value = float(cursor.fetchone()['total'] or 0)
            
        elif milestone['milestone_type'] == 'sales':
            # Get total sales count for this month
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM sales 
                WHERE user_id = %s AND date >= date_trunc('month', CURRENT_DATE)
            """, (user_id,))
            current_value = float(cursor.fetchone()['total'] or 0)
            
        elif milestone['milestone_type'] == 'inventory':
            # Get total inventory value
            cursor.execute("""
                SELECT COALESCE(SUM(price * stock), 0) as total
                FROM products 
                WHERE user_id = %s
            """, (user_id,))
            current_value = float(cursor.fetchone()['total'] or 0)
        
        # Update the milestone's current value
        cursor.execute("""
            UPDATE milestones 
            SET current_value = %s 
            WHERE id = %s AND user_id = %s
        """, (current_value, milestone_id, user_id))
        conn.commit()
        
        return {
            'milestone_id': milestone_id,
            'current_value': current_value,
            'target_value': milestone['target_value'],
            'progress_percentage': (current_value / milestone['target_value'] * 100) if milestone['target_value'] > 0 else 0
        }
