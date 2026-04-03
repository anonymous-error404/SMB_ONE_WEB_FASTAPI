"""
AI-powered insights generator based on sales, inventory, and forecast data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def generate_key_insights(
    sales_df: pd.DataFrame = None,
    inventory_data: Dict = None,
    forecast_data: List[Dict] = None,
    performance_data: List[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Generate actionable insights based on multiple data sources
    Returns list of insights with type, message, severity, and details
    """
    insights = []
    
    try:
        # Insight 1: Forecast-based revenue projection
        if forecast_data and len(forecast_data) > 0:
            total_forecast = sum(day['predicted_revenue'] for day in forecast_data)
            avg_daily = total_forecast / len(forecast_data)
            monthly_projection = avg_daily * 30
            
            # Compare with historical average
            if sales_df is not None and not sales_df.empty:
                historical_avg = sales_df['revenue'].mean() if 'revenue' in sales_df.columns else avg_daily
                growth_rate = ((avg_daily - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0
                
                if growth_rate > 5:
                    insights.append({
                        'type': 'forecast',
                        'severity': 'positive',
                        'icon': 'TrendingUp',
                        'title': 'Strong Revenue Growth Predicted',
                        'message': f'AI forecast shows {growth_rate:.1f}% revenue increase over next 7 days. Projected monthly revenue: ₹{monthly_projection:,.0f}',
                        'action': 'Prepare inventory for increased demand'
                    })
                elif growth_rate < -5:
                    insights.append({
                        'type': 'forecast',
                        'severity': 'warning',
                        'icon': 'TrendingDown',
                        'title': 'Revenue Decline Expected',
                        'message': f'Forecast indicates {abs(growth_rate):.1f}% decrease. Review pricing and marketing strategies.',
                        'action': 'Consider promotional campaigns'
                    })
                else:
                    insights.append({
                        'type': 'forecast',
                        'severity': 'info',
                        'icon': 'Activity',
                        'title': 'Stable Revenue Trajectory',
                        'message': f'Next 7 days forecast: ₹{total_forecast:,.0f}. Growth rate: {growth_rate:.1f}%',
                        'action': 'Maintain current operational pace'
                    })
        
        # Insight 2: Inventory health analysis
        if inventory_data:
            low_stock = inventory_data.get('lowStockItems', 0)
            total_products = inventory_data.get('totalProducts', 0)
            stock_value = inventory_data.get('stockValue', 0)
            
            if low_stock > 0:
                low_stock_pct = (low_stock / total_products * 100) if total_products > 0 else 0
                
                if low_stock_pct > 20:
                    insights.append({
                        'type': 'inventory',
                        'severity': 'critical',
                        'icon': 'AlertTriangle',
                        'title': 'Critical Stock Shortage',
                        'message': f'{low_stock} products ({low_stock_pct:.0f}%) are below minimum levels. Risk of stockouts.',
                        'action': f'Urgent: Reorder {low_stock} items immediately'
                    })
                elif low_stock_pct > 10:
                    insights.append({
                        'type': 'inventory',
                        'severity': 'warning',
                        'icon': 'Package',
                        'title': 'Inventory Replenishment Needed',
                        'message': f'{low_stock} items need restocking. Current stock value: ₹{stock_value:,.0f}',
                        'action': 'Schedule reorder for low-stock items'
                    })
                else:
                    insights.append({
                        'type': 'inventory',
                        'severity': 'info',
                        'icon': 'Package',
                        'title': 'Healthy Inventory Levels',
                        'message': f'{low_stock} items need attention. Overall stock: ₹{stock_value:,.0f}',
                        'action': 'Monitor weekly, reorder as needed'
                    })
        
        # Insight 3: Sales performance trends
        if sales_df is not None and not sales_df.empty and 'date' in sales_df.columns:
            # Get recent sales (last 30 days vs previous 30 days)
            sales_df['date'] = pd.to_datetime(sales_df['date'])
            thirty_days_ago = datetime.now() - timedelta(days=30)
            sixty_days_ago = datetime.now() - timedelta(days=60)
            
            recent_sales = sales_df[sales_df['date'] >= thirty_days_ago]['revenue'].sum()
            previous_sales = sales_df[
                (sales_df['date'] >= sixty_days_ago) & 
                (sales_df['date'] < thirty_days_ago)
            ]['revenue'].sum()
            
            if previous_sales > 0:
                sales_growth = ((recent_sales - previous_sales) / previous_sales * 100)
                
                if sales_growth > 15:
                    insights.append({
                        'type': 'sales',
                        'severity': 'positive',
                        'icon': 'DollarSign',
                        'title': 'Exceptional Sales Performance',
                        'message': f'Last 30 days: ₹{recent_sales:,.0f} ({sales_growth:+.1f}% vs previous period)',
                        'action': 'Analyze winning products and replicate success'
                    })
                elif sales_growth < -10:
                    insights.append({
                        'type': 'sales',
                        'severity': 'warning',
                        'icon': 'TrendingDown',
                        'title': 'Sales Momentum Declining',
                        'message': f'Last 30 days: ₹{recent_sales:,.0f} ({sales_growth:.1f}% decline)',
                        'action': 'Review customer feedback and adjust strategy'
                    })
        
        # Insight 4: Best performing products
        if sales_df is not None and not sales_df.empty and 'product_name' in sales_df.columns:
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_df = sales_df[sales_df['date'] >= thirty_days_ago] if 'date' in sales_df.columns else sales_df
            
            if not recent_df.empty:
                top_products = recent_df.groupby('product_name')['revenue'].sum().nlargest(3)
                
                if len(top_products) > 0:
                    top_product = top_products.index[0]
                    top_revenue = top_products.values[0]
                    total_revenue = recent_df['revenue'].sum()
                    contribution_pct = (top_revenue / total_revenue * 100) if total_revenue > 0 else 0
                    
                    insights.append({
                        'type': 'product',
                        'severity': 'info',
                        'icon': 'Star',
                        'title': 'Top Revenue Generator',
                        'message': f'"{top_product}" drives {contribution_pct:.1f}% of revenue (₹{top_revenue:,.0f})',
                        'action': 'Ensure sufficient stock and consider bundling'
                    })
        
        # Insight 5: Performance metrics analysis
        if performance_data and len(performance_data) >= 2:
            latest = performance_data[-1]
            previous = performance_data[-2]
            
            profit_margin_latest = (latest['profit'] / latest['revenue'] * 100) if latest.get('revenue', 0) > 0 else 0
            profit_margin_prev = (previous['profit'] / previous['revenue'] * 100) if previous.get('revenue', 0) > 0 else 0
            
            margin_change = profit_margin_latest - profit_margin_prev
            
            if margin_change > 2:
                insights.append({
                    'type': 'profitability',
                    'severity': 'positive',
                    'icon': 'TrendingUp',
                    'title': 'Profit Margin Improvement',
                    'message': f'Margin increased to {profit_margin_latest:.1f}% ({margin_change:+.1f}pp). Costs under control.',
                    'action': 'Document successful cost optimization measures'
                })
            elif margin_change < -2:
                insights.append({
                    'type': 'profitability',
                    'severity': 'warning',
                    'icon': 'AlertCircle',
                    'title': 'Margin Compression Detected',
                    'message': f'Margin dropped to {profit_margin_latest:.1f}% ({margin_change:.1f}pp). Rising costs detected.',
                    'action': 'Review supplier pricing and operational efficiency'
                })
        
        # Insight 6: Weekend vs Weekday performance (if we have date data)
        if sales_df is not None and not sales_df.empty and 'date' in sales_df.columns:
            sales_df['weekday'] = pd.to_datetime(sales_df['date']).dt.dayofweek
            sales_df['is_weekend'] = sales_df['weekday'].isin([5, 6])
            
            weekend_avg = sales_df[sales_df['is_weekend']]['revenue'].mean()
            weekday_avg = sales_df[~sales_df['is_weekend']]['revenue'].mean()
            
            if weekend_avg > weekday_avg * 1.2:
                insights.append({
                    'type': 'pattern',
                    'severity': 'info',
                    'icon': 'Calendar',
                    'title': 'Weekend Sales Peak',
                    'message': f'Weekend sales {((weekend_avg/weekday_avg - 1) * 100):.0f}% higher than weekdays',
                    'action': 'Staff accordingly and run weekend promotions'
                })
            elif weekday_avg > weekend_avg * 1.2:
                insights.append({
                    'type': 'pattern',
                    'severity': 'info',
                    'icon': 'Calendar',
                    'title': 'Weekday Sales Dominance',
                    'message': f'Weekday sales {((weekday_avg/weekend_avg - 1) * 100):.0f}% higher than weekends',
                    'action': 'Focus marketing efforts on weekdays'
                })
        
        # If no insights generated, add a default one
        if len(insights) == 0:
            insights.append({
                'type': 'info',
                'severity': 'info',
                'icon': 'Activity',
                'title': 'Business Operating Normally',
                'message': 'All key metrics are within expected ranges across sales, inventory, and forecasting.',
                'action': 'Continue current strategies and monitor weekly'
            })
        
        # Return top 5 most relevant insights
        # Priority: critical > warning > positive > info
        severity_order = {'critical': 0, 'warning': 1, 'positive': 2, 'info': 3}
        insights.sort(key=lambda x: severity_order.get(x['severity'], 4))
        
        return insights[:5]
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Return a meaningful default insight even on error
        return [{
            'type': 'info',
            'severity': 'info',
            'icon': 'Activity',
            'title': 'Business Metrics Available',
            'message': 'Sales, inventory, and forecast data is being analyzed for actionable insights.',
            'action': 'Ensure all data sources are connected properly'
        }]
