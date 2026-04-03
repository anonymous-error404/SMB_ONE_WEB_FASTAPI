import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
import logging

# Set up basic logging
logger = logging.getLogger(__name__)

# Deployment-grade constants for consistency
ROUNDING_PRECISION = 2
DAYS_IN_YEAR = 365

# --- HELPER FUNCTION ---

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

# --- CORE ANALYTICS FUNCTIONS ---

def get_cash_flow_prediction(df_revenue_forecast: pd.DataFrame, df_expense_forecast: pd.DataFrame) -> Dict[str, Any]:
    """
    Predicts net cash flow for the next 30, 60, and 90 days by combining revenue and expense forecasts.
    
    Args:
        df_revenue_forecast: DataFrame with 'date' and 'forecast_revenue'.
        df_expense_forecast: DataFrame with 'date' and 'forecast_expense'.
        
    Returns:
        A dictionary with predicted cash inflows, outflows, and net flow for key horizons.
    """
    _validate_input_data(df_revenue_forecast, 'df_revenue_forecast', ['date', 'forecast_revenue'])
    _validate_input_data(df_expense_forecast, 'df_expense_forecast', ['date', 'forecast_expense'])

    # Ensure dates are uniform and set as index
    df_revenue_forecast = df_revenue_forecast.set_index(pd.to_datetime(df_revenue_forecast['date']))
    df_expense_forecast = df_expense_forecast.set_index(pd.to_datetime(df_expense_forecast['date']))
    
    # Merge forecasts on date index
    df_merged = pd.merge(
        df_revenue_forecast[['forecast_revenue']],
        df_expense_forecast[['forecast_expense']],
        left_index=True, right_index=True, how='outer'
    ).fillna(0)
    
    df_merged['net_flow'] = df_merged['forecast_revenue'] - df_merged['forecast_expense']
    
    # Helper to calculate metrics for a specific number of days
    def calculate_horizon(days: int) -> Dict[str, float]:
        end_date = pd.Timestamp('today') + pd.Timedelta(days=days)
        # Use only forecast dates up to the end date
        period_data = df_merged[df_merged.index <= end_date] 
        
        inflow = period_data['forecast_revenue'].sum()
        outflow = period_data['forecast_expense'].sum()
        net_flow = period_data['net_flow'].sum()
        
        return {
            "inflow": round(inflow, ROUNDING_PRECISION),
            "outflow": round(outflow, ROUNDING_PRECISION),
            "net_flow": round(net_flow, ROUNDING_PRECISION)
        }

    forecast_data = {}
    forecast_data["30_day"] = calculate_horizon(30)
    forecast_data["60_day"] = calculate_horizon(60)
    forecast_data["90_day"] = calculate_horizon(90)
    
    return forecast_data


def get_expense_breakdown(df_expenses: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes and categorizes historical expenses, calculating a total and period-over-period change.
    
    Args:
        df_expenses: DataFrame containing 'date', 'amount', and 'category'.
        
    Returns:
        A dictionary with total expenses, categorical breakdown, and MoM change based on last two complete months.
    """
    _validate_input_data(df_expenses, 'df_expenses', ['date', 'amount', 'category'])
    
    df_expenses['date'] = pd.to_datetime(df_expenses['date'])
    today = pd.Timestamp('today').normalize()
    
    # 1. Define Comparison Periods (Last Complete Month vs. Month Before) for stable reporting
    last_day_prev_month = pd.to_datetime(today.replace(day=1)) - timedelta(days=1)
    
    # Last Complete Month (LCM)
    start_of_lcm = last_day_prev_month.to_period('M').start_time
    lcm_expenses = df_expenses[(df_expenses['date'] >= start_of_lcm) & (df_expenses['date'] <= last_day_prev_month)]
    
    # Month Before Last Complete Month (MBLCM)
    start_of_mblcm = (start_of_lcm - pd.DateOffset(months=1))
    end_of_mblcm = (start_of_lcm - timedelta(days=1))
    mblcm_expenses = df_expenses[(df_expenses['date'] >= start_of_mblcm) & (df_expenses['date'] <= end_of_mblcm)]
    
    total_lcm = lcm_expenses['amount'].sum()
    total_mblcm = mblcm_expenses['amount'].sum()

    # 2. Calculate MoM Change
    mom_change_pct = ((total_lcm - total_mblcm) / total_mblcm) if total_mblcm > 0 else 0
    
    # 3. Categorical Breakdown (using LCM)
    if total_lcm > 0:
        category_breakdown = lcm_expenses.groupby('category')['amount'].sum().reset_index(name='total_amount')
        category_breakdown['share_percent'] = (category_breakdown['total_amount'] / total_lcm * 100).round(1)
        category_breakdown = category_breakdown.sort_values(by='total_amount', ascending=False)
        category_list = category_breakdown.round(ROUNDING_PRECISION).to_dict('records')
    else:
        category_list = []
    
    return {
        "lcm_total_expense": round(total_lcm, ROUNDING_PRECISION),
        "mom_change_percent": f"{mom_change_pct * 100:.{ROUNDING_PRECISION}f}%",
        "category_breakdown": category_list
    }


def get_receivables_aging(df_invoices: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes outstanding invoices and groups them into aging buckets (e.g., 0-30, 31-60 days past due).
    
    Args:
        df_invoices: DataFrame containing 'due_date', 'status' (e.g., 'Outstanding'), and 'amount'.
        
    Returns:
        A dictionary with the total outstanding amount and amounts for each aging bucket.
    """
    _validate_input_data(df_invoices, 'df_invoices', ['due_date', 'status', 'amount'])
    
    df_invoices['due_date'] = pd.to_datetime(df_invoices['due_date'])
    today = pd.Timestamp('today').normalize()
    
    # Filter for only outstanding invoices
    outstanding_invoices = df_invoices[df_invoices['status'].isin(['Outstanding', 'Partial'])].copy()
    
    if outstanding_invoices.empty:
        return {
            "total_outstanding": 0.0,
            "aging_buckets": []
        }

    # Calculate days past due (or days until due if negative)
    outstanding_invoices['days_past_due'] = (today - outstanding_invoices['due_date']).dt.days
    
    # Define standard aging buckets (in days past due)
    bins = [-np.inf, 0, 30, 60, 90, np.inf]
    labels = ['Not Due Yet', '1-30 Days Past Due', '31-60 Days Past Due', '61-90 Days Past Due', '> 90 Days Past Due']
    
    outstanding_invoices['aging_bucket'] = pd.cut(
        outstanding_invoices['days_past_due'], 
        bins=bins, 
        labels=labels, 
        right=True,
        include_lowest=True
    )
    
    aging_summary = outstanding_invoices.groupby('aging_bucket')['amount'].sum().reset_index(name='amount')
    
    # Convert Categorical back to String for clean JSON output
    aging_summary['aging_bucket'] = aging_summary['aging_bucket'].astype(str)
    
    total_outstanding = outstanding_invoices['amount'].sum()

    return {
        "total_outstanding": round(total_outstanding, ROUNDING_PRECISION),
        "aging_buckets": aging_summary.round(ROUNDING_PRECISION).to_dict('records')
    }


def get_payment_patterns(df_invoices: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates the Days Sales Outstanding (DSO) to measure the average time customers take to pay.
    
    Args:
        df_invoices: DataFrame containing 'issue_date', 'paid_date', and 'status' (e.g., 'Paid').
        
    Returns:
        A dictionary containing the calculated DSO and a payment speed breakdown.
    """
    _validate_input_data(df_invoices, 'df_invoices', ['issue_date', 'paid_date', 'status'])
    
    df_invoices['issue_date'] = pd.to_datetime(df_invoices['issue_date'])
    df_invoices['paid_date'] = pd.to_datetime(df_invoices['paid_date'])
    
    # Filter for only paid invoices
    paid_invoices = df_invoices[df_invoices['status'] == 'Paid'].copy()
    
    if paid_invoices.empty:
        return {
            "days_sales_outstanding_dso": 0,
            "payment_speed_breakdown": [],
            "analysis_note": "No paid invoices found for DSO calculation."
        }
        
    # Calculate days to pay
    paid_invoices['days_to_pay'] = (paid_invoices['paid_date'] - paid_invoices['issue_date']).dt.days
    
    # Clean data: Filter out payment anomalies where paid_date is before issue_date
    paid_invoices = paid_invoices[paid_invoices['days_to_pay'] >= 0]
    
    # Calculate average Days Sales Outstanding (DSO)
    average_dso = paid_invoices['days_to_pay'].mean()
    
    # Calculate Payment Breakdown (e.g., Percentage of invoices paid in <30 days)
    # Define time buckets based on payment terms
    payment_summary = paid_invoices.groupby(
        pd.cut(
            paid_invoices['days_to_pay'],
            bins=[0, 30, 60, 90, np.inf],
            labels=['< 30 Days', '31-60 Days', '61-90 Days', '> 90 Days'],
            right=False, # Interval is [low, high)
            include_lowest=True
        )
    )['issue_date'].count().reset_index(name='count')
    
    total_paid_invoices = len(paid_invoices)
    payment_summary['share_percent'] = (payment_summary['count'] / total_paid_invoices * 100).round(1)
    
    # Rename and clean up for JSON output
    payment_summary = payment_summary.rename(columns={'issue_date': 'payment_speed'})
    payment_summary['payment_speed'] = payment_summary['payment_speed'].astype(str)
    
    return {
        "days_sales_outstanding_dso": round(average_dso, ROUNDING_PRECISION),
        "payment_speed_breakdown": payment_summary.to_dict('records')
    }
