import pandas as pd
from typing import Dict, Any, List, Optional
import logging

# Set up basic logging
logger = logging.getLogger(__name__)

# Deployment-grade constant inherited from sales_analytics
ROUNDING_PRECISION = 2
DAYS_IN_YEAR = 365

# --- CORE ANALYTICS FUNCTIONS ---

def _validate_input_data(df: Optional[pd.DataFrame], df_name: str, required_cols: List[str]):
    """
    Helper function to validate that the required DataFrame is present and 
    contains all necessary columns. Raises ValueError on failure.
    """
    if df is None or df.empty:
        raise ValueError(
            f"Input DataFrame '{df_name}' cannot be None or empty. "
            "Please ensure data is loaded and passed from data_processor."
        )
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in '{df_name}': {', '.join(missing_cols)}")


def get_inventory_turnover(df_sales: pd.DataFrame, df_stock_snapshot: pd.DataFrame, lookback_days: int = 90) -> Dict[str, Any]:
    """
    Calculates the Inventory Turnover Rate for the entire inventory over a specific period.
    
    Turnover Rate = (Cost of Goods Sold / Average Inventory Value)
    
    Args:
        df_sales: DataFrame with historical sales data, including 'date' and 'cogs'.
        df_stock_snapshot: DataFrame with current stock, including 'product_name', 'current_stock_units', 'unit_cost'.
        lookback_days: The number of recent days to consider for calculating COGS.
        
    Returns:
        A dictionary containing the calculated turnover rate and related metrics.
    """
    _validate_input_data(df_sales, 'df_sales', ['date', 'cogs'])
    _validate_input_data(df_stock_snapshot, 'df_stock_snapshot', ['product_name', 'current_stock_units', 'unit_cost'])

    df_sales['date'] = pd.to_datetime(df_sales['date'])
    
    # 1. Calculate COGS for the Lookback Period
    recent_sales = df_sales[df_sales['date'] >= (pd.Timestamp('today') - pd.Timedelta(days=lookback_days))]
    total_cogs_period = recent_sales['cogs'].sum()
    
    # 2. Estimate Current Inventory Value
    # Using the current snapshot as a proxy for "Average Inventory" since detailed historical inventory records are complex.
    df_stock_snapshot['current_value'] = df_stock_snapshot['current_stock_units'] * df_stock_snapshot['unit_cost']
    current_inventory_value = df_stock_snapshot['current_value'].sum()

    # 3. Calculate Turnover Rate
    if current_inventory_value > 0 and total_cogs_period > 0:
        # Annualize COGS for better comparison
        annualized_cogs = total_cogs_period * (DAYS_IN_YEAR / lookback_days)
        turnover_rate = annualized_cogs / current_inventory_value
    else:
        turnover_rate = 0

    return {
        "turnover_rate_annualized": round(turnover_rate, ROUNDING_PRECISION),
        "total_cogs_period": round(total_cogs_period, ROUNDING_PRECISION),
        "current_inventory_value": round(current_inventory_value, ROUNDING_PRECISION),
        "lookback_days": lookback_days,
        "analysis_note": "Turnover rate calculated based on annualized COGS from lookback period."
    }


def get_slow_moving_alerts(df_sales: pd.DataFrame, df_stock_snapshot: pd.DataFrame, sales_lookback_days: int = 90, slow_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Identifies products considered 'slow-moving' based on a low Stock-to-Sales ratio.
    
    Args:
        df_sales: DataFrame with historical sales data, including 'date' and 'quantity'.
        df_stock_snapshot: DataFrame with current stock, including 'product_name' and 'current_stock_units'.
        sales_lookback_days: Period used to determine average daily sales rate.
        slow_threshold: If Stock-to-Sales Ratio is greater than this, trigger an alert (e.g., 0.5 means more than 15 days of stock).
        
    Returns:
        A list of dictionaries for products flagged as slow-moving.
    """
    _validate_input_data(df_sales, 'df_sales', ['date', 'product_name', 'quantity'])
    _validate_input_data(df_stock_snapshot, 'df_stock_snapshot', ['product_name', 'current_stock_units'])

    # 1. Calculate Average Daily Sales (Velocity) per Product
    df_sales['date'] = pd.to_datetime(df_sales['date'])
    
    # Aggregate quantity sold over the lookback period
    recent_sales = df_sales[df_sales['date'] >= (pd.Timestamp('today') - pd.Timedelta(days=sales_lookback_days))]
    product_sales_sum = recent_sales.groupby('product_name')['quantity'].sum().reset_index(name='total_quantity_sold')
    
    # Merge stock and sales data
    df_merged = pd.merge(df_stock_snapshot, product_sales_sum, on='product_name', how='left').fillna(0)
    
    # Calculate daily sales rate
    df_merged['daily_sales_rate'] = df_merged['total_quantity_sold'] / sales_lookback_days
    
    # 2. Calculate Days of Stock Remaining (Days-on-Hand)
    # Days-on-Hand = Current Stock / Daily Sales Rate
    # Use 1 day as the divisor if sales rate is zero to prevent division by zero, but ensure the alert logic handles this.
    
    # Handle zero division: If daily sales rate is 0, Days-on-Hand is effectively infinite (or max lookback days)
    df_merged['days_on_hand'] = np.where(
        df_merged['daily_sales_rate'] > 0,
        df_merged['current_stock_units'] / df_merged['daily_sales_rate'],
        sales_lookback_days * 2 # Set a high number for truly non-moving stock
    )
    
    # 3. Apply Alert Threshold
    # Alert if a product can last longer than 2 * lookback days (truly slow) OR
    # if days_on_hand is above a certain hard limit (e.g., 60 days)
    
    days_on_hand_threshold = sales_lookback_days * slow_threshold
    
    slow_movers = df_merged[df_merged['days_on_hand'] > days_on_hand_threshold]
    
    # 4. Format Output
    output_cols = ['product_name', 'current_stock_units', 'total_quantity_sold', 'daily_sales_rate', 'days_on_hand']
    slow_movers = slow_movers[output_cols].sort_values(by='days_on_hand', ascending=False)
    
    return slow_movers.round(ROUNDING_PRECISION).to_dict('records')


def get_stock_recommendations(df_stock_snapshot: pd.DataFrame, df_forecast: pd.DataFrame, safety_stock_multiplier: float = 1.2) -> List[Dict[str, Any]]:
    """
    Generates reorder and overstock recommendations based on safety stock and short-term forecast.
    
    Args:
        df_stock_snapshot: DataFrame with 'product_name', 'current_stock_units', 'min_safety_stock'.
        df_forecast: DataFrame with 'product_name' and 'forecast_quantity_30_days' (30-day demand).
        safety_stock_multiplier: Multiplier for safety stock (e.g., 1.2 means 20% buffer).
        
    Returns:
        A list of dictionaries for products needing immediate attention.
    """
    _validate_input_data(df_stock_snapshot, 'df_stock_snapshot', ['product_name', 'current_stock_units', 'min_safety_stock'])
    _validate_input_data(df_forecast, 'df_forecast', ['product_name', 'forecast_quantity_30_days'])

    # Merge stock and 30-day forecast
    df_merged = pd.merge(df_stock_snapshot, df_forecast, on='product_name', how='inner')
    
    # Calculate Reorder Point: (30-Day Forecast) + (Safety Stock * Multiplier)
    df_merged['required_stock'] = (df_merged['min_safety_stock'] * safety_stock_multiplier)
    
    # Add buffer for the next 30 days of expected demand
    df_merged['required_stock_for_demand'] = df_merged['required_stock'] + df_merged['forecast_quantity_30_days']
    
    # Calculate stock difference
    df_merged['stock_delta'] = df_merged['current_stock_units'] - df_merged['required_stock_for_demand']
    
    # Identify key recommendations
    recommendations = []
    
    # 1. Reorder Alert (Current stock is below safety stock adjusted for demand)
    reorder_alerts = df_merged[df_merged['stock_delta'] < 0]
    for _, row in reorder_alerts.iterrows():
        recommendations.append({
            "product_name": row['product_name'],
            "type": "REORDER_ALERT",
            "message": f"Critical: Need {abs(row['stock_delta']):.{ROUNDING_PRECISION}f} units to meet 30-day forecast and safety stock.",
            "deficit_units": abs(row['stock_delta'])
        })
        
    # 2. Overstock Alert (Current stock significantly exceeds 60 days of required stock + safety stock)
    # Define overstock as stock_delta > 2 * forecast_quantity_30_days
    overstock_alerts = df_merged[df_merged['stock_delta'] > df_merged['forecast_quantity_30_days']]
    for _, row in overstock_alerts.iterrows():
        recommendations.append({
            "product_name": row['product_name'],
            "type": "OVERSTOCK_ALERT",
            "message": f"High: Excess stock of {row['stock_delta']:.{ROUNDING_PRECISION}f} units beyond 30-day needs. Consider promotional offers.",
            "excess_units": row['stock_delta']
        })

    return recommendations
