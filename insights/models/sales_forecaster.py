import pandas as pd
import numpy as np
import os
import json
from typing import Tuple, Dict, Any, List, Optional, Union
import logging
from datetime import datetime, timedelta
import warnings
from functools import lru_cache
import calendar
import holidays

from darts import TimeSeries
from darts.models import LightGBMModel, RandomForest, LinearRegressionModel
from darts.dataprocessing.transformers import Scaler
from darts.metrics import mape, rmse, mae, smape
from darts.utils.model_selection import backtest

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

class IndianHolidayCalendar:
    """
    Enhanced Indian holiday calendar using the Python holidays library for accurate holiday detection.
    
    This class generates major Indian holidays including:
    - Official government holidays from the holidays library
    - Regional holidays and state-specific observances
    - Festival seasons and shopping periods
    - Business impact analysis for retail forecasting
    """
    
    def __init__(self, state: str = 'IN', include_regional: bool = True):
        """
        Initialize the Indian holiday calendar.
        
        Args:
            state: State code for regional holidays (default: 'IN' for national)
            include_regional: Whether to include regional holidays
        """
        self.state = state
        self.include_regional = include_regional
        
        # Initialize holidays objects for different years and states
        self.national_holidays = {}
        self.regional_holidays = {}
        
        # Major commercial holidays that significantly impact sales
        self.major_commercial_holidays = {
            'diwali', 'deepavali', 'dussehra', 'vijayadashami', 'holi', 
            'diwali/deepavali', 'eid al-fitr', 'eid ul-fitr', 'christmas day',
            'independence day', 'republic day', 'gandhi jayanti',
            'ganesh chaturthi', 'karva chauth'
        }
        
        # Festival seasons and shopping periods
        self.shopping_seasons = {
            'pre_diwali_shopping': {'start_offset': -20, 'end_offset': 0, 'base_holiday': 'diwali'},
            'post_diwali_shopping': {'start_offset': 0, 'end_offset': 7, 'base_holiday': 'diwali'},
            'wedding_season_winter': {'months': [11, 12, 1, 2], 'intensity': 'high'},
            'summer_shopping': {'months': [4, 5], 'intensity': 'medium'},
            'festival_season': {'months': [8, 9, 10, 11], 'intensity': 'high'},
            'new_year_shopping': {'start_offset': -10, 'end_offset': 7, 'base_holiday': 'new year\'s day'}
        }
    
    def get_holidays_for_year(self, year: int) -> Dict[str, datetime]:
        """Get all holidays for a specific year using the holidays library."""
        if year not in self.national_holidays:
            # Get national holidays
            self.national_holidays[year] = holidays.India(years=year, state=None)
            
            # Add state-specific holidays if requested
            if self.include_regional and self.state != 'IN':
                self.regional_holidays[year] = holidays.India(years=year, state=self.state)
        
        holiday_dict = {}
        
        # Convert holidays to datetime objects
        for date, name in self.national_holidays[year].items():
            holiday_dict[name.lower().replace(' ', '_').replace('/', '_')] = datetime.combine(date, datetime.min.time())
        
        # Add regional holidays
        if year in self.regional_holidays:
            for date, name in self.regional_holidays[year].items():
                key = f"regional_{name.lower().replace(' ', '_').replace('/', '_')}"
                holiday_dict[key] = datetime.combine(date, datetime.min.time())
        
        return holiday_dict
    
    def generate_holiday_features(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Generate comprehensive holiday features using the holidays library.
        
        Returns a DataFrame with holiday indicators and business-relevant features.
        """
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        features_df = pd.DataFrame({'date': date_range})
        
        # Initialize all holiday features
        holiday_features = [
            'is_holiday', 'is_major_holiday', 'is_festival_season',
            'is_shopping_season', 'days_to_next_holiday', 'days_from_last_holiday',
            'is_diwali_season', 'is_wedding_season', 'is_summer_sale',
            'is_new_year_season', 'month_of_year', 'quarter',
            'is_weekend', 'day_of_week', 'day_of_month', 'day_of_year',
            'holiday_intensity', 'commercial_impact_score'
        ]
        
        for feature in holiday_features:
            features_df[feature] = 0
        
        # Get unique years in the date range
        years = list(set([date.year for date in date_range]))
        all_holidays = {}
        
        # Collect holidays from all relevant years
        for year in years:
            national_holidays = holidays.India(years=year, state=None)
            if self.include_regional and self.state != 'IN':
                regional_holidays = holidays.India(years=year, state=self.state)
                # Merge regional holidays
                for date, name in regional_holidays.items():
                    national_holidays[date] = f"Regional: {name}"
            
            # Convert to datetime and add to collection
            for date, name in national_holidays.items():
                all_holidays[datetime.combine(date, datetime.min.time())] = name
        
        logger.info(f"Found {len(all_holidays)} holidays from {min(years)} to {max(years)}")
        
        # Process each date
        for idx, date in enumerate(date_range):
            date_dt = date.to_pydatetime()
            
            # Basic date features
            features_df.loc[idx, 'month_of_year'] = date_dt.month
            features_df.loc[idx, 'quarter'] = (date_dt.month - 1) // 3 + 1
            features_df.loc[idx, 'is_weekend'] = 1 if date_dt.weekday() >= 5 else 0
            features_df.loc[idx, 'day_of_week'] = date_dt.weekday()
            features_df.loc[idx, 'day_of_month'] = date_dt.day
            features_df.loc[idx, 'day_of_year'] = date_dt.timetuple().tm_yday
            
            # Holiday detection using holidays library
            is_holiday = date_dt in all_holidays
            holiday_name = all_holidays.get(date_dt, '').lower()
            
            features_df.loc[idx, 'is_holiday'] = 1 if is_holiday else 0
            
            # Major holiday detection
            is_major = any(major in holiday_name for major in self.major_commercial_holidays)
            features_df.loc[idx, 'is_major_holiday'] = 1 if is_major else 0
            
            # Festival season detection
            features_df.loc[idx, 'is_festival_season'] = self._is_festival_season(date_dt)
            
            # Shopping season features
            self._add_shopping_season_features(features_df, idx, date_dt, all_holidays)
            
            # Holiday intensity and commercial impact
            features_df.loc[idx, 'holiday_intensity'] = self._calculate_holiday_intensity(date_dt, all_holidays)
            features_df.loc[idx, 'commercial_impact_score'] = self._calculate_commercial_impact(date_dt, all_holidays)
            
            # Proximity to holidays
            self._add_holiday_proximity_features(features_df, idx, date_dt, all_holidays)
        
        logger.info(f"Generated holiday features with {features_df['is_holiday'].sum()} holiday days")
        return features_df
    
    def _is_festival_season(self, date_dt: datetime) -> int:
        """Determine if date falls in major festival season."""
        # Festival season: August to November (major Indian festivals)
        if date_dt.month in [8, 9, 10, 11]:
            return 1
        return 0
    
    def _calculate_holiday_intensity(self, date_dt: datetime, all_holidays: Dict[datetime, str]) -> float:
        """Calculate holiday intensity based on proximity and importance."""
        if date_dt in all_holidays:
            holiday_name = all_holidays[date_dt].lower()
            if any(major in holiday_name for major in self.major_commercial_holidays):
                return 3.0  # High intensity
            return 2.0  # Medium intensity
        
        # Check for nearby holidays (within 3 days)
        for i in range(1, 4):
            before = date_dt - timedelta(days=i)
            after = date_dt + timedelta(days=i)
            
            if before in all_holidays or after in all_holidays:
                return 1.0 / i  # Decreasing intensity by distance
        
        return 0.0
    
    def _calculate_commercial_impact(self, date_dt: datetime, all_holidays: Dict[datetime, str]) -> float:
        """Calculate commercial impact score for business planning."""
        base_score = 0.0
        
        # Direct holiday impact
        if date_dt in all_holidays:
            holiday_name = all_holidays[date_dt].lower()
            if 'diwali' in holiday_name or 'deepavali' in holiday_name:
                base_score = 10.0
            elif any(major in holiday_name for major in ['dussehra', 'holi', 'eid']):
                base_score = 8.0
            elif any(major in holiday_name for major in self.major_commercial_holidays):
                base_score = 6.0
            else:
                base_score = 3.0
        
        # Weekend bonus
        if date_dt.weekday() >= 5:  # Weekend
            base_score *= 1.2
        
        # Month-based multipliers
        month_multipliers = {
            10: 1.5,  # October (Dussehra, pre-Diwali)
            11: 1.8,  # November (Diwali, wedding season)
            12: 1.3,  # December (Christmas, New Year)
            3: 1.2,   # March (Holi)
            4: 1.1,   # April (various regional festivals)
            8: 1.2,   # August (Independence Day, festivals)
            9: 1.3    # September (Ganesh Chaturthi)
        }
        
        base_score *= month_multipliers.get(date_dt.month, 1.0)
        
        return round(base_score, 2)
    
    def _add_shopping_season_features(self, df: pd.DataFrame, idx: int, 
                                    date_dt: datetime, all_holidays: Dict[datetime, str]):
        """Add shopping season specific features."""
        month, day = date_dt.month, date_dt.day
        
        # Diwali season (check for actual Diwali date)
        diwali_dates = [date for date, name in all_holidays.items() 
                       if 'diwali' in name.lower() or 'deepavali' in name.lower()]
        
        if diwali_dates:
            diwali_date = min(diwali_dates, key=lambda x: abs((x - date_dt).days))
            days_to_diwali = (diwali_date - date_dt).days
            
            if -7 <= days_to_diwali <= 20:  # 20 days before to 7 days after
                df.loc[idx, 'is_diwali_season'] = 1
        
        # Wedding seasons (traditional periods)
        if ((month == 11 and day >= 15) or month == 12 or 
            month == 1 or (month == 2 and day <= 15)):
            df.loc[idx, 'is_wedding_season'] = 1
        
        # Summer shopping season
        if month in [4, 5]:
            df.loc[idx, 'is_summer_sale'] = 1
        
        # New Year season
        if (month == 12 and day >= 20) or (month == 1 and day <= 7):
            df.loc[idx, 'is_new_year_season'] = 1
        
        # General shopping season indicator
        if any([df.loc[idx, col] for col in ['is_diwali_season', 'is_wedding_season', 
                                           'is_summer_sale', 'is_new_year_season']]):
            df.loc[idx, 'is_shopping_season'] = 1
    
    def _add_holiday_proximity_features(self, df: pd.DataFrame, idx: int, 
                                      date_dt: datetime, all_holidays: Dict[datetime, str]):
        """Add features for proximity to holidays."""
        min_days_to_next = float('inf')
        min_days_from_last = float('inf')
        
        for holiday_date in all_holidays.keys():
            days_diff = (holiday_date - date_dt).days
            
            if days_diff > 0:  # Future holiday
                min_days_to_next = min(min_days_to_next, days_diff)
            elif days_diff < 0:  # Past holiday
                min_days_from_last = min(min_days_from_last, abs(days_diff))
        
        # Cap the values to meaningful ranges
        df.loc[idx, 'days_to_next_holiday'] = min(min_days_to_next, 30) if min_days_to_next != float('inf') else 30
        df.loc[idx, 'days_from_last_holiday'] = min(min_days_from_last, 30) if min_days_from_last != float('inf') else 30
    
    def get_holiday_summary(self, year: int) -> Dict[str, Any]:
        """Get a summary of holidays for a specific year."""
        india_holidays = holidays.India(years=year)
        
        if self.include_regional and self.state != 'IN':
            regional_holidays = holidays.India(years=year, state=self.state)
            total_holidays = len(set(list(india_holidays.keys()) + list(regional_holidays.keys())))
        else:
            total_holidays = len(india_holidays)
        
        # Categorize holidays
        major_holidays = []
        festival_holidays = []
        government_holidays = []
        
        for date, name in india_holidays.items():
            name_lower = name.lower()
            if any(major in name_lower for major in self.major_commercial_holidays):
                major_holidays.append((date, name))
            
            if any(festival in name_lower for festival in ['diwali', 'holi', 'dussehra', 'ganesh']):
                festival_holidays.append((date, name))
            
            if any(govt in name_lower for govt in ['independence', 'republic', 'gandhi']):
                government_holidays.append((date, name))
        
        return {
            'year': year,
            'total_holidays': total_holidays,
            'major_commercial_holidays': len(major_holidays),
            'festival_holidays': len(festival_holidays),
            'government_holidays': len(government_holidays),
            'major_holidays_list': [(date.strftime('%Y-%m-%d'), name) for date, name in major_holidays],
            'peak_months': self._get_peak_holiday_months(india_holidays)
        }
    
    def _get_peak_holiday_months(self, holiday_dict: holidays.HolidayBase) -> Dict[int, int]:
        """Get months with most holidays."""
        month_counts = {}
        for date in holiday_dict.keys():
            month = date.month
            month_counts[month] = month_counts.get(month, 0) + 1
        
        return dict(sorted(month_counts.items(), key=lambda x: x[1], reverse=True))

class SalesForecaster:
    """
    Dynamic deployment-grade forecasting engine supporting multiple models and configurations.
    
    This class handles the entire model lifecycle: initialization, scaling, 
    training (with covariate integration), rigorous validation (via backtesting), 
    prediction (with confidence intervals), and persistence (save/load).
    """
    
    # Define default paths for saving and loading model artifacts
    MODEL_FILENAME = 'models/production_model.pkl'
    CONFIG_FILENAME = 'forecaster_config.json'
    
    # Supported model types
    SUPPORTED_MODELS = {
        'lightgbm': LightGBMModel,
        'random_forest': RandomForest,
        'linear_regression': LinearRegressionModel
    }
    
    def __init__(self, 
                 model_type: str = 'lightgbm',
                 input_chunk_length: int = 30, 
                 output_chunk_length: int = 90, 
                 random_state: int = 42,
                 config_file: Optional[str] = None,
                 enable_auto_tuning: bool = False,
                 log_level: str = 'INFO'):
        """
        Dynamic initialization with configurable model type and parameters.
        
        Args:
            model_type: Type of model to use ('lightgbm', 'random_forest', 'linear_regression')
            input_chunk_length: Number of historical points to use for prediction
            output_chunk_length: Number of future points to predict
            random_state: Random seed for reproducibility
            config_file: Path to JSON configuration file
            enable_auto_tuning: Whether to enable automatic hyperparameter tuning
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.model_type = model_type.lower()
        self.input_chunk_length = input_chunk_length
        self.output_chunk_length = output_chunk_length
        self.random_state = random_state
        self.enable_auto_tuning = enable_auto_tuning
        
        # Set logging level
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize model and scaler
        self.model: Optional[Union[LightGBMModel, RandomForest, LinearRegressionModel]] = None
        self.scaler = Scaler()
        
        # Initialize Indian holiday calendar for enhanced forecasting
        self.holiday_calendar = IndianHolidayCalendar()
        
        # Get model parameters based on type
        self.model_params = self._get_model_parameters()
        
        logger.info(f"Forecaster initialized: {model_type} model, input_chunk={input_chunk_length}, output_chunk={output_chunk_length}")
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            'model_parameters': {
                'lightgbm': {
                    'n_estimators': 500,
                    'max_depth': 7,
                    'learning_rate': 0.05,
                    'subsample': 0.8,
                    'colsample_bytree': 0.8
                },
                'random_forest': {
                    'n_estimators': 200,
                    'max_depth': 10,
                    'min_samples_split': 5,
                    'min_samples_leaf': 2
                },
                'linear_regression': {
                    'l1_ratio': 0.5,
                    'alpha': 0.1
                }
            },
            'validation': {
                'backtest_start': 0.8,
                'backtest_horizon': 30,
                'min_training_samples': 100
            },
            'prediction': {
                'confidence_intervals': [0.05, 0.5, 0.95],
                'num_samples': 500
            },
            'holiday_features': {
                'enabled': True,
                'include_proximity': True,
                'include_shopping_seasons': True,
                'include_weekend_effects': True,
                'holiday_impact_days': 3,  # Days before/after holiday to consider
                'major_holiday_weight': 2.0,  # Weight multiplier for major holidays
                'festival_season_weight': 1.5  # Weight multiplier for festival seasons
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
    
    def _get_model_parameters(self) -> Dict[str, Any]:
        """Get model-specific parameters based on model type."""
        if self.model_type not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model type: {self.model_type}. Supported types: {list(self.SUPPORTED_MODELS.keys())}")
        
        # Base parameters common to all models
        base_params = {
            'lags': [-i for i in range(1, min(self.input_chunk_length, 7) + 1)],  # Limit lags to 7 days max
            'output_chunk_length': self.output_chunk_length
        }
        
        # Add random_state only for models that support it
        if self.model_type != 'linear_regression':
            base_params['random_state'] = self.random_state
        
        # Add model-specific parameters only if they exist for this model type
        model_specific_params = self.config['model_parameters'].get(self.model_type, {})
        
        # Only add parameters that are valid for this model type
        if self.model_type == 'linear_regression':
            # LinearRegressionModel has very limited parameters in Darts
            # It doesn't accept l1_ratio or alpha in the constructor
            # These are set via fit() method if needed
            pass  # Only use base_params for linear regression
        else:
            # For other models (LightGBM, RandomForest), add all parameters
            base_params.update(model_specific_params)
        
        return base_params
    
    def generate_holiday_enhanced_covariates(self, 
                                           start_date: datetime, 
                                           end_date: datetime,
                                           existing_covariates: Optional[pd.DataFrame] = None) -> TimeSeries:
        """
        Generate comprehensive covariates including Indian holidays and seasonal features.
        
        Args:
            start_date: Start date for covariate generation
            end_date: End date for covariate generation
            existing_covariates: Optional existing covariates to merge with holiday features
            
        Returns:
            TimeSeries object with enhanced holiday and seasonal features
        """
        logger.info(f"Generating holiday-enhanced covariates from {start_date} to {end_date}")
        
        # Generate holiday features
        holiday_features = self.holiday_calendar.generate_holiday_features(start_date, end_date)
        
        # If existing covariates are provided, merge them
        if existing_covariates is not None:
            # Ensure date column alignment
            if 'date' in existing_covariates.columns:
                # Convert to datetime if needed
                existing_covariates['date'] = pd.to_datetime(existing_covariates['date'])
                holiday_features['date'] = pd.to_datetime(holiday_features['date'])
                
                # Merge on date
                combined_features = pd.merge(holiday_features, existing_covariates, on='date', how='left')
            else:
                # If no date column, assume same length and concatenate
                combined_features = pd.concat([holiday_features, existing_covariates], axis=1)
        else:
            combined_features = holiday_features
        
        # Set date as index for TimeSeries conversion
        combined_features = combined_features.set_index('date')
        
        # Convert to TimeSeries
        try:
            covariate_series = TimeSeries.from_dataframe(combined_features)
            logger.info(f"Generated covariates with {len(combined_features.columns)} features: {list(combined_features.columns)}")
            return covariate_series
        except Exception as e:
            logger.error(f"Failed to create TimeSeries from covariates: {e}")
            raise ValueError(f"Covariate generation failed: {e}")
    
    def get_holiday_impact_analysis(self, 
                                  target_series: TimeSeries,
                                  start_analysis_date: Optional[datetime] = None,
                                  end_analysis_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Analyze the impact of Indian holidays on sales patterns.
        
        Args:
            target_series: Historical sales data
            start_analysis_date: Start date for analysis (default: series start)
            end_analysis_date: End date for analysis (default: series end)
            
        Returns:
            Dictionary with holiday impact analysis
        """
        if start_analysis_date is None:
            start_analysis_date = target_series.start_time()
        if end_analysis_date is None:
            end_analysis_date = target_series.end_time()
        
        logger.info(f"Analyzing holiday impact from {start_analysis_date} to {end_analysis_date}")
        
        # Generate holiday features for the analysis period
        holiday_features = self.holiday_calendar.generate_holiday_features(
            start_analysis_date, end_analysis_date
        )
        
        # Convert target series to DataFrame
        target_df = target_series.pd_dataframe().reset_index()
        target_df.columns = ['date', 'sales']
        
        # Merge with holiday features
        analysis_df = pd.merge(holiday_features, target_df, on='date', how='inner')
        
        # Calculate holiday impact metrics
        holiday_impact = {}
        
        # Overall holiday vs non-holiday performance
        holiday_sales = analysis_df[analysis_df['is_holiday'] == 1]['sales']
        non_holiday_sales = analysis_df[analysis_df['is_holiday'] == 0]['sales']
        
        if len(holiday_sales) > 0 and len(non_holiday_sales) > 0:
            holiday_impact['avg_holiday_sales'] = holiday_sales.mean()
            holiday_impact['avg_non_holiday_sales'] = non_holiday_sales.mean()
            holiday_impact['holiday_lift_percent'] = (
                (holiday_sales.mean() / non_holiday_sales.mean() - 1) * 100
            ).round(2)
        
        # Major holiday impact
        major_holiday_sales = analysis_df[analysis_df['is_major_holiday'] == 1]['sales']
        if len(major_holiday_sales) > 0:
            holiday_impact['avg_major_holiday_sales'] = major_holiday_sales.mean()
            holiday_impact['major_holiday_lift_percent'] = (
                (major_holiday_sales.mean() / non_holiday_sales.mean() - 1) * 100
            ).round(2)
        
        # Festival season impact
        festival_sales = analysis_df[analysis_df['is_festival_season'] == 1]['sales']
        if len(festival_sales) > 0:
            holiday_impact['avg_festival_season_sales'] = festival_sales.mean()
            holiday_impact['festival_season_lift_percent'] = (
                (festival_sales.mean() / non_holiday_sales.mean() - 1) * 100
            ).round(2)
        
        # Shopping season impact
        shopping_season_sales = analysis_df[analysis_df['is_shopping_season'] == 1]['sales']
        if len(shopping_season_sales) > 0:
            holiday_impact['avg_shopping_season_sales'] = shopping_season_sales.mean()
            holiday_impact['shopping_season_lift_percent'] = (
                (shopping_season_sales.mean() / non_holiday_sales.mean() - 1) * 100
            ).round(2)
        
        # Weekend vs weekday analysis
        weekend_sales = analysis_df[analysis_df['is_weekend'] == 1]['sales']
        weekday_sales = analysis_df[analysis_df['is_weekend'] == 0]['sales']
        if len(weekend_sales) > 0 and len(weekday_sales) > 0:
            holiday_impact['avg_weekend_sales'] = weekend_sales.mean()
            holiday_impact['avg_weekday_sales'] = weekday_sales.mean()
            holiday_impact['weekend_lift_percent'] = (
                (weekend_sales.mean() / weekday_sales.mean() - 1) * 100
            ).round(2)
        
        # Monthly patterns
        monthly_avg = analysis_df.groupby('month_of_year')['sales'].mean()
        holiday_impact['monthly_patterns'] = monthly_avg.to_dict()
        holiday_impact['peak_sales_month'] = monthly_avg.idxmax()
        holiday_impact['lowest_sales_month'] = monthly_avg.idxmin()
        
        logger.info("Holiday impact analysis completed")
        return holiday_impact
        
    def save_model(self, path: str = MODEL_FILENAME) -> None:
        """Saves the trained model and scaler state for future deployment."""
        if self.model is None:
            logger.warning("Attempted to save, but the model is not trained yet.")
            return

        # Darts models have a built-in save method that handles model state
        self.model.save(path)
        
        # Save the scaler state separately, as it is needed to inverse-transform the forecast
        import joblib
        joblib.dump(self.scaler, f"{path.replace('.pkl', '_scaler.pkl')}")
        logger.info(f"Model and scaler successfully saved to {path} and its companion file.")

    def load_model(self, path: str = MODEL_FILENAME) -> bool:
        """Loads a previously trained model and scaler from disk with enhanced error handling."""
        try:
            # Check if file exists first
            if not os.path.exists(path):
                logger.warning(f"Model file not found at {path}")
                return False
                
            # Load the model artifact using the correct model class
            model_class = self.SUPPORTED_MODELS[self.model_type]
            self.model = model_class.load(path)
            
            # Load the scaler state
            scaler_path = f"{path.replace('.pkl', '_scaler.pkl')}"
            if not os.path.exists(scaler_path):
                logger.error(f"Scaler file not found at {scaler_path}")
                return False
                
            import joblib
            self.scaler = joblib.load(scaler_path)
            
            logger.info(f"Model and scaler successfully loaded from {path}")
            logger.info(f"Model type: {self.model_type}, Scaler: {type(self.scaler)}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model from {path}: {e}")
            return False
    
    def validate_model(self) -> Dict[str, Any]:
        """Validate that the loaded model is ready for predictions."""
        if self.model is None:
            return {"valid": False, "error": "No model loaded"}
        
        if self.scaler is None:
            return {"valid": False, "error": "No scaler loaded"}
        
        try:
            # Create test series with sufficient data points
            test_dates = pd.date_range('2024-01-01', periods=60, freq='D')
            test_values = np.random.randn(60) * 100 + 1000
            test_series = TimeSeries.from_times_and_values(test_dates, test_values)
            
            # Check if model uses future covariates
            uses_covariates = hasattr(self.model, 'lags_future_covariates') and self.model.lags_future_covariates is not None
            
            # Test prediction with covariates if needed
            if uses_covariates:
                # Generate simple test covariates
                test_cov_dates = pd.date_range('2024-01-01', periods=70, freq='D')
                test_cov_values = np.random.randint(0, 2, size=70)
                test_covariates = TimeSeries.from_times_and_values(test_cov_dates, test_cov_values)
                test_pred = self.model.predict(n=5, series=test_series, future_covariates=test_covariates)
            else:
                test_pred = self.model.predict(n=5, series=test_series)
            
            return {
                "valid": True,
                "model_type": self.model_type,
                "model_ready": True,
                "scaler_ready": True,
                "uses_covariates": uses_covariates,
                "test_prediction_successful": True,
                "test_prediction_length": len(test_pred)
            }
        except Exception as e:
            import traceback
            return {
                "valid": False, 
                "error": f"Model validation failed: {str(e)}",
                "details": traceback.format_exc()
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        if self.model is None:
            return {"status": "no_model_loaded"}
        
        return {
            "model_type": self.model_type,
            "model_loaded": True,
            "scaler_loaded": self.scaler is not None,
            "model_parameters": self.model_params,
            "validation": self.validate_model()
        }
            
    def train(self, 
              target_series: TimeSeries, 
              covariates: Optional[TimeSeries] = None,
              future_covariates: Optional[TimeSeries] = None,
              validation_split: float = 0.2,
              early_stopping: bool = True,
              use_holiday_features: bool = True) -> Dict[str, Any]:
        """
        Dynamic training method with configurable validation, early stopping, and Indian holiday integration.
        
        Args:
            target_series: Time series data to train on
            covariates: Optional covariate time series (backward compatibility)
            future_covariates: Optional future covariate time series (preferred parameter name) 
                       holiday features will be auto-generated)
            validation_split: Fraction of data to use for validation
            early_stopping: Whether to use early stopping during training
            use_holiday_features: Whether to automatically generate Indian holiday features
            
        Returns:
            Dictionary with training metrics and model performance
        """
        logger.info(f"Starting {self.model_type} model training on data up to: {target_series.end_time()}")
        
        # Handle backward compatibility: covariates vs future_covariates
        if future_covariates is None and covariates is not None:
            logger.info("Using 'covariates' parameter (backward compatibility)")
            future_covariates = covariates
        
        # Regenerate model parameters fresh for this training session
        # This ensures parameters match the current model type
        self.model_params = self._get_model_parameters()
        logger.info(f"Model parameters generated for {self.model_type}")
        
        # Handle covariates - use provided ones or generate simple holiday features
        if future_covariates is not None:
            # Use the covariates provided
            logger.info(f"Using provided future covariates with {future_covariates.n_components} components")
            # Validate covariate date range
            if target_series.end_time() > future_covariates.end_time():
                raise ValueError(
                    f"Future covariates must extend beyond target series. "
                    f"Target ends at {target_series.end_time()}, covariates end at {future_covariates.end_time()}"
                )
        elif use_holiday_features:
            # Generate simple holiday covariates if none provided
            logger.info("Generating simple holiday features for Linear Regression...")
            
            # Create a simple holiday indicator (just binary holiday/no holiday)
            start_date = target_series.start_time()
            end_date = target_series.end_time() + timedelta(days=self.output_chunk_length)
            
            # Simple holiday calendar
            indian_holidays = holidays.India()
            
            # Create date range
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            holiday_data = pd.DataFrame({
                'date': date_range,
                'is_holiday': [1 if date.date() in indian_holidays else 0 for date in date_range]
            })
            holiday_data.set_index('date', inplace=True)
            
            # Convert to TimeSeries
            future_covariates = TimeSeries.from_dataframe(holiday_data)
            logger.info("Simple holiday features generated successfully")
        
        # Validate input data
        min_samples = self.config['validation']['min_training_samples']
        if len(target_series) < min_samples:
            raise ValueError(f"Insufficient training data: {len(target_series)} < {min_samples}")
        
        try:
            # 1. Prepare training and validation data
            if validation_split > 0:
                split_point = int(len(target_series) * (1 - validation_split))
                train_series = target_series[:split_point]
                val_series = target_series[split_point:]
                
                if future_covariates is not None:
                    train_future_covariates = future_covariates[:split_point + self.output_chunk_length]
                    val_future_covariates = future_covariates[split_point:]
                else:
                    train_future_covariates = val_future_covariates = None
            else:
                train_series = target_series
                val_series = None
                train_future_covariates = future_covariates
                val_future_covariates = None
            
            # 2. Fit and apply scaler to the training series
            scaled_train = self.scaler.fit_transform(train_series)
            
            # 3. Initialize the model based on type
            model_class = self.SUPPORTED_MODELS[self.model_type]
            
            # Prepare model parameters
            model_params = self.model_params.copy()
            
            # Add early stopping parameters if supported
            if early_stopping and val_series is not None and self.model_type == 'lightgbm':
                # For LightGBM in Darts, early stopping is handled via fit parameters, not constructor
                pass
            
            # 4. Add future covariates parameter if we have covariates
            if train_future_covariates is not None:
                model_params['lags_future_covariates'] = [0]  # Use current day's holiday info
            
            # Initialize and train the model
            self.model = model_class(**model_params)
            
            # Train the model with future covariates if available
            if train_future_covariates is not None:
                self.model.fit(series=scaled_train, future_covariates=train_future_covariates)
            else:
                self.model.fit(scaled_train)
            
            # 5. Calculate training metrics
            training_metrics = self._calculate_training_metrics(scaled_train, val_series)
            
            logger.info(f"{self.model_type} model training completed successfully")
            logger.info(f"Training metrics: {training_metrics}")
            
            return {
                "model_type": self.model_type,
                "training_samples": len(train_series),
                "validation_samples": len(val_series) if val_series else 0,
                "training_metrics": training_metrics,
                "model_parameters": self.model_params,
                "training_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise ValueError(f"Model training failed: {e}")
    
    def _calculate_training_metrics(self, 
                                  train_series: TimeSeries, 
                                  val_series: Optional[TimeSeries]) -> Dict[str, float]:
        """Calculate training and validation metrics."""
        metrics = {}
        
        try:
            # Training metrics
            train_pred = self.model.predict(n=len(train_series), series=train_series)
            metrics['train_mape'] = round(mape(train_series, train_pred), 2)
            metrics['train_rmse'] = round(rmse(train_series, train_pred), 2)
            metrics['train_mae'] = round(mae(train_series, train_pred), 2)
            
            # Validation metrics if available
            if val_series is not None:
                val_pred = self.model.predict(n=len(val_series), series=train_series)
                metrics['val_mape'] = round(mape(val_series, val_pred), 2)
                metrics['val_rmse'] = round(rmse(val_series, val_pred), 2)
                metrics['val_mae'] = round(mae(val_series, val_pred), 2)
                
        except Exception as e:
            logger.warning(f"Could not calculate training metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics


    def validate_model_backtest(self, target_series: TimeSeries, covariates: TimeSeries, start_date: float = 0.9, horizon: int = 30) -> Dict[str, float]:
        """
        Performs robust time-series backtesting using Darts.
        
        This simulates making predictions historically and is the gold standard 
        for evaluating forecasting accuracy in a deployment setting.
        
        Args:
            target_series: The full historical TimeSeries.
            covariates: The full historical and future covariates.
            start_date: Fraction (0.0 to 1.0) of the target series to use for the initial training set.
            horizon: How many days to forecast in each step of the backtest.
            
        Returns:
            A dictionary of average evaluation metrics (MAPE, RMSE) over the backtest period.
        """
        if self.model is None:
            raise RuntimeError("Model must be trained or loaded before validation.")
            
        logger.info(f"Starting backtest simulation with horizon={horizon} days...")
        
        # NOTE: Backtesting requires a fresh model instance to be created inside the backtest utility
        # We reuse the model parameters but initialize a new LightGBMModel instance for the utility.
        model_instance = LightGBMModel(**self.model_params)
        
        # 1. Perform backtesting
        backtest_predictions = backtest(
            series=target_series,
            model=model_instance,
            start=start_date, # Start validation after 90% of data is used for training
            forecast_horizon=horizon,
            stride=horizon, # Evaluate every 30 days
            retrain=False, # Use the model trained up to the start point (saves time)
            verbose=True,
            past_covariates=covariates # Pass all covariates for Darts to handle
        )
        
        # 2. Calculate metrics (using the median forecast, component 0.5)
        # Note: Darts automatically aligns the prediction with the target for metrics
        avg_mape = mape(target_series, backtest_predictions.univariate_component(0.5))
        avg_rmse = rmse(target_series, backtest_predictions.univariate_component(0.5))
        
        return {
            "avg_mape": round(avg_mape, 2),
            "avg_rmse": round(avg_rmse, 2),
            "backtest_note": f"Evaluated over {len(backtest_predictions)} total time steps."
        }


    def predict(self, 
                n: int, 
                future_covariates: Optional[TimeSeries] = None,
                num_samples: Optional[int] = None,
                return_components: bool = False,
                model_path: Optional[str] = None,
                use_holiday_features: bool = True,
                prediction_start_date: Optional[datetime] = None) -> Tuple[TimeSeries, pd.DataFrame]:
        """
        Enhanced prediction method with explicit model path support and automatic Indian holiday integration.
        
        Args:
            n: Number of time steps to forecast
            future_covariates: Optional future covariate time series (if None and use_holiday_features=True,
                             holiday features will be auto-generated)
            num_samples: Number of samples for probabilistic forecasting
            return_components: Whether to return individual forecast components
            model_path: Explicit path to pre-trained model file
            use_holiday_features: Whether to automatically generate Indian holiday features
            prediction_start_date: Start date for prediction (if None, will start from next day)
            
        Returns:
            Tuple of (forecast_series, forecast_dataframe)
        """
        # Try to load model if not already loaded
        if self.model is None or self.scaler is None:
            load_path = model_path or self.MODEL_FILENAME
            if not self.load_model(load_path):
                raise RuntimeError(
                    f"Model not found at {load_path}. "
                    f"Please train a model first or provide correct model path."
                )
        
        # Validate model before prediction
        validation = self.validate_model()
        if not validation["valid"]:
            raise RuntimeError(f"Model validation failed: {validation['error']}")
        
        # Auto-generate holiday-enhanced future covariates if none provided
        if future_covariates is None and use_holiday_features:
            logger.info("No future covariates provided. Generating holiday-enhanced features for prediction...")
            
            # Determine prediction start date
            if prediction_start_date is None:
                prediction_start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            end_date = prediction_start_date + timedelta(days=n)
            
            future_covariates = self.generate_holiday_enhanced_covariates(
                prediction_start_date, end_date
            )
            logger.info(f"Holiday-enhanced future covariates generated for {n} days starting from {prediction_start_date}")
        elif use_holiday_features and future_covariates is not None:
            logger.info("Future covariates provided. Consider using generate_holiday_enhanced_covariates() for better holiday-aware predictions.")
        
        # Use configured number of samples if not specified
        if num_samples is None:
            num_samples = self.config['prediction']['num_samples']
        
        logger.info(f"Generating {n}-day forecast using {self.model_type} model with {num_samples} samples...")

        try:
            # 1. Generate the forecast (on scaled data)
            predict_params = {
                'n': n,
                'num_samples': num_samples
            }
            
            if future_covariates is not None:
                predict_params['future_covariates'] = future_covariates
            
            scaled_forecast = self.model.predict(**predict_params)
            
            # 2. Inverse transform the forecast back to the original scale
            forecast = self.scaler.inverse_transform(scaled_forecast)
            
            # 3. Prepare enhanced summary DataFrame
            df_forecast = self._prepare_forecast_dataframe(forecast, return_components)
            
            # 4. Add forecast metadata
            forecast_metadata = {
                'model_type': self.model_type,
                'forecast_horizon_days': n,
                'confidence_intervals': self.config['prediction']['confidence_intervals'],
                'num_samples': num_samples,
                'forecast_date': datetime.now().isoformat(),
                'forecast_start': df_forecast['date'].iloc[0],
                'forecast_end': df_forecast['date'].iloc[-1]
            }
            
            logger.info(f"Forecast generated successfully: {forecast_metadata['forecast_start']} to {forecast_metadata['forecast_end']}")
            
            return forecast, df_forecast
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise ValueError(f"Forecast generation failed: {e}")
    
    def _prepare_forecast_dataframe(self, 
                                   forecast: TimeSeries, 
                                   return_components: bool = False) -> pd.DataFrame:
        """Prepare forecast DataFrame with enhanced formatting and metadata."""
        df_forecast = forecast.pd_dataframe().reset_index()
        
        # Rename columns based on confidence intervals
        confidence_intervals = self.config['prediction']['confidence_intervals']
        column_mapping = {'time': 'date'}
        
        for i, ci in enumerate(confidence_intervals):
            if ci == 0.5:
                column_mapping[f'component_{ci}'] = 'forecast_revenue'
            else:
                column_mapping[f'component_{ci}'] = f'bound_{ci}'
        
        df_forecast = df_forecast.rename(columns=column_mapping)
        
        # Add additional metrics
        if 'forecast_revenue' in df_forecast.columns:
            # Calculate forecast confidence width
            lower_bound = df_forecast.get('bound_0.05', df_forecast['forecast_revenue'])
            upper_bound = df_forecast.get('bound_0.95', df_forecast['forecast_revenue'])
            df_forecast['confidence_width'] = (upper_bound - lower_bound).round(2)
            df_forecast['confidence_width_pct'] = (
                (df_forecast['confidence_width'] / df_forecast['forecast_revenue'] * 100)
            ).round(1)
        
        # Format date column
        df_forecast['date'] = df_forecast['date'].dt.strftime('%Y-%m-%d')
        
        # Round numeric columns
        numeric_cols = df_forecast.select_dtypes(include=[np.number]).columns
        df_forecast[numeric_cols] = df_forecast[numeric_cols].round(2)
        
        return df_forecast

    
    def get_upcoming_indian_holidays(self, 
                                   days_ahead: int = 90,
                                   start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get upcoming Indian holidays using the holidays library for accurate dates.
        
        Args:
            days_ahead: Number of days to look ahead for holidays
            start_date: Start date for holiday lookup (default: today)
            
        Returns:
            Dictionary with upcoming holidays and business insights
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_date = start_date + timedelta(days=days_ahead)
        
        logger.info(f"Retrieving upcoming Indian holidays from {start_date} to {end_date}")
        
        # Get holidays for the relevant years using holidays library
        years = list(set([start_date.year, end_date.year]))
        all_holidays = {}
        
        for year in years:
            india_holidays = holidays.India(years=year)
            for date, name in india_holidays.items():
                if start_date.date() <= date <= end_date.date():
                    all_holidays[date] = name
        
        # Extract upcoming holidays
        upcoming_holidays = []
        
        for holiday_date, holiday_name in all_holidays.items():
            days_until = (holiday_date - start_date.date()).days
            
            # Determine holiday impact level using the major commercial holidays list
            impact_level = "High" if any(major in holiday_name.lower() 
                                       for major in self.holiday_calendar.major_commercial_holidays) else "Medium"
            
            upcoming_holidays.append({
                'name': holiday_name,
                'date': holiday_date.strftime('%Y-%m-%d'),
                'days_until': days_until,
                'impact_level': impact_level,
                'day_of_week': holiday_date.strftime('%A'),
                'is_weekend': holiday_date.weekday() >= 5
            })
        
        # Sort by date
        upcoming_holidays.sort(key=lambda x: x['days_until'])
        
        # Generate holiday features for shopping season analysis
        holiday_features = self.holiday_calendar.generate_holiday_features(start_date, end_date)
        
        # Get shopping seasons
        shopping_periods = []
        shopping_season_rows = holiday_features[holiday_features['is_shopping_season'] == 1]
        
        if not shopping_season_rows.empty:
            # Group consecutive shopping season days
            current_period_start = None
            current_period_end = None
            
            for _, row in shopping_season_rows.iterrows():
                if current_period_start is None:
                    current_period_start = row['date']
                    current_period_end = row['date']
                elif (row['date'] - current_period_end).days <= 1:
                    current_period_end = row['date']
                else:
                    # End current period and start new one
                    shopping_periods.append({
                        'start_date': current_period_start.strftime('%Y-%m-%d'),
                        'end_date': current_period_end.strftime('%Y-%m-%d'),
                        'duration_days': (current_period_end - current_period_start).days + 1,
                        'season_type': self._identify_shopping_season_type(current_period_start)
                    })
                    current_period_start = row['date']
                    current_period_end = row['date']
            
            # Add the last period
            if current_period_start is not None:
                shopping_periods.append({
                    'start_date': current_period_start.strftime('%Y-%m-%d'),
                    'end_date': current_period_end.strftime('%Y-%m-%d'),
                    'duration_days': (current_period_end - current_period_start).days + 1,
                    'season_type': self._identify_shopping_season_type(current_period_start)
                })
        
        # Enhanced business insights
        high_impact_holidays = [h for h in upcoming_holidays if h['impact_level'] == 'High']
        weekend_holidays = [h for h in upcoming_holidays if h['is_weekend']]
        
        insights = {
            'total_holidays': len(upcoming_holidays),
            'high_impact_holidays': len(high_impact_holidays),
            'weekend_holidays': len(weekend_holidays),
            'next_major_holiday': high_impact_holidays[0] if high_impact_holidays else None,
            'shopping_seasons': len(shopping_periods),
            'peak_shopping_days': sum([p['duration_days'] for p in shopping_periods]),
            'festival_season_coverage': self._calculate_festival_season_coverage(holiday_features),
            'commercial_impact_score': round(holiday_features['commercial_impact_score'].mean(), 2)
        }
        
        result = {
            'lookup_period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days_covered': days_ahead
            },
            'upcoming_holidays': upcoming_holidays,
            'shopping_periods': shopping_periods,
            'business_insights': insights,
            'recommendations': self._generate_enhanced_holiday_recommendations(upcoming_holidays, shopping_periods, insights)
        }
        
        logger.info(f"Found {len(upcoming_holidays)} upcoming holidays and {len(shopping_periods)} shopping periods")
        return result
    
    def _identify_shopping_season_type(self, date: datetime) -> str:
        """Identify the type of shopping season based on date."""
        month = date.month
        
        if month in [10, 11]:
            return "Diwali Season"
        elif month in [11, 12, 1, 2]:
            return "Wedding Season"
        elif month in [4, 5]:
            return "Summer Sale"
        elif month in [12, 1]:
            return "New Year Season"
        else:
            return "General Shopping"
    
    def _calculate_festival_season_coverage(self, holiday_features: pd.DataFrame) -> float:
        """Calculate what percentage of the period falls in festival season."""
        total_days = len(holiday_features)
        festival_days = holiday_features['is_festival_season'].sum()
        return round((festival_days / total_days) * 100, 1) if total_days > 0 else 0.0
    
    def _generate_enhanced_holiday_recommendations(self, 
                                                 holidays: List[Dict], 
                                                 shopping_periods: List[Dict],
                                                 insights: Dict[str, Any]) -> List[str]:
        """Generate enhanced business recommendations based on upcoming holidays."""
        recommendations = []
        
        if not holidays:
            recommendations.append("No major holidays in the forecast period. Focus on regular seasonal trends and promotional opportunities.")
            return recommendations
        
        # High-impact holiday recommendations
        high_impact_holidays = [h for h in holidays if h['impact_level'] == 'High']
        if high_impact_holidays:
            next_holiday = high_impact_holidays[0]
            recommendations.append(
                f"🎯 Major holiday alert: {next_holiday['name']} in {next_holiday['days_until']} days "
                f"({next_holiday['day_of_week']}). Expected high sales impact - prepare inventory and marketing campaigns."
            )
        
        # Weekend holiday opportunities
        weekend_holidays = [h for h in holidays if h['is_weekend']]
        if weekend_holidays:
            recommendations.append(
                f"📅 {len(weekend_holidays)} holidays fall on weekends, creating extended shopping opportunities. "
                f"Plan for increased foot traffic and longer shopping periods."
            )
        
        # Shopping season strategy
        if shopping_periods:
            longest_period = max(shopping_periods, key=lambda x: x['duration_days'])
            recommendations.append(
                f"🛍️ Peak shopping period: {longest_period['season_type']} "
                f"({longest_period['start_date']} to {longest_period['end_date']}, {longest_period['duration_days']} days). "
                f"Maximize inventory and promotional activities."
            )
        
        # Commercial impact insights
        if insights['commercial_impact_score'] > 5.0:
            recommendations.append(
                f"💰 High commercial impact period (score: {insights['commercial_impact_score']}/10). "
                f"Expect significant revenue opportunities - consider premium pricing and exclusive offers."
            )
        elif insights['commercial_impact_score'] > 3.0:
            recommendations.append(
                f"📈 Moderate commercial impact expected (score: {insights['commercial_impact_score']}/10). "
                f"Good opportunity for targeted promotions and customer engagement."
            )
        
        # Festival season coverage
        if insights['festival_season_coverage'] > 50:
            recommendations.append(
                f"🎭 {insights['festival_season_coverage']}% of period falls in festival season. "
                f"Implement festive themes, special collections, and cultural marketing strategies."
            )
        
        # Clustering analysis
        clustered_holidays = []
        for i, holiday in enumerate(holidays[:-1]):
            next_holiday = holidays[i + 1]
            if next_holiday['days_until'] - holiday['days_until'] <= 7:
                clustered_holidays.extend([holiday, next_holiday])
        
        if len(set(h['name'] for h in clustered_holidays)) >= 2:
            recommendations.append(
                f"🎪 Multiple holidays clustered within 7 days. Plan for sustained high-demand period "
                f"with adequate staffing and inventory buffers."
            )
        
        return recommendations
    def get_model_metrics(self, actual_series: TimeSeries, forecast_series: TimeSeries) -> Dict[str, float]:
        """
        Calculates key accuracy metrics for a simple train/test split evaluation.
        """
        # Ensure series are aligned before calculating metrics
        actual_aligned, forecast_aligned = actual_series.align(forecast_series)
        
        return {
            "mape": round(mape(actual_aligned, forecast_aligned), 2),
            "rmse": round(rmse(actual_aligned, forecast_aligned), 2)
        }

# Convenience function for creating Indian market-optimized forecaster
def create_indian_market_forecaster(model_type: str = 'lightgbm',
                                  input_chunk_length: int = 45,
                                  output_chunk_length: int = 90,
                                  config_file: Optional[str] = None) -> SalesForecaster:
    """
    Create a SalesForecaster optimized for the Indian market with holiday integration.
    
    Args:
        model_type: Type of model ('lightgbm', 'random_forest', 'linear_regression')
        input_chunk_length: Historical data points (increased for holiday patterns)
        output_chunk_length: Forecast horizon days
        config_file: Optional configuration file path
        
    Returns:
        Configured SalesForecaster instance
    """
    logger.info("Creating Indian market-optimized sales forecaster...")
    
    forecaster = SalesForecaster(
        model_type=model_type,
        input_chunk_length=input_chunk_length,
        output_chunk_length=output_chunk_length,
        config_file=config_file,
        enable_auto_tuning=True,
        log_level='INFO'
    )
    
    logger.info(f"Indian market forecaster created with holiday calendar support")
    logger.info(f"Model: {model_type}, Input: {input_chunk_length} days, Output: {output_chunk_length} days")
    
    return forecaster

# Example usage and testing
if __name__ == "__main__":
    # Example of how to use the enhanced forecaster with holidays library
    print("Indian Holiday-Enhanced Sales Forecaster (using Python holidays library)")
    print("="*75)
    
    # Create forecaster
    forecaster = create_indian_market_forecaster()
    
    # Show upcoming holidays using the holidays library
    upcoming = forecaster.get_upcoming_indian_holidays(days_ahead=180)
    print(f"\nUpcoming holidays in next 180 days: {upcoming['business_insights']['total_holidays']}")
    print(f"High impact holidays: {upcoming['business_insights']['high_impact_holidays']}")
    print(f"Commercial impact score: {upcoming['business_insights']['commercial_impact_score']}")
    
    # Show some upcoming holidays
    if upcoming['upcoming_holidays']:
        print("\nNext 5 holidays:")
        for holiday in upcoming['upcoming_holidays'][:5]:
            print(f"  • {holiday['name']} - {holiday['date']} ({holiday['days_until']} days, {holiday['impact_level']} impact)")
    
    # Show holiday features for current month
    start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=30)
    holiday_features = forecaster.holiday_calendar.generate_holiday_features(start_date, end_date)
    
    print(f"\nHoliday features generated: {len(holiday_features.columns)} features")
    print(f"Days with holidays this month: {holiday_features['is_holiday'].sum()}")
    print(f"Days in shopping season: {holiday_features['is_shopping_season'].sum()}")
    print(f"Average commercial impact score: {holiday_features['commercial_impact_score'].mean():.2f}")
    
    # Show holiday summary for current year
    year_summary = forecaster.holiday_calendar.get_holiday_summary(datetime.now().year)
    print(f"\n{year_summary['year']} Holiday Summary:")
    print(f"  Total holidays: {year_summary['total_holidays']}")
    print(f"  Major commercial holidays: {year_summary['major_commercial_holidays']}")
    print(f"  Festival holidays: {year_summary['festival_holidays']}")
    print(f"  Government holidays: {year_summary['government_holidays']}")
    
    # Show recommendations
    if upcoming['recommendations']:
        print(f"\nBusiness Recommendations:")
        for i, rec in enumerate(upcoming['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
    
    print(f"\n✅ Indian market forecaster ready with comprehensive holiday support!")
    print(f"📅 Using Python holidays library for accurate {datetime.now().year} holiday dates")
    print(f"🎯 Enhanced with commercial impact scoring and business intelligence")