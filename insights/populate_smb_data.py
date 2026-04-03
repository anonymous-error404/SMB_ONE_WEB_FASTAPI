"""
Populate SMB Business Data for Rakesh Singh
Creates realistic business data for a small-medium business for testing and insights
"""

import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime, date, timedelta
import random

# Database path
DB_PATH = Path(__file__).parent / "data" / "business_data.db"

def populate_smb_data():
    """Populate database with realistic SMB data"""
    params = {
        "host": "localhost",
        "database": "smb_one_db",
        "user": "postgres",
        "password": "Rajnikant@1",
        "port": 5432
    }
    conn = psycopg2.connect(**params)
    cursor = conn.cursor()
    
    # Get user_id for Rakesh Singh
    cursor.execute("SELECT id FROM users WHERE email = %s", ("rakesh@gmail.com",))
    user_result = cursor.fetchone()
    if not user_result:
        print("❌ User Rakesh Singh not found. Please create the user first.")
        return
    
    user_id = user_result[0]
    print(f"📋 Adding data for user_id: {user_id} (Rakesh Singh)")
    
    # Clear existing data for this user (if any)
    tables = ['categories', 'suppliers', 'products', 'customers', 'sales', 'contracts', 'transactions', 'shipments', 'milestones']
    for table in tables:
        cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
    
    print("🗑️  Cleared existing user data")
    
    # 1. Categories (Small business product categories)
    categories = [
        ("Electronics", "Phones, laptops, accessories"),
        ("Office Supplies", "Stationery, furniture, equipment"),
        ("Textiles", "Fabrics, garments, home textiles"),
        ("Hardware", "Tools, construction materials"),
        ("Food & Beverages", "Packaged foods, beverages")
    ]
    
    for name, desc in categories:
        cursor.execute("""
            INSERT INTO categories (name, description, user_id)
            VALUES (%s, %s, %s)
        """, (name, desc, user_id))
    
    print("✅ Added 5 product categories")
    
    # 2. Suppliers (Local and regional suppliers)
    suppliers = [
        ("Tech Distributors Pvt Ltd", "Rahul Kumar", "rahul@techdist.com", "+91-98765-43210", "Mumbai, Maharashtra", 4.2),
        ("Office World", "Priya Sharma", "priya@officeworld.in", "+91-87654-32109", "Delhi", 4.5),
        ("Textile Hub", "Suresh Gupta", "suresh@textilehub.com", "+91-76543-21098", "Tirupur, Tamil Nadu", 4.0),
        ("Hardware Solutions", "Amit Patel", "amit@hardwaresol.in", "+91-65432-10987", "Ahmedabad, Gujarat", 4.3),
        ("Food Mart Wholesale", "Neha Singh", "neha@foodmart.co.in", "+91-54321-09876", "Pune, Maharashtra", 4.1)
    ]
    
    supplier_ids = []
    for name, contact, email, phone, address, rating in suppliers:
        cursor.execute("""
            INSERT INTO suppliers (name, contact_person, email, phone, address, rating, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (name, contact, email, phone, address, rating, user_id))
        supplier_ids.append(cursor.fetchone()[0])
    
    print("✅ Added 5 suppliers")
    
    # 3. Products (SMB appropriate inventory)
    products = [
        # Electronics
        ("Samsung Galaxy A23", "Electronics", "SGAL-A23-001", 15999, 12500, 25, 5, supplier_ids[0]),
        ("HP Laptop 15s", "Electronics", "HP-L15S-002", 42999, 38000, 12, 3, supplier_ids[0]),
        ("Wireless Earbuds", "Electronics", "WE-PRO-003", 2999, 2200, 50, 10, supplier_ids[0]),
        
        # Office Supplies
        ("Office Chair Executive", "Office Supplies", "OC-EXE-004", 8500, 6800, 15, 3, supplier_ids[1]),
        ("A4 Paper Ream", "Office Supplies", "A4P-RM-005", 350, 280, 100, 20, supplier_ids[1]),
        ("Printer Canon", "Office Supplies", "PR-CAN-006", 12500, 10200, 8, 2, supplier_ids[1]),
        
        # Textiles
        ("Cotton Fabric Roll", "Textiles", "CTN-FAB-007", 1200, 950, 40, 8, supplier_ids[2]),
        ("Designer Kurta", "Textiles", "DES-KUR-008", 899, 650, 30, 5, supplier_ids[2]),
        ("Bedsheet Set", "Textiles", "BED-SET-009", 1599, 1200, 25, 5, supplier_ids[2]),
        
        # Hardware
        ("Power Drill Kit", "Hardware", "PDR-KIT-010", 3500, 2800, 20, 4, supplier_ids[3]),
        ("Paint Bucket 20L", "Hardware", "PNT-20L-011", 2200, 1800, 30, 6, supplier_ids[3]),
        ("Metal Pipes", "Hardware", "MET-PIP-012", 450, 350, 60, 12, supplier_ids[3]),
        
        # Food & Beverages
        ("Basmati Rice 25kg", "Food & Beverages", "BAS-25K-013", 2500, 2100, 20, 4, supplier_ids[4]),
        ("Cooking Oil 15L", "Food & Beverages", "COK-15L-014", 1800, 1500, 25, 5, supplier_ids[4]),
        ("Tea Packets 100g", "Food & Beverages", "TEA-100-015", 180, 140, 80, 15, supplier_ids[4])
    ]
    
    product_ids = []
    for name, category, sku, price, cost, stock, reorder_level, supplier_id in products:
        cursor.execute("""
            INSERT INTO products (name, category, sku, price, cost, stock, reorder_level, supplier_id, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (name, category, sku, price, cost, stock, reorder_level, supplier_id, user_id))
        product_ids.append(cursor.fetchone()[0])
    
    print("✅ Added 15 products across 5 categories")
    
    # 4. Customers (SMB typical customers)
    customers = [
        ("Rajesh Enterprises", "rajesh@enterprises.com", "+91-99887-76655", "Rajesh Kumar", "123 Main St, Mumbai", "Mumbai", "Maharashtra", "Business", 0, None),
        ("Priya Trading Co", "priya@trading.co.in", "+91-88776-65544", "Priya Agarwal", "456 Market Rd, Delhi", "Delhi", "Delhi", "Business", 0, None),
        ("Suresh Retail", "suresh@retail.in", "+91-77665-54433", "Suresh Patel", "789 Shop St, Ahmedabad", "Ahmedabad", "Gujarat", "Business", 0, None),
        ("Anita Stores", "anita@stores.com", "+91-66554-43322", "Anita Singh", "321 Trade Ave, Pune", "Pune", "Maharashtra", "Business", 0, None),
        ("Local Consumer", "consumer@email.com", "+91-55443-32211", "Rahul Verma", "654 Home St, Bangalore", "Bangalore", "Karnataka", "Individual", 0, None),
        ("Meera Boutique", "meera@boutique.in", "+91-44332-21100", "Meera Sharma", "987 Fashion St, Jaipur", "Jaipur", "Rajasthan", "Business", 0, None),
        ("Tech Solutions", "tech@solutions.co", "+91-33221-10099", "Vikash Kumar", "147 IT Park, Hyderabad", "Hyderabad", "Telangana", "Business", 0, None),
        ("Home Needs", "home@needs.in", "+91-22110-09988", "Sunita Gupta", "258 Residential, Chennai", "Chennai", "Tamil Nadu", "Individual", 0, None)
    ]
    
    customer_ids = []
    for name, email, phone, company, address, city, state, segment, total_purchases, last_purchase in customers:
        cursor.execute("""
            INSERT INTO customers (name, email, phone, company, address, city, state, segment, total_purchases, last_purchase_date, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (name, email, phone, company, address, city, state, segment, total_purchases, last_purchase, user_id))
        customer_ids.append(cursor.fetchone()[0])
    
    print("✅ Added 8 customers (mix of business and individual)")
    
    # 5. Sales Transactions (Last 6 months)
    sales_data = []
    start_date = date.today() - timedelta(days=180)
    
    for day_offset in range(180):
        current_date = start_date + timedelta(days=day_offset)
        
        # Generate 1-5 sales per day randomly
        daily_sales = random.randint(0, 4)
        
        for _ in range(daily_sales):
            product_idx = random.randint(0, len(products) - 1)
            product = products[product_idx]
            customer_id = random.choice(customer_ids)
            
            quantity = random.randint(1, 5)
            unit_price = product[3]  # price
            unit_cost = product[4]   # cost
            revenue = unit_price * quantity
            cost = unit_cost * quantity
            profit = revenue - cost
            
            sales_data.append((
                current_date, product_ids[product_idx], product[0], product[1],
                quantity, unit_price, revenue, cost, profit, customer_id, "India", user_id
            ))
    
    cursor.executemany("""
        INSERT INTO sales (date, product_id, product_name, category, quantity, unit_price, revenue, cost, profit, customer_id, region, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, sales_data)
    
    print(f"✅ Added {len(sales_data)} sales transactions over 6 months")
    
    # 6. Contracts (SMB typical contracts)
    contracts = [
        ("CON-2024-001", "Rajesh Enterprises", 250000, "2024-08-01", "2025-08-01", "Active", "Annual supply contract for electronics", "2024-08-15"),
        ("CON-2024-002", "Priya Trading Co", 180000, "2024-09-01", "2025-03-01", "Active", "6-month office supplies contract", "2024-09-10"),
        ("CON-2024-003", "Suresh Retail", 320000, "2024-07-15", "2025-07-15", "Active", "Retail partnership agreement", "2024-07-25"),
        ("CON-2024-004", "Tech Solutions", 150000, "2024-10-01", "2025-04-01", "Active", "Hardware maintenance contract", "2024-10-05"),
        ("CON-2024-005", "Meera Boutique", 95000, "2024-06-01", "2024-12-01", "Completed", "Textile supply contract", "2024-06-10")
    ]
    
    for contract_id, client, value, start, end, status, desc, signed in contracts:
        cursor.execute("""
            INSERT INTO contracts (contract_id, client_name, value, start_date, end_date, status, description, signed_date, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (contract_id, client, value, start, end, status, desc, signed, user_id))
    
    print("✅ Added 5 business contracts")
    
    # 7. Financial Transactions (Revenue and Expenses)
    financial_data = []
    
    # Revenue transactions from sales
    for i in range(60):  # 2 months of revenue entries
        transaction_date = date.today() - timedelta(days=i)
        amount = random.randint(15000, 45000)
        
        financial_data.append((
            transaction_date, f"Sales Revenue - {transaction_date}", amount, "Income",
            "Sales", "Completed", f"REV-{transaction_date.strftime('%Y%m%d')}-{i+1:03d}", user_id
        ))
    
    # Expense transactions
    expenses = [
        ("Rent Payment", -25000, "Expense", "Rent"),
        ("Electricity Bill", -3500, "Expense", "Utilities"),
        ("Staff Salaries", -85000, "Expense", "Payroll"),
        ("Inventory Purchase", -120000, "Expense", "Inventory"),
        ("Marketing", -8000, "Expense", "Marketing"),
        ("Transport", -6000, "Expense", "Logistics"),
        ("Office Supplies", -4000, "Expense", "Office"),
        ("Insurance", -12000, "Expense", "Insurance")
    ]
    
    for i in range(8):  # Monthly expenses for 2 months
        for desc, amount, type_val, category in expenses:
            transaction_date = date.today() - timedelta(days=(i*7))
            financial_data.append((
                transaction_date, desc, amount, type_val, category, "Completed",
                f"EXP-{transaction_date.strftime('%Y%m%d')}-{i+1:03d}", user_id
            ))
    
    cursor.executemany("""
        INSERT INTO transactions (date, description, amount, type, category, status, reference_number, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, financial_data)
    
    print(f"✅ Added {len(financial_data)} financial transactions")
    
    # 8. Shipments (Order fulfillment)
    shipments = [
        ("TRK-001-2024", "ORD-001", customer_ids[0], "Delivered", "Mumbai", "Delhi", "2024-10-25", "2024-10-27", 5.2, 450),
        ("TRK-002-2024", "ORD-002", customer_ids[1], "In Transit", "Mumbai", "Ahmedabad", "2024-10-28", None, 3.8, 320),
        ("TRK-003-2024", "ORD-003", customer_ids[2], "Processing", "Mumbai", "Pune", "2024-10-30", None, 2.5, 280),
        ("TRK-004-2024", "ORD-004", customer_ids[3], "Delivered", "Mumbai", "Bangalore", "2024-10-20", "2024-10-23", 4.1, 520),
        ("TRK-005-2024", "ORD-005", customer_ids[4], "Delivered", "Mumbai", "Jaipur", "2024-10-18", "2024-10-21", 6.3, 680)
    ]
    
    for tracking, order_id, customer_id, status, origin, dest, ship_date, delivery_date, weight, cost in shipments:
        cursor.execute("""
            INSERT INTO shipments (tracking_number, order_id, customer_id, status, origin, destination, ship_date, delivery_date, weight, shipping_cost, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (tracking, order_id, customer_id, status, origin, dest, ship_date, delivery_date, weight, cost, user_id))
    
    print("✅ Added 5 shipment records")
    
    # 9. Milestones (Business goals)
    milestones = [
        ("Monthly Revenue Target", "Achieve ₹5,00,000 monthly revenue", 500000, 0, "revenue", "2024-12-31", "active", "2024-10-01", None),
        ("Customer Base Growth", "Reach 50 active customers", 50, 8, "customers", "2025-03-31", "active", "2024-10-01", None),
        ("Inventory Turnover", "Improve inventory turnover to 8x per year", 8, 4, "inventory", "2025-06-30", "active", "2024-10-01", None),
        ("Profit Margin", "Maintain 25% profit margin", 25, 22, "custom", "2024-12-31", "active", "2024-10-01", None)
    ]
    
    for title, desc, target, current, unit, target_date, status, created, completed in milestones:
        cursor.execute("""
            INSERT INTO milestones (title, description, target_value, current_progress, unit, target_date, status, created_date, completed_date, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, desc, target, current, unit, target_date, status, created, completed, user_id))
    
    print("✅ Added 4 business milestones")
    
    # Update customer total purchases based on sales
    cursor.execute("""
        UPDATE customers 
        SET total_purchases = (
            SELECT COALESCE(SUM(revenue), 0) 
            FROM sales 
            WHERE sales.customer_id = customers.id
        ),
        last_purchase_date = (
            SELECT MAX(date) 
            FROM sales 
            WHERE sales.customer_id = customers.id
        )
        WHERE user_id = %s
    """, (user_id,))
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*70)
    print("🎉 SMB DATA POPULATION COMPLETED")
    print("="*70)
    print("📊 DATA SUMMARY:")
    print("• 5 Product Categories")
    print("• 5 Suppliers")
    print("• 15 Products (across Electronics, Office, Textiles, Hardware, Food)")
    print("• 8 Customers (B2B and B2C)")
    print(f"• {len(sales_data)} Sales Transactions (6 months)")
    print("• 5 Business Contracts")
    print(f"• {len(financial_data)} Financial Transactions")
    print("• 5 Shipments")
    print("• 4 Business Milestones")
    print("="*70)
    print("✅ Rakesh Singh's SMB business is ready for insights!")
    print("="*70)

if __name__ == "__main__":
    populate_smb_data()