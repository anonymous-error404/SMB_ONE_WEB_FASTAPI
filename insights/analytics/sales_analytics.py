import pandas as pd
import numpy as np
import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import date, timedelta
import logging
from functools import lru_cache
import warnings

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('insights.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dynamic configuration constants
ROUNDING_PRECISION = int(os.getenv('ROUNDING_PRECISION', '2'))
DEFAULT_LOOKBACK_DAYS = int(os.getenv('DEFAULT_LOOKBACK_DAYS', '30'))
DEFAULT_TOP_N_PRODUCTS = int(os.getenv('DEFAULT_TOP_N_PRODUCTS', '5'))

# --- CORE ANALYTICS FUNCTIONS ---

def _validate_input_data(df_transactions: Optional[pd.DataFrame], 
                        required_cols: List[str],
                        data_name: str = "transactions",
                        min_rows: int = 1) -> pd.DataFrame:
    """
    Enhanced validation function with dynamic parameters and data quality checks.
    
    Args:
        df_transactions: Input DataFrame to validate
        required_cols: List of required columns
        data_name: Name of the dataset for error messages
        min_rows: Minimum number of rows required
        
    Returns:
        Validated DataFrame
        
    Raises:
        ValueError: If validation fails
    """
    if df_transactions is None:
        raise ValueError(f"Input DataFrame '{data_name}' cannot be None.")
    
    if df_transactions.empty:
        raise ValueError(f"Input DataFrame '{data_name}' is empty.")
    
    if len(df_transactions) < min_rows:
        raise ValueError(f"Input DataFrame '{data_name}' has insufficient rows: {len(df_transactions)} < {min_rows}")
    
    missing_cols = [col for col in required_cols if col not in df_transactions.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in '{data_name}': {', '.join(missing_cols)}")
    
    # Log data quality metrics
    logger.info(f"{data_name} validation passed: {len(df_transactions)} rows, {len(df_transactions.columns)} columns")
    
    return df_transactions.copy()


def get_revenue_trends(df_transactions: Optional[pd.DataFrame],
                      lookback_days: int = DEFAULT_LOOKBACK_DAYS,
                      include_ytd: bool = True,
                      include_quarterly: bool = False) -> Dict[str, Any]:
    """
    Dynamic revenue trends analysis with configurable time periods and metrics.
    
    Args:
        df_transactions: DataFrame containing 'date' and 'revenue' columns
        lookback_days: Number of days to look back for YoY comparison
        include_ytd: Whether to include year-to-date metrics
        include_quarterly: Whether to include quarterly metrics
    
    Returns:
        Dictionary with calculated revenue metrics and growth rates
    """
    logger.info(f"Calculating revenue trends with {lookback_days} day lookback")
    
    df_transactions = _validate_input_data(df_transactions, ['date', 'revenue'], "revenue_trends", 30)

    # Ensure date column is the index and in datetime format
    df_transactions = df_transactions.set_index('date')
    df_transactions.index = pd.to_datetime(df_transactions.index)
    
    today = date.today()
    results = {}
    
    try:
        # 1. MoM (Month-over-Month) Analysis
        last_day_of_prev_month = pd.to_datetime(today.replace(day=1)) - timedelta(days=1)
        start_of_lcm = last_day_of_prev_month.to_period('M').start_time
        lcm_revenue = df_transactions.loc[start_of_lcm:last_day_of_prev_month, 'revenue'].sum()
        
        start_of_mblcm = (start_of_lcm - pd.DateOffset(months=1))
        end_of_mblcm = (start_of_lcm - timedelta(days=1))
        mblcm_revenue = df_transactions.loc[start_of_mblcm:end_of_mblcm, 'revenue'].sum()

        mom_growth = ((lcm_revenue - mblcm_revenue) / mblcm_revenue) if mblcm_revenue > 0 else 0
        
        results.update({
            "lcm_revenue": round(lcm_revenue, ROUNDING_PRECISION),
            "mblcm_revenue": round(mblcm_revenue, ROUNDING_PRECISION),
            "mom_growth_percent": f"{mom_growth * 100:.{ROUNDING_PRECISION}f}%",
            "mom_growth_value": round(lcm_revenue - mblcm_revenue, ROUNDING_PRECISION)
        })
        
        # 2. Year-over-Year Growth with dynamic lookback
        last_period_revenue = df_transactions[
            df_transactions.index.date >= (today - timedelta(days=lookback_days))
        ]['revenue'].sum()
        
        same_period_last_year = df_transactions[
            (df_transactions.index.date >= (today - timedelta(days=365 + lookback_days))) & 
            (df_transactions.index.date < (today - timedelta(days=365)))
        ]['revenue'].sum()
        
        yoy_growth = ((last_period_revenue - same_period_last_year) / same_period_last_year) if same_period_last_year > 0 else 0
        
        results.update({
            "last_period_revenue": round(last_period_revenue, ROUNDING_PRECISION),
            "same_period_last_year": round(same_period_last_year, ROUNDING_PRECISION),
            "yoy_growth_percent": f"{yoy_growth * 100:.{ROUNDING_PRECISION}f}%",
            "yoy_growth_value": round(last_period_revenue - same_period_last_year, ROUNDING_PRECISION)
        })
        
        # 3. Year-to-Date (YTD) Revenue
        if include_ytd:
            ytd_revenue = df_transactions[df_transactions.index.year == today.year]['revenue'].sum()
            results["ytd_revenue"] = round(ytd_revenue, ROUNDING_PRECISION)
        
        # 4. Quarterly Analysis (if requested)
        if include_quarterly:
            current_quarter = pd.Timestamp(today).quarter
            qtd_revenue = df_transactions[
                (df_transactions.index.year == today.year) & 
                (df_transactions.index.quarter == current_quarter)
            ]['revenue'].sum()
            results["qtd_revenue"] = round(qtd_revenue, ROUNDING_PRECISION)
        
        # Add metadata
        results.update({
            "analysis_date": today.strftime('%Y-%m-%d'),
            "lookback_days": lookback_days,
            "data_period": f"{df_transactions.index.min().strftime('%Y-%m-%d')} to {df_transactions.index.max().strftime('%Y-%m-%d')}"
        })
        
        logger.info("Revenue trends calculation completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Error calculating revenue trends: {e}")
        raise ValueError(f"Revenue trends calculation failed: {e}")

def get_product_performance(df_transactions: Optional[pd.DataFrame],
                           top_n: int = DEFAULT_TOP_N_PRODUCTS,
                           sort_by: str = 'revenue',
                           include_velocity: bool = True,
                           include_margins: bool = True,
                           min_transactions: int = 1) -> Dict[str, Any]:
    """
    Dynamic product performance analysis with configurable metrics and filters.
    
    Args:
        df_transactions: DataFrame containing product sales data
        top_n: Number of top/bottom products to return
        sort_by: Metric to sort by ('revenue', 'profit', 'quantity', 'margin')
        include_velocity: Whether to calculate sales velocity
        include_margins: Whether to calculate profit margins
        min_transactions: Minimum number of transactions for a product to be included
        
    Returns:
        Dictionary with product performance metrics and rankings
    """
    logger.info(f"Analyzing product performance with top_n={top_n}, sort_by={sort_by}")
    
    required_cols = ['date', 'product_name', 'revenue']
    if include_margins:
        required_cols.extend(['profit'])
    if include_velocity:
        required_cols.append('quantity')
    
    df_transactions = _validate_input_data(df_transactions, required_cols, "product_performance", 10)

    try:
        # 1. Filter products with minimum transaction threshold
        product_transaction_counts = df_transactions.groupby('product_name').size()
        valid_products = product_transaction_counts[product_transaction_counts >= min_transactions].index
        df_filtered = df_transactions[df_transactions['product_name'].isin(valid_products)]
        
        if df_filtered.empty:
            logger.warning(f"No products meet minimum transaction threshold of {min_transactions}")
            return {"top_products": [], "bottom_products": [], "summary": {}}
        
        # 2. Aggregate performance by product
        agg_dict = {
            'total_revenue': ('revenue', 'sum'),
            'avg_revenue': ('revenue', 'mean'),
            'transaction_count': ('revenue', 'count')
        }
        
        if include_margins and 'profit' in df_filtered.columns:
            agg_dict.update({
                'total_profit': ('profit', 'sum'),
                'avg_profit': ('profit', 'mean')
            })
        
        if include_velocity and 'quantity' in df_filtered.columns:
            agg_dict['total_quantity'] = ('quantity', 'sum')
        
        product_summary = df_filtered.groupby('product_name').agg(agg_dict).reset_index()
        
        # 3. Calculate derived metrics
        if include_margins and 'total_profit' in product_summary.columns:
            product_summary['profit_margin'] = (
                product_summary['total_profit'] / product_summary['total_revenue']
            ).fillna(0).round(ROUNDING_PRECISION)
        
        if include_velocity and 'total_quantity' in product_summary.columns:
            # Calculate sales velocity (units per day)
            active_days = df_filtered.groupby('product_name')['date'].nunique()
            product_summary = product_summary.set_index('product_name')
            product_summary['sales_velocity_per_day'] = (
                product_summary['total_quantity'] / active_days
            ).fillna(0).round(ROUNDING_PRECISION)
            product_summary = product_summary.reset_index()
        
        # 4. Sort by specified metric
        valid_sort_columns = {
            'revenue': 'total_revenue',
            'profit': 'total_profit',
            'quantity': 'total_quantity',
            'margin': 'profit_margin'
        }
        
        sort_column = valid_sort_columns.get(sort_by, 'total_revenue')
        if sort_column not in product_summary.columns:
            logger.warning(f"Sort column '{sort_column}' not available, using 'total_revenue'")
            sort_column = 'total_revenue'
        
        # 5. Get top and bottom performers
        top_performers = product_summary.sort_values(by=sort_column, ascending=False).head(top_n)
        bottom_performers = product_summary.sort_values(by=sort_column, ascending=True).head(top_n)
        
        # 6. Format output
        def format_output_dict(df: pd.DataFrame) -> List[Dict[str, Any]]:
            output_cols = ['product_name', 'total_revenue', 'transaction_count']
            if include_margins and 'profit_margin' in df.columns:
                output_cols.append('profit_margin')
            if include_velocity and 'sales_velocity_per_day' in df.columns:
                output_cols.append('sales_velocity_per_day')
            
            return df[output_cols].round(ROUNDING_PRECISION).to_dict('records')
        
        # 7. Calculate summary statistics
        summary_stats = {
            "total_products": len(product_summary),
            "total_revenue": round(product_summary['total_revenue'].sum(), ROUNDING_PRECISION),
            "avg_revenue_per_product": round(product_summary['total_revenue'].mean(), ROUNDING_PRECISION),
            "sort_metric": sort_by
        }
        
        if include_margins and 'total_profit' in product_summary.columns:
            summary_stats.update({
                "total_profit": round(product_summary['total_profit'].sum(), ROUNDING_PRECISION),
                "avg_profit_margin": round(product_summary['profit_margin'].mean(), ROUNDING_PRECISION)
            })
        
        result = {
            "top_products": format_output_dict(top_performers),
            "bottom_products": format_output_dict(bottom_performers),
            "summary": summary_stats,
            "metric_definitions": {
                "sales_velocity": "Average units sold per day since product was first active",
                "profit_margin": "Total profit divided by total revenue",
                "transaction_count": "Number of individual transactions"
            }
        }
        
        logger.info(f"Product performance analysis completed: {len(product_summary)} products analyzed")
        return result
        
    except Exception as e:
        logger.error(f"Error in product performance analysis: {e}")
        raise ValueError(f"Product performance analysis failed: {e}")


def get_customer_segmentation(df_transactions: Optional[pd.DataFrame],
                             segment_column: str = 'customer_segment',
                             include_aov: bool = True,
                             include_frequency: bool = True,
                             min_segment_size: int = 1) -> Dict[str, Any]:
    """
    Dynamic customer segmentation analysis with configurable metrics and filters.
    
    Args:
        df_transactions: DataFrame containing customer transaction data
        segment_column: Column name to use for segmentation
        include_aov: Whether to calculate average order value
        include_frequency: Whether to calculate transaction frequency
        min_segment_size: Minimum number of transactions per segment
        
    Returns:
        Dictionary with segment analysis and summary statistics
    """
    logger.info(f"Analyzing customer segmentation using column: {segment_column}")
    
    required_cols = ['date', 'revenue', segment_column]
    df_transactions = _validate_input_data(df_transactions, required_cols, "customer_segmentation", 10)

    try:
        # 1. Filter segments with minimum size
        segment_counts = df_transactions.groupby(segment_column).size()
        valid_segments = segment_counts[segment_counts >= min_segment_size].index
        df_filtered = df_transactions[df_transactions[segment_column].isin(valid_segments)]
        
        if df_filtered.empty:
            logger.warning(f"No segments meet minimum size threshold of {min_segment_size}")
            return {"segments": [], "summary": {}}
        
        # 2. Calculate segment metrics
        agg_dict = {
            'total_revenue': ('revenue', 'sum'),
            'transaction_count': ('revenue', 'count'),
            'unique_customers': (segment_column, 'nunique') if 'customer_id' in df_filtered.columns else None
        }
        
        if include_aov:
            agg_dict['average_order_value'] = ('revenue', 'mean')
            agg_dict['median_order_value'] = ('revenue', 'median')
        
        # Remove None values from agg_dict
        agg_dict = {k: v for k, v in agg_dict.items() if v is not None}
        
        segment_summary = df_filtered.groupby(segment_column).agg(agg_dict).reset_index()
        
        # 3. Calculate derived metrics
        total_revenue = segment_summary['total_revenue'].sum()
        segment_summary['revenue_share_percent'] = (
            segment_summary['total_revenue'] / total_revenue * 100
        ).round(1)
        
        if include_frequency:
            # Calculate average transactions per customer (if customer_id available)
            if 'unique_customers' in segment_summary.columns:
                segment_summary['avg_transactions_per_customer'] = (
                    segment_summary['transaction_count'] / segment_summary['unique_customers']
                ).round(2)
        
        # 4. Sort by revenue (descending)
        segment_summary = segment_summary.sort_values(by='total_revenue', ascending=False)
        
        # 5. Calculate summary statistics
        summary_stats = {
            "total_segments": len(segment_summary),
            "total_revenue": round(total_revenue, ROUNDING_PRECISION),
            "total_transactions": segment_summary['transaction_count'].sum(),
            "largest_segment": segment_summary.iloc[0][segment_column] if len(segment_summary) > 0 else None,
            "largest_segment_share": round(segment_summary.iloc[0]['revenue_share_percent'], 1) if len(segment_summary) > 0 else 0
        }
        
        if include_aov:
            summary_stats.update({
                "overall_aov": round(df_filtered['revenue'].mean(), ROUNDING_PRECISION),
                "highest_aov_segment": segment_summary.iloc[0][segment_column] if len(segment_summary) > 0 else None
            })
        
        result = {
            "segments": segment_summary.round(ROUNDING_PRECISION).to_dict('records'),
            "summary": summary_stats,
            "segment_column": segment_column,
            "analysis_date": date.today().strftime('%Y-%m-%d')
        }
        
        logger.info(f"Customer segmentation analysis completed: {len(segment_summary)} segments analyzed")
        return result
        
    except Exception as e:
        logger.error(f"Error in customer segmentation analysis: {e}")
        raise ValueError(f"Customer segmentation analysis failed: {e}")
