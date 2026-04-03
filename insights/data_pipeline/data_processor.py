import pandas as pd
import numpy as np
import holidays
import os
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from darts import TimeSeries
import logging
from darts.utils.timeseries_generation import datetime_attribute_timeseries
from datetime import datetime, timedelta
import warnings
from functools import lru_cache

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

class DataProcessor:
    """
    A deployment-grade class responsible for loading, cleaning, and feature-engineering 
    data required by the Analytics Modules and the Darts Forecasting Engine.
    
    In a live environment, the load methods would interact with SQLAlchemy/asyncpg 
    to fetch data from the database. Here, they are abstracted to accept DataFrames.
    """
    
    def __init__(self, 
                 country: str = 'IN', 
                 forecast_days: int = 90,
                 config_file: Optional[str] = None,
                 enable_caching: bool = True,
                 log_level: str = 'INFO'):
        """
        Initializes processor with dynamic configuration.
        
        Args:
            country: Country code for holiday calendar
            forecast_days: Number of days to forecast
            config_file: Path to JSON configuration file
            enable_caching: Enable LRU caching for expensive operations
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.country = country
        self.forecast_days = forecast_days
        self.enable_caching = enable_caching
        self.config = self._load_config(config_file)
        
        # Set logging level dynamically
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Initialize holiday calendar with caching
        self.indian_holidays = self._get_holidays()
        
        # Dynamic configuration parameters
        self.date_columns = self.config.get('date_columns', ['date', 'created_at', 'timestamp'])
        self.required_columns = self.config.get('required_columns', {})
        self.data_validation_rules = self.config.get('data_validation', {})
        
        logger.info(f"DataProcessor initialized for {country} with {forecast_days} forecast days")
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            'date_columns': ['date', 'created_at', 'timestamp'],
            'required_columns': {
                'sales': ['date', 'revenue'],
                'inventory': ['product_name', 'current_stock_units'],
                'financial': ['date', 'amount']
            },
            'data_validation': {
                'min_date_range_days': 30,
                'max_missing_percentage': 10,
                'outlier_threshold': 3.0
            },
            'forecasting': {
                'min_data_points': 30,
                'seasonality_periods': [7, 30, 365],
                'trend_components': True
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Configuration loaded from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}. Using defaults.")
        
        return default_config
    
    @lru_cache(maxsize=1)
    def _get_holidays(self) -> Dict[datetime.date, str]:
        """Get holidays with caching for performance."""
        try:
            # For India, use without subdivision or use specific state codes
            if self.country == 'IN':
                return holidays.India()
            else:
                return holidays.country_holidays(self.country)
        except Exception as e:
            logger.warning(f"Failed to load holidays for {self.country}: {e}")
            return {}
        
    # --- ABSTRACT DATA LOADING METHODS ---
    
    def load_analytics_data(self, 
                           sales_data: pd.DataFrame, 
                           inventory_data: pd.DataFrame, 
                           financial_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Dynamic method to load and validate all necessary DataFrames for analytics modules.
        
        Args:
            sales_data: Raw DataFrame for sales/revenue/profit.
            inventory_data: Raw DataFrame for stock levels/costs.
            financial_data: Raw DataFrame for expenses/invoices/receivables.
            
        Returns:
            A dictionary containing all validated and cleaned DataFrames.
            
        Raises:
            ValueError: If data validation fails
        """
        logger.info("Starting data loading and validation process")
        
        # Validate and clean each dataset
        validated_data = {}
        
        try:
            validated_data["sales"] = self._validate_and_clean_dataframe(
                sales_data, "sales", self.required_columns.get('sales', ['date', 'revenue'])
            )
            validated_data["inventory"] = self._validate_and_clean_dataframe(
                inventory_data, "inventory", self.required_columns.get('inventory', ['product_name', 'current_stock_units'])
            )
            validated_data["financial"] = self._validate_and_clean_dataframe(
                financial_data, "financial", self.required_columns.get('financial', ['date', 'amount'])
            )
            
            logger.info("All datasets validated and cleaned successfully")
            return validated_data
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            raise ValueError(f"Data loading failed: {e}")
    
    def _validate_and_clean_dataframe(self, 
                                    df: pd.DataFrame, 
                                    data_type: str, 
                                    required_cols: List[str]) -> pd.DataFrame:
        """
        Validate and clean a DataFrame with dynamic rules.
        
        Args:
            df: Input DataFrame
            data_type: Type of data (sales, inventory, financial)
            required_cols: Required columns for this data type
            
        Returns:
            Cleaned and validated DataFrame
        """
        if df is None or df.empty:
            raise ValueError(f"{data_type} DataFrame is empty or None")
        
        # Check required columns
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in {data_type} data: {missing_cols}")
        
        # Create a copy to avoid modifying original
        cleaned_df = df.copy()
        
        # Auto-detect and convert date columns
        cleaned_df = self._auto_convert_dates(cleaned_df)
        
        # Handle missing values based on data type
        cleaned_df = self._handle_missing_values(cleaned_df, data_type)
        
        # Remove outliers if configured
        if self.data_validation_rules.get('remove_outliers', False):
            cleaned_df = self._remove_outliers(cleaned_df, data_type)
        
        # Log data quality metrics
        self._log_data_quality(cleaned_df, data_type)
        
        return cleaned_df
    
    def _auto_convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-detect and convert date columns."""
        for col in df.columns:
            if col.lower() in [dc.lower() for dc in self.date_columns]:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    logger.debug(f"Converted column '{col}' to datetime")
                except Exception as e:
                    logger.warning(f"Failed to convert column '{col}' to datetime: {e}")
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Handle missing values based on data type and configuration."""
        max_missing = self.data_validation_rules.get('max_missing_percentage', 10)
        
        for col in df.columns:
            missing_pct = (df[col].isnull().sum() / len(df)) * 100
            
            if missing_pct > max_missing:
                logger.warning(f"Column '{col}' has {missing_pct:.1f}% missing values")
            
            # Fill missing values based on data type
            if df[col].dtype in ['int64', 'float64']:
                df[col] = df[col].fillna(df[col].median())
            elif df[col].dtype == 'object':
                df[col] = df[col].fillna('Unknown')
        
        return df
    
    def _remove_outliers(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Remove outliers using IQR method."""
        threshold = self.data_validation_rules.get('outlier_threshold', 3.0)
        
        for col in df.select_dtypes(include=[np.number]).columns:
            if col in ['date', 'id']:  # Skip non-numeric columns
                continue
                
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            if outliers > 0:
                logger.info(f"Removed {outliers} outliers from column '{col}' in {data_type} data")
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        
        return df
    
    def _log_data_quality(self, df: pd.DataFrame, data_type: str) -> None:
        """Log data quality metrics."""
        logger.info(f"{data_type} data quality metrics:")
        logger.info(f"  - Rows: {len(df)}")
        logger.info(f"  - Columns: {len(df.columns)}")
        logger.info(f"  - Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        if 'date' in df.columns:
            date_range = df['date'].max() - df['date'].min()
            logger.info(f"  - Date range: {date_range.days} days")


    # --- FEATURE ENGINEERING FOR DARTS FORECASTING ---
    
    def _generate_time_covariates(self, series: TimeSeries) -> TimeSeries:
        """
        Creates time-based external features for Darts (e.g., day of week, month).
        
        Args:
            series: The time series used to define the date range.
            
        Returns:
            A TimeSeries object with date features.
        """
        # Generate features for the entire history + forecast horizon
        covariates = datetime_attribute_timeseries(
            series, 
            attribute='dayofweek', 
            one_hot=True
        )
        covariates = covariates.stack(
            datetime_attribute_timeseries(series, attribute='month', one_hot=True)
        )
        # Add a numeric trend covariate (important for GBM models)
        trend = TimeSeries.from_times_and_values(
            series.time_index, 
            np.arange(len(series)), 
            columns=['trend']
        )
        covariates = covariates.stack(trend)
        
        return covariates


    def _generate_holiday_covariates(self, start_date: pd.Timestamp, end_date: pd.Timestamp) -> TimeSeries:
        """
        Generates a 0/1 binary TimeSeries for Indian holiday features.
        
        Args:
            start_date: Start of the historical data period.
            end_date: End of the forecast horizon.
            
        Returns:
            A TimeSeries with columns for different holiday features.
        """
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df_holidays = pd.DataFrame(index=date_range)
        
        # 1. Main Holiday Flag (Binary indicator for a holiday on that day)
        df_holidays['is_holiday'] = [1 if d in self.indian_holidays else 0 for d in date_range]
        
        # 2. Pre-Holiday Surge (Flag 7 days before a major holiday)
        is_major_holiday = lambda d: d in self.indian_holidays and ('Diwali' in self.indian_holidays.get(d) or 'Holi' in self.indian_holidays.get(d) or 'Christmas' in self.indian_holidays.get(d))
        pre_holiday_surge = np.zeros(len(date_range))
        
        for i, d in enumerate(date_range):
            # Check the next 7 days for a major holiday
            for j in range(1, 8):
                future_date = d + timedelta(days=j)
                if future_date in self.indian_holidays and is_major_holiday(future_date.date()):
                    pre_holiday_surge[i] = 1
                    break
                    
        df_holidays['pre_holiday_surge'] = pre_holiday_surge
        
        # 3. Post-Holiday Dip (Flag 3 days after a major holiday)
        post_holiday_dip = np.zeros(len(date_range))
        for i, d in enumerate(date_range):
            # Check the last 3 days for a major holiday
            for j in range(1, 4):
                past_date = d - timedelta(days=j)
                if past_date in self.indian_holidays and is_major_holiday(past_date.date()):
                    post_holiday_dip[i] = 1
                    break
        
        df_holidays['post_holiday_dip'] = post_holiday_dip
        
        return TimeSeries.from_dataframe(df_holidays, time_col=None, freq='D')


    def prepare_for_forecasting(self, 
                               df_sales: pd.DataFrame, 
                               target_column: str = 'revenue',
                               frequency: str = 'D',
                               include_holidays: bool = True,
                               include_time_features: bool = True,
                               custom_covariates: Optional[List[str]] = None) -> Tuple[TimeSeries, TimeSeries]:
        """
        Dynamic method to prepare sales data and generate covariates for forecasting.
        
        Args:
            df_sales: DataFrame containing date and target column
            target_column: Column to use as time series target
            frequency: Time series frequency ('D', 'W', 'M', etc.)
            include_holidays: Whether to include holiday features
            include_time_features: Whether to include time-based features
            custom_covariates: List of additional covariate columns to include
            
        Returns:
            Tuple of (target_series, all_covariates_series)
            
        Raises:
            ValueError: If data is insufficient for forecasting
        """
        logger.info(f"Preparing forecasting data for target column: {target_column}")
        
        if df_sales.empty:
            raise ValueError("Sales DataFrame is empty. Cannot prepare for forecasting.")
        
        # Validate minimum data requirements
        min_data_points = self.config.get('forecasting', {}).get('min_data_points', 30)
        if len(df_sales) < min_data_points:
            raise ValueError(f"Insufficient data points: {len(df_sales)} < {min_data_points}")
        
        # 1. Prepare Target Series with dynamic frequency
        df_sales = df_sales.copy()
        df_sales = self._auto_convert_dates(df_sales)
        
        # Auto-detect date column if not explicitly set
        date_col = self._detect_date_column(df_sales)
        df_sales = df_sales.set_index(date_col).sort_index()
        
        # Validate target column exists
        if target_column not in df_sales.columns:
            raise ValueError(f"Target column '{target_column}' not found in data")
        
        # Aggregate to specified frequency
        target_series_df = df_sales[target_column].resample(frequency).sum().fillna(0)
        target_series = TimeSeries.from_series(target_series_df, freq=frequency)

        # 2. Determine Full Date Range for Covariates
        start_date = target_series.start_time()
        end_date = target_series.end_time() + pd.Timedelta(days=self.forecast_days)
        
        # Create a placeholder series for the full range
        full_range_series = target_series.append_values([0] * self.forecast_days)

        # 3. Generate Covariates dynamically
        all_covariates_list = []
        
        if include_holidays:
            try:
                holiday_covariates = self._generate_holiday_covariates(start_date, end_date)
                all_covariates_list.append(holiday_covariates)
                logger.info("Holiday covariates generated")
            except Exception as e:
                logger.warning(f"Failed to generate holiday covariates: {e}")
        
        if include_time_features:
            try:
                time_covariates = self._generate_time_covariates(full_range_series)
                all_covariates_list.append(time_covariates)
                logger.info("Time-based covariates generated")
            except Exception as e:
                logger.warning(f"Failed to generate time covariates: {e}")
        
        # Add custom covariates if provided
        if custom_covariates:
            custom_covs = self._generate_custom_covariates(df_sales, custom_covariates, frequency)
            if custom_covs is not None:
                all_covariates_list.append(custom_covs)
                logger.info(f"Custom covariates generated: {custom_covariates}")
        
        # Stack all covariates together
        if all_covariates_list:
            all_covariates = all_covariates_list[0]
            for cov in all_covariates_list[1:]:
                all_covariates = all_covariates.stack(cov)
        else:
            # Create empty covariates if none are generated
            all_covariates = TimeSeries.from_times_and_values(
                full_range_series.time_index, 
                np.zeros((len(full_range_series), 1)), 
                columns=['empty_covariate']
            )
        
        logger.info(f"Forecasting preparation complete:")
        logger.info(f"  - Target series: {target_series.start_time()} to {target_series.end_time()}")
        logger.info(f"  - Covariates: {all_covariates.start_time()} to {all_covariates.end_time()}")
        logger.info(f"  - Frequency: {frequency}")
        
        return target_series, all_covariates
    
    def _detect_date_column(self, df: pd.DataFrame) -> str:
        """Auto-detect the date column in the DataFrame."""
        for col in self.date_columns:
            if col in df.columns:
                return col
        
        # If no standard date column found, look for datetime-like columns
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]' or 'date' in col.lower():
                return col
        
        raise ValueError(f"No date column found. Expected one of: {self.date_columns}")
    
    def _generate_custom_covariates(self, 
                                  df: pd.DataFrame, 
                                  covariate_columns: List[str], 
                                  frequency: str) -> Optional[TimeSeries]:
        """Generate custom covariates from additional columns."""
        try:
            available_cols = [col for col in covariate_columns if col in df.columns]
            if not available_cols:
                logger.warning(f"None of the custom covariate columns found: {covariate_columns}")
                return None
            
            # Aggregate custom columns to the specified frequency
            custom_data = df[available_cols].resample(frequency).mean().fillna(0)
            
            return TimeSeries.from_dataframe(custom_data, freq=frequency)
            
        except Exception as e:
            logger.error(f"Failed to generate custom covariates: {e}")
            return None
