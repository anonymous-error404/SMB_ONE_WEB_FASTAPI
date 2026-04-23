from fastapi import FastAPI, HTTPException, Depends, Query, Body, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import logging
import os
from datetime import datetime, date
import uvicorn

# Import our enhanced modules
from data_pipeline.data_processor import DataProcessor
from analytics.sales_analytics import get_revenue_trends, get_product_performance, get_customer_segmentation
from analytics.financials_analytics import get_cash_flow_prediction, get_expense_breakdown, get_receivables_aging, get_payment_patterns
from analytics.inventory_analytics import get_inventory_turnover, get_slow_moving_alerts, get_stock_recommendations
# from models.sales_forecaster import SalesForecaster  # Using simple_forecaster.py instead
from simple_forecaster import get_sales_forecast as get_forecast_from_model

# Import database functions
from database import (
    get_dashboard_stats,
    get_monthly_revenue,
    get_inventory_stats,
    get_category_data,
    get_stock_data,
    get_low_stock_items,
    get_cash_flow_data,
    get_transactions,
    get_insights_stats,
    get_performance_data,
    get_business_metrics,
    get_sales_forecast,
    get_contracts,
    get_sales_dataframe,
    get_products_dataframe,
    get_all_products,
    get_transactions_dataframe,
    get_db
)
import psycopg2
import psycopg2.extras
import hashlib
import base64
import time

def get_user_id_from_token(auth_header: Optional[str]):
    """Decode our simple base64 token and return user id from users table.
    Returns None if token missing/invalid or user not found.
    """
    if not auth_header:
        return None
    try:
        # support "Bearer <token>" and raw token
        token = auth_header.split(" ")[-1]
        decoded = base64.b64decode(token).decode()
        email = decoded.split(":")[0]
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row:
                return row['id']
    except Exception:
        return None
    return None

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

# Initialize FastAPI app
app = FastAPI(
    title="Business Insights API",
    description="Dynamic business analytics and forecasting API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/auth/register")
async def register_endpoint(payload: Dict[str, Any] = Body(...)):
    """Register a new user. Stores name, email, hashed password, and security question/answer."""
    name = payload.get('name')
    email = payload.get('email')
    password = payload.get('password')
    security_question = payload.get('securityQuestion')
    security_answer = payload.get('securityAnswer')
    
    if not name or not email or not password or not security_question or not security_answer:
        raise HTTPException(status_code=400, detail="name, email, password, securityQuestion and securityAnswer are required")

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Create users table if missing with security fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT UNIQUE,
                    password TEXT,
                    security_question TEXT,
                    security_answer TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check if security fields exist, if not add them
            cursor.execute("SELECT column_name as name FROM information_schema.columns WHERE table_name = 'users'")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'security_question' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
            if 'security_answer' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            hashed_answer = hashlib.sha256(security_answer.lower().strip().encode()).hexdigest()
            
            cursor.execute(
                "INSERT INTO users (name, email, password, security_question, security_answer) VALUES (%s, %s, %s, %s, %s) RETURNING id", 
                (name, email, hashed_password, security_question, hashed_answer)
            )
            user_id = cursor.fetchone()['id']
            conn.commit()

            token = base64.b64encode(f"{email}:{int(time.time())}".encode()).decode()

            return JSONResponse(content={
                "success": True,
                "data": {"token": token, "user": {"id": user_id, "name": name, "email": email}},
                "metadata": {"created_at": datetime.now().isoformat()}
            })
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
async def login_endpoint(payload: Dict[str, Any] = Body(...)):
    """Authenticate user and return a simple token."""
    print(payload)  # Debugging statement to check incoming payload
    email = payload.get('email')
    password = payload.get('password')
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, password FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            if not row:
                print("Invalid credentials: email not found")
                raise HTTPException(status_code=401, detail="Invalid credentials")
            stored_hash = row['password']
            provided_hash = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash != provided_hash:
                print("Invalid credentials: password mismatch")
                raise HTTPException(status_code=401, detail="Invalid credentials")

            token = base64.b64encode(f"{email}:{int(time.time())}".encode()).decode()
            user = {"id": row['id'], "name": row['name'], "email": row['email']}

            return JSONResponse(content={
                "success": True,
                "data": {"token": token, "user": user},
                "metadata": {"authenticated_at": datetime.now().isoformat()}
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/security-question")
async def get_security_question_endpoint(email: str = Query(...)):
    """Get the security question for a user's email."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT security_question FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Email not found")
            
            return JSONResponse(content={
                "success": True,
                "data": {"securityQuestion": row['security_question']},
                "metadata": {}
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get security question failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/forgot-password")
async def forgot_password_endpoint(payload: Dict[str, Any] = Body(...)):
    """Reset password using security question verification."""
    email = payload.get('email')
    security_answer = payload.get('securityAnswer')
    new_password = payload.get('newPassword')
    
    if not email or not security_answer or not new_password:
        raise HTTPException(status_code=400, detail="email, securityAnswer and newPassword are required")

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, security_answer FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Verify security answer
            provided_answer_hash = hashlib.sha256(security_answer.lower().strip().encode()).hexdigest()
            if row['security_answer'] != provided_answer_hash:
                raise HTTPException(status_code=401, detail="Incorrect security answer")
            
            # Update password
            new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password_hash, email))
            conn.commit()
            
            # Generate new token for automatic login
            token = base64.b64encode(f"{email}:{int(time.time())}".encode()).decode()
            
            return JSONResponse(content={
                "success": True,
                "data": {
                    "message": "Password reset successfully",
                    "token": token,
                    "user": {"id": row['id'], "name": row['name'], "email": email}
                },
                "metadata": {"reset_at": datetime.now().isoformat()}
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global instances (in production, these would be dependency injected)
data_processor = None
sales_forecaster = None

# Pydantic models for request/response validation
class SalesDataRequest(BaseModel):
    """Request model for sales data analysis."""
    data: List[Dict[str, Any]] = Field(..., description="Sales transaction data")
    lookback_days: int = Field(30, ge=1, le=365, description="Number of days to look back")
    include_ytd: bool = Field(True, description="Include year-to-date metrics")
    include_quarterly: bool = Field(False, description="Include quarterly metrics")
    
    @validator('data')
    def validate_data_not_empty(cls, v):
        if not v:
            raise ValueError('Data cannot be empty')
        return v

class ProductPerformanceRequest(BaseModel):
    """Request model for product performance analysis."""
    data: List[Dict[str, Any]] = Field(..., description="Product sales data")
    top_n: int = Field(5, ge=1, le=50, description="Number of top/bottom products to return")
    sort_by: str = Field('revenue', description="Metric to sort by")
    include_velocity: bool = Field(True, description="Include sales velocity metrics")
    include_margins: bool = Field(True, description="Include profit margin metrics")
    min_transactions: int = Field(1, ge=1, description="Minimum transactions per product")

class ForecastingRequest(BaseModel):
    """Request model for sales forecasting."""
    data: List[Dict[str, Any]] = Field(..., description="Historical sales data")
    forecast_days: int = Field(90, ge=1, le=365, description="Number of days to forecast")
    model_type: str = Field('lightgbm', description="Model type to use")
    target_column: str = Field('revenue', description="Column to forecast")
    frequency: str = Field('D', description="Time series frequency")
    include_holidays: bool = Field(True, description="Include holiday features")
    include_time_features: bool = Field(True, description="Include time-based features")

class DashboardRequest(BaseModel):
    """Request model for dashboard data."""
    data: List[Dict[str, Any]] = Field(..., description="Transaction/sales data")
    lookback_days: int = Field(30, ge=1, le=365, description="Days to analyze")

class InventoryRequest(BaseModel):
    """Request model for inventory data."""
    data: List[Dict[str, Any]] = Field(..., description="Inventory/product data")
    low_stock_threshold: int = Field(10, ge=1, description="Stock level threshold")

class FinancialRequest(BaseModel):
    """Request model for financial data."""
    data: List[Dict[str, Any]] = Field(..., description="Financial transaction data")
    months: int = Field(6, ge=1, le=24, description="Number of months")

class ContractRequest(BaseModel):
    """Request model for contract data."""
    data: List[Dict[str, Any]] = Field(..., description="Contract data")

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]

# Dependency functions
def get_data_processor() -> DataProcessor:
    """Get or create data processor instance."""
    global data_processor
    if data_processor is None:
        data_processor = DataProcessor(
            country=os.getenv('COUNTRY', 'IN'),
            forecast_days=int(os.getenv('FORECAST_DAYS', '90')),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )
    return data_processor

# Removed get_sales_forecaster() - using simple_forecaster.py directly instead

# Utility functions
def convert_to_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert list of dictionaries to DataFrame with validation."""
    try:
        df = pd.DataFrame(data)
        if df.empty:
            raise ValueError("DataFrame is empty")
        return df
    except Exception as e:
        logger.error(f"Failed to convert data to DataFrame: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid data format: {e}")

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Business Insights API v2.0",
        "docs": "/docs",
        "health": "/health",
        "status": "operational"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check data processor
        dp = get_data_processor()
        dp_status = "healthy"
        
        # Check forecaster (simple_forecaster)
        from simple_forecaster import get_forecaster
        sf = get_forecaster()
        sf_status = "healthy" if sf.model is not None else "model_not_loaded"
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="2.0.0",
            services={
                "data_processor": dp_status,
                "sales_forecaster": sf_status,
                "database": "not_implemented",  # Would check DB connection in production
                "cache": "not_implemented"  # Would check Redis/cache in production
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.post("/analytics/revenue-trends")
async def analyze_revenue_trends(request: SalesDataRequest = None):
    """Dynamic revenue trends analysis endpoint using database data."""
    try:
        lookback_days = request.lookback_days if request else 365
        include_ytd = request.include_ytd if request else True
        include_quarterly = request.include_quarterly if request else True
        
        logger.info(f"Processing revenue trends from database (lookback: {lookback_days} days)")
        
        # Get sales data from database
        from database import get_sales_dataframe
        df = get_sales_dataframe()
        
        # Perform analysis
        results = get_revenue_trends(
            df_transactions=df,
            lookback_days=lookback_days,
            include_ytd=include_ytd,
            include_quarterly=include_quarterly
        )
        
        return JSONResponse(content={
            "success": True,
            "data": results,
            "metadata": {
                "request_id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "processed_at": datetime.now().isoformat(),
                "records_processed": len(df),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Revenue trends analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

@app.post("/analytics/product-performance")
async def analyze_product_performance(request: ProductPerformanceRequest = None):
    """Dynamic product performance analysis endpoint using database data."""
    try:
        top_n = request.top_n if request else 10
        sort_by = request.sort_by if request else 'revenue'
        include_velocity = request.include_velocity if request else True
        include_margins = request.include_margins if request else True
        min_transactions = request.min_transactions if request else 5
        
        logger.info(f"Processing product performance from database (top {top_n})")
        
        # Get sales data from database
        from database import get_sales_dataframe
        df = get_sales_dataframe()
        
        # Perform analysis
        results = get_product_performance(
            df_transactions=df,
            top_n=top_n,
            sort_by=sort_by,
            include_velocity=include_velocity,
            include_margins=include_margins,
            min_transactions=min_transactions
        )
        
        return JSONResponse(content={
            "success": True,
            "data": results,
            "metadata": {
                "request_id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "processed_at": datetime.now().isoformat(),
                "records_processed": len(df),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Product performance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

@app.post("/analytics/customer-segmentation")
async def analyze_customer_segmentation(
    data: List[Dict[str, Any]] = Body(None, description="Customer transaction data (optional, will use database if not provided)"),
    segment_column: str = Query('customer_segment', description="Column to use for segmentation"),
    include_aov: bool = Query(True, description="Include average order value metrics"),
    include_frequency: bool = Query(True, description="Include frequency metrics"),
    min_segment_size: int = Query(1, ge=1, description="Minimum segment size")
):
    """Dynamic customer segmentation analysis endpoint using database data."""
    try:
        logger.info("Processing customer segmentation from database")
        
        # Get sales data from database
        from database import get_sales_dataframe
        df = get_sales_dataframe()
        
        # Perform analysis
        results = get_customer_segmentation(
            df_transactions=df,
            segment_column=segment_column,
            include_aov=include_aov,
            include_frequency=include_frequency,
            min_segment_size=min_segment_size
        )
        
        return JSONResponse(content={
            "success": True,
            "data": results,
            "metadata": {
                "request_id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "processed_at": datetime.now().isoformat(),
                "records_processed": len(df),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Customer segmentation analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

@app.post("/forecasting/sales-forecast")
async def generate_sales_forecast(
    request: ForecastingRequest = None,
    authorization: Optional[str] = Header(None)
):
    """Fast sales forecasting using pre-trained model from models folder with database data."""
    try:
        forecast_days = request.forecast_days if request else 7
        user_id = get_user_id_from_token(authorization)
        logger.info(f"Generating {forecast_days}-day forecast using pre-trained model for user {user_id}")
        
        # Use simple_forecaster to load and use the .pkl model
        forecast_result = get_forecast_from_model(days=forecast_days, user_id=user_id)
        
        if not forecast_result.get("success", False):
            error_msg = forecast_result.get("error", "Unknown error")
            logger.warning(f"Forecast generation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Forecasting failed: {error_msg}")
        
        # Return the forecast data
        return JSONResponse(content=forecast_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sales forecasting failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {e}")

@app.post("/forecasting/train-model")
async def train_forecasting_model(
    request: ForecastingRequest = None,
    dp: DataProcessor = Depends(get_data_processor)
):
    """
    Train and save the forecasting model using database data (run once or periodically).
    Note: This endpoint is deprecated in favor of using pre-trained sale_forecaster.pkl.
    Model training is complex and should be done offline with train_model.py script.
    """
    return JSONResponse(content={
        "success": False,
        "message": "Model training endpoint is deprecated. Using pre-trained sale_forecaster.pkl instead.",
        "recommendation": "The application now uses pre-trained models from the models/ folder for faster performance. If you need to retrain, run train_model.py script directly."
    }, status_code=501)

@app.get("/forecasting/model-status")
async def get_model_status():
    """Check the status of the pre-trained model."""
    import os
    model_path = "models/sale_forecaster.pkl"
    scaler_path = "models/sale_forecaster_scaler.pkl"
    
    model_exists = os.path.exists(model_path)
    scaler_exists = os.path.exists(scaler_path)
    
    if model_exists and scaler_exists:
        model_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_path))
        return {
            "model_exists": True,
            "scaler_exists": True,
            "model_path": model_path,
            "scaler_path": scaler_path,
            "model_age_days": model_age.days,
            "model_size_mb": round(os.path.getsize(model_path) / (1024*1024), 2),
            "status": "ready_for_predictions",
            "message": "Pre-trained model and scaler are ready"
        }
    else:
        return {
            "model_exists": model_exists,
            "scaler_exists": scaler_exists,
            "model_path": model_path,
            "scaler_path": scaler_path,
            "status": "model_not_found" if not model_exists else "scaler_not_found",
            "message": f"Missing files: {', '.join([p for p, exists in [(model_path, model_exists), (scaler_path, scaler_exists)] if not exists])}"
        }

@app.get("/forecasting/available-models")
async def get_available_models():
    """List all available trained models in the models folder."""
    import os
    import glob
    
    models_dir = "models"
    if not os.path.exists(models_dir):
        return {"models": [], "message": "No models folder found"}
    
    model_files = glob.glob(f"{models_dir}/*.pkl")
    models = []
    
    for model_file in model_files:
        model_name = os.path.basename(model_file)
        model_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_file))
        models.append({
            "name": model_name,
            "path": model_file,
            "age_days": model_age.days,
            "size_mb": round(os.path.getsize(model_file) / (1024*1024), 2)
        })
    
    return {"models": models, "total_models": len(models)}

@app.get("/config")
async def get_configuration():
    """Get current system configuration."""
    return {
        "environment": {
            "country": os.getenv('COUNTRY', 'IN'),
            "forecast_days": int(os.getenv('FORECAST_DAYS', '90')),
            "model_type": os.getenv('MODEL_TYPE', 'lightgbm'),
            "log_level": os.getenv('LOG_LEVEL', 'INFO')
        },
        "api": {
            "version": "2.0.0",
            "docs_url": "/docs",
            "health_url": "/health"
        }
    }

# ==================== FRONTEND INTEGRATION ENDPOINTS ====================
# These endpoints provide data in the format expected by the React frontend

@app.get("/api/dashboard/stats")
async def dashboard_stats_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get comprehensive dashboard statistics from database.
    Returns all metrics needed for the Dashboard page.
    """
    try:
        logger.info("Fetching dashboard stats from database")

        # Resolve user id (if provided via Authorization header)
        user_id = get_user_id_from_token(authorization)
        # Get stats from database
        from database import get_dashboard_stats as fetch_dashboard_stats
        stats = fetch_dashboard_stats(user_id=user_id)

        return JSONResponse(content={
            "success": True,
            "data": stats,
            "metadata": {
                "request_id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })

    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard stats failed: {e}")

@app.get("/api/dashboard/revenue")
async def monthly_revenue_endpoint(
    months: int = Query(6, ge=1, le=24, description="Number of months to return"),
    authorization: Optional[str] = Header(None)
):
    """
    Get monthly revenue data for charts from database.
    """
    try:
        logger.info(f"Fetching monthly revenue for {months} months from database")
        
        # Get monthly revenue from database (respect user if Authorization present)
        from database import get_monthly_revenue as fetch_monthly_revenue
        user_id = get_user_id_from_token(authorization)
        result = fetch_monthly_revenue(months, user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "months": months,
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Monthly revenue failed: {e}")
        raise HTTPException(status_code=500, detail=f"Monthly revenue failed: {e}")

@app.get("/api/inventory/stats")
async def inventory_stats_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get inventory statistics for the Inventory page from database.
    """
    try:
        logger.info("Fetching inventory stats from database")
        
        # Support optional user scoping via Authorization header
        from database import get_inventory_stats as fetch_inventory_stats
        user_id = get_user_id_from_token(authorization)
        stats = fetch_inventory_stats(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": stats,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Inventory stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Inventory stats failed: {e}")

@app.get("/api/inventory/categories")
async def category_distribution_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get product category distribution for pie charts from database.
    """
    try:
        logger.info("Fetching category distribution from database")
        
        from database import get_category_data as fetch_category_data
        user_id = get_user_id_from_token(authorization)
        result = fetch_category_data(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Category distribution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Category distribution failed: {e}")

@app.get("/api/inventory/stock-levels")
async def stock_levels_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get stock vs sales comparison for bar charts from database.
    """
    try:
        logger.info("Fetching stock level comparison from database")
        
        from database import get_stock_data as fetch_stock_data
        user_id = get_user_id_from_token(authorization)
        result = fetch_stock_data(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Stock comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stock comparison failed: {e}")

@app.get("/api/inventory/low-stock")
async def low_stock_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get products with low stock levels for alerts table from database.
    """
    try:
        logger.info("Fetching low stock items from database")
        
        from database import get_low_stock_items as fetch_low_stock
        user_id = get_user_id_from_token(authorization)
        result = fetch_low_stock(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(result),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Low stock items failed: {e}")
        raise HTTPException(status_code=500, detail=f"Low stock items failed: {e}")

@app.get("/api/inventory/items")
async def get_inventory_items(request: Request):
    """Get all inventory items"""
    try:
        # For now, get all products without user filtering since DB schema doesn't have user_id
        result = get_all_products(None)
        
        return JSONResponse({
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(result),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Get inventory items failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get inventory items failed: {e}")

@app.post("/api/inventory/items")
async def add_inventory_item_endpoint(
    item_data: dict = Body(...),
    authorization: Optional[str] = Header(None)
):
    """
    Add a new inventory item to the database.
    """
    try:
        # For now, skip user authentication since the DB schema doesn't have user_id in products table
        logger.info(f"Adding inventory item: {item_data.get('name', 'Unknown')}")
        
        # Validate required fields
        required_fields = ['name', 'category', 'price', 'cost', 'stock']
        for field in required_fields:
            if field not in item_data or item_data[field] is None:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Insert into database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, category, sku, price, cost, stock, reorder_level, supplier_id, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                item_data['name'],
                item_data['category'],
                item_data.get('sku', f"SKU-{item_data['name'][:3].upper()}-{hash(item_data['name']) % 10000:04d}"),
                float(item_data['price']),
                float(item_data['cost']),
                int(item_data['stock']),
                int(item_data.get('reorderLevel', 10)),
                item_data.get('supplier_id', 1),  # Default to first supplier
                1  # Default user_id for now
            ))
            item_id = cursor.fetchone()['id']
            conn.commit()
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "id": item_id,
                "name": item_data['name'],
                "message": "Item added successfully"
            },
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "item_id": item_id
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add inventory item failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add item: {e}")

@app.get("/api/financial/cash-flow")
async def cash_flow_endpoint(months: int = Query(6, ge=1, le=24), authorization: Optional[str] = Header(None)):
    """
    Get cash flow data (inflow/outflow) by month for financial charts from database.
    """
    try:
        logger.info(f"Fetching cash flow for {months} months from database")
        
        from database import get_cash_flow_data as fetch_cash_flow
        user_id = get_user_id_from_token(authorization)
        result = fetch_cash_flow(months, user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "months": months,
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Cash flow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cash flow failed: {e}")

@app.get("/api/financial/cash-flow-daily")
async def daily_cash_flow_endpoint(days: int = Query(7, ge=1, le=30), authorization: Optional[str] = Header(None)):
    """
    Get daily cash flow data (inflow/outflow) for last N days for financial charts from database.
    """
    try:
        logger.info(f"Fetching daily cash flow for {days} days from database")
        
        from database import get_daily_cash_flow_data
        user_id = get_user_id_from_token(authorization)
        result = get_daily_cash_flow_data(days, user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "days": days,
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Daily cash flow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Daily cash flow failed: {e}")

@app.get("/api/financial/transactions")
async def transactions_endpoint(
    limit: int = Query(10, ge=1, le=100, description="Number of transactions to return"),
    authorization: Optional[str] = Header(None)
):
    """
    Get recent financial transactions for the transactions table from database.
    """
    try:
        logger.info(f"Fetching {limit} recent transactions from database")
        
        from database import get_transactions as fetch_transactions
        user_id = get_user_id_from_token(authorization)
        result = fetch_transactions(limit, user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(result),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Transactions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transactions failed: {e}")

@app.get("/api/insights/stats")
async def insights_stats_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get insights statistics for KPI cards on Insights page from database.
    """
    try:
        logger.info("Fetching insights stats from database")
        
        from database import get_insights_stats as fetch_insights_stats
        user_id = get_user_id_from_token(authorization)
        stats = fetch_insights_stats(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": stats,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Insights stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Insights stats failed: {e}")

@app.get("/api/insights/performance")
async def performance_endpoint(
    months: int = Query(6, ge=1, le=24, description="Number of months"),
    authorization: Optional[str] = Header(None)
):
    """
    Get revenue vs profit performance data for composed charts from database.
    """
    try:
        logger.info(f"Fetching performance metrics for {months} months from database")
        
        from database import get_performance_data
        user_id = get_user_id_from_token(authorization)
        result = get_performance_data(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "months": months,
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Performance metrics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance metrics failed: {e}")

@app.get("/api/insights/sales-forecast")
async def sales_forecast_endpoint(days: int = Query(7, ge=1, le=90), authorization: Optional[str] = Header(None)):
    """
    Get AI-powered sales forecast for the next N days using pre-trained model.
    """
    try:
        logger.info(f"Generating {days}-day sales forecast")
        
        # Prefer per-user simple DB-based forecast when user scoped
        from database import get_sales_forecast as fetch_sales_forecast
        user_id = get_user_id_from_token(authorization)
        forecast_result = fetch_sales_forecast(user_id=user_id)
        
        # Debug: Check what we got
        logger.info(f"Forecast result type: {type(forecast_result)}")
        
        # The function now returns a list of daily forecasts
        if isinstance(forecast_result, list):
            return JSONResponse(content={
                "success": True,
                "data": forecast_result,
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "days": len(forecast_result),
                    "source": "database_forecast"
                }
            })
        else:
            logger.warning(f"Unexpected forecast format: {type(forecast_result)}")
            return JSONResponse(content=forecast_result, status_code=200)
            
    except Exception as e:
        logger.error(f"Sales forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sales forecast failed: {e}")

@app.get("/api/insights/business-metrics")
async def business_metrics_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get business health metrics for radar chart from database.
    Returns standardized scores (0-100) for various business metrics.
    """
    try:
        logger.info("Fetching business metrics from database")
        
        # Get business metrics from database
        from database import get_business_metrics
        user_id = get_user_id_from_token(authorization)
        metrics = get_business_metrics(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": metrics,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Business metrics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Business metrics failed: {e}")

@app.get("/api/insights/key-insights")
async def key_insights_endpoint(authorization: Optional[str] = Header(None)):
    """
    Generate AI-powered actionable insights based on sales, inventory, and forecast data.
    """
    try:
        logger.info("Generating key insights from multiple data sources")
        
        # Import required modules
        from database import get_sales_dataframe, get_inventory_stats, get_performance_data, get_sales_forecast
        from analytics.insights_generator import generate_key_insights
        user_id = get_user_id_from_token(authorization)
        # Gather data from multiple sources (scoped to user if auth provided)
        sales_df = get_sales_dataframe(user_id=user_id)
        inventory_data = get_inventory_stats(user_id=user_id)
        performance_data = get_performance_data(user_id=user_id)
        forecast_data = get_sales_forecast(user_id=user_id)
        
        # Generate insights
        insights = generate_key_insights(
            sales_df=sales_df,
            inventory_data=inventory_data,
            forecast_data=forecast_data,
            performance_data=performance_data
        )
        
        return JSONResponse(content={
            "success": True,
            "data": insights,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "insights_count": len(insights),
                "source": "ai_analysis"
            }
        })
        
    except Exception as e:
        logger.error(f"Key insights generation failed: {e}")
        # Return fallback insights
        return JSONResponse(content={
            "success": True,
            "data": [{
                'type': 'info',
                'severity': 'info',
                'icon': 'Info',
                'title': 'Insights Processing',
                'message': 'AI insights are being generated. Please check back shortly.',
                'action': 'Refresh page in a moment'
            }],
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "error": str(e)
            }
        })

@app.get("/api/insights/quick-stats")
async def quick_stats_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get quick statistics for insights page - calculated from real data (optimized query).
    """
    try:
        logger.info("Calculating quick stats from database")
        
        from database import get_db
        user_id = get_user_id_from_token(authorization)
        with get_db() as conn:
            cursor = conn.cursor()
            # Calculate average deal size with SQL (faster)
            if user_id is None:
                cursor.execute("SELECT AVG(revenue) as avg_revenue FROM sales")
            else:
                cursor.execute("SELECT AVG(revenue) as avg_revenue FROM sales WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            avg_deal_size = int(result['avg_revenue']) if result['avg_revenue'] else 0
            
            # Calculate customer retention (SQL approach)
            if user_id is None:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT customer_id) as total_customers,
                        COUNT(DISTINCT CASE WHEN purchase_count > 1 THEN customer_id END) as repeat_customers
                    FROM (
                        SELECT customer_id, COUNT(*) as purchase_count
                        FROM sales
                        GROUP BY customer_id
                    )
                """)
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT customer_id) as total_customers,
                        COUNT(DISTINCT CASE WHEN purchase_count > 1 THEN customer_id END) as repeat_customers
                    FROM (
                        SELECT customer_id, COUNT(*) as purchase_count
                        FROM sales
                        WHERE user_id = %s
                        GROUP BY customer_id
                    )
                """, (user_id,))
            retention_result = cursor.fetchone()
            total_customers = retention_result['total_customers'] or 0
            repeat_customers = retention_result['repeat_customers'] or 0
            retention_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
            
            # Calculate sales conversion (simplified)
            if user_id is None:
                cursor.execute("SELECT COUNT(*) as total_sales, COUNT(DISTINCT customer_id) as unique_customers FROM sales")
            else:
                cursor.execute("SELECT COUNT(*) as total_sales, COUNT(DISTINCT customer_id) as unique_customers FROM sales WHERE user_id = %s", (user_id,))
            conversion_result = cursor.fetchone()
            total_sales = conversion_result['total_sales'] or 0
            unique_customers = conversion_result['unique_customers'] or 1
            conversion_rate = min((total_sales / (unique_customers * 1.5) * 100), 100)
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "avgDealSize": avg_deal_size,
                "retentionRate": round(retention_rate, 1),
                "conversionRate": round(conversion_rate, 1)
            },
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "calculated"
            }
        })
        
    except Exception as e:
        logger.error(f"Quick stats calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick stats failed: {e}")

@app.get("/api/insights/milestones")
async def milestones_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get user-defined milestones with calculated progress.
    """
    try:
        user_id = get_user_id_from_token(authorization)
        logger.info(f"Fetching user milestones for user {user_id}")
        
        from database import get_milestones, calculate_milestone_progress
        
        # Get user's milestones
        milestones = get_milestones(user_id=user_id)
        
        # Calculate progress for each milestone
        milestone_data = []
        for milestone in milestones:
            milestone_item = {
                'id': milestone['id'],
                'title': milestone['title'],
                'description': milestone['description'],
                'target_value': milestone['target_value'],
                'current_value': milestone.get('current_value', 0),
                'progress_percentage': milestone.get('progress_percentage', 0),
                'target_date': milestone['target_date'],
                'milestone_type': milestone.get('milestone_type', milestone.get('unit', 'custom')),
                'status': milestone['status'],
                'priority': milestone.get('priority', 'medium'),
                'created_at': milestone['created_date'],
                'completed_date': milestone['completed_date']
            }
            milestone_data.append(milestone_item)
        
        return JSONResponse(content={
            "success": True,
            "data": milestone_data,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(milestone_data),
                "source": "user_milestones"
            }
        })
        
    except Exception as e:
        logger.error(f"Milestones fetch failed: {e}")
        return JSONResponse(content={
            "success": True,
            "data": ["Create milestones to track your progress"],
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "fallback"
            }
        })

@app.get("/api/contracts")
async def contracts_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get all contracts data for contracts page from database.
    """
    try:
        logger.info("Fetching contracts from database")
        
        # Get contracts from database
        from database import get_contracts as fetch_contracts
        user_id = get_user_id_from_token(authorization)
        result = fetch_contracts(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(result),
                "source": "database"
            }
        })
        
    except Exception as e:
        logger.error(f"Contracts failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contracts failed: {e}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "detail": str(exc)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )

# ==================== MILESTONE MANAGEMENT ENDPOINTS ====================

@app.post("/api/milestones")
async def create_milestone_endpoint(
    milestone_data: dict = Body(...),
    authorization: Optional[str] = Header(None)
):
    """Create a new milestone for the user."""
    try:
        user_id = get_user_id_from_token(authorization)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate required fields
        required_fields = ['title', 'milestone_type']
        for field in required_fields:
            if field not in milestone_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        from database import add_milestone
        
        milestone_id = add_milestone(
            title=milestone_data['title'],
            description=milestone_data.get('description', ''),
            target_value=milestone_data.get('target_value'),
            target_date=milestone_data.get('target_date'),
            milestone_type=milestone_data['milestone_type'],
            priority=milestone_data.get('priority', 'medium'),
            user_id=user_id
        )
        
        return JSONResponse(content={
            "success": True,
            "data": {"id": milestone_id, "message": "Milestone created successfully"},
            "metadata": {"processed_at": datetime.now().isoformat()}
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create milestone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create milestone: {e}")

@app.put("/api/milestones/{milestone_id}")
async def update_milestone_endpoint(
    milestone_id: int,
    updates: dict = Body(...),
    authorization: Optional[str] = Header(None)
):
    """Update a milestone (only if it belongs to the user)."""
    try:
        user_id = get_user_id_from_token(authorization)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        from database import update_milestone
        
        success = update_milestone(milestone_id, user_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Milestone not found or access denied")
        
        return JSONResponse(content={
            "success": True,
            "data": {"message": "Milestone updated successfully"},
            "metadata": {"processed_at": datetime.now().isoformat()}
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update milestone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update milestone: {e}")

@app.delete("/api/milestones/{milestone_id}")
async def delete_milestone_endpoint(
    milestone_id: int,
    authorization: Optional[str] = Header(None)
):
    """Delete a milestone (only if it belongs to the user)."""
    try:
        user_id = get_user_id_from_token(authorization)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        from database import delete_milestone
        
        success = delete_milestone(milestone_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Milestone not found or access denied")
        
        return JSONResponse(content={
            "success": True,
            "data": {"message": "Milestone deleted successfully"},
            "metadata": {"processed_at": datetime.now().isoformat()}
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete milestone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete milestone: {e}")

@app.post("/api/milestones/{milestone_id}/progress")
async def update_milestone_progress_endpoint(
    milestone_id: int,
    authorization: Optional[str] = Header(None)
):
    """Recalculate progress for a specific milestone."""
    try:
        user_id = get_user_id_from_token(authorization)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        from database import calculate_milestone_progress
        
        progress = calculate_milestone_progress(milestone_id, user_id)
        
        if progress is None:
            raise HTTPException(status_code=404, detail="Milestone not found or access denied")
        
        return JSONResponse(content={
            "success": True,
            "data": progress,
            "metadata": {"processed_at": datetime.now().isoformat()}
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update milestone progress failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update progress: {e}")

@app.get("/api/insights/product-forecast")
async def product_forecast_endpoint(
    product_id: int = Query(..., description="Product ID to forecast"),
    days: int = Query(7, ge=1, le=30, description="Number of days to forecast"),
    authorization: Optional[str] = Header(None)
):
    """
    Get sales forecast for a specific product from simple_forecaster.py
    """
    try:
        logger.info(f"Generating forecast for product {product_id} for {days} days")
        
        from simple_forecaster import generate_product_forecast
        user_id = get_user_id_from_token(authorization)
        forecast_data = generate_product_forecast(product_id, days, user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": forecast_data,
            "metadata": {
                "product_id": product_id,
                "days": days,
                "processed_at": datetime.now().isoformat(),
                "source": "darts_forecasting"
            }
        })
        
    except Exception as e:
        logger.error(f"Product forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Product forecast failed: {e}")

@app.get("/api/insights/products-list")
async def products_list_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get list of all products for forecasting dropdown
    """
    try:
        from database import get_all_products_for_forecasting
        user_id = get_user_id_from_token(authorization)
        products = get_all_products_for_forecasting(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": products,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(products)
            }
        })
        
    except Exception as e:
        logger.error(f"Products list failed: {e}")
        raise HTTPException(status_code=500, detail=f"Products list failed: {e}")

@app.get("/api/inventory/restock-recommendations")
async def restock_recommendations_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get inventory restocking recommendations based on sales patterns
    """
    try:
        from database import get_product_inventory_status
        user_id = get_user_id_from_token(authorization)
        inventory_status = get_product_inventory_status(user_id=user_id)
        
        return JSONResponse(content={
            "success": True,
            "data": inventory_status,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(inventory_status)
            }
        })
        
    except Exception as e:
        logger.error(f"Restock recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restock recommendations failed: {e}")

# ==================== BLOCKCHAIN SMART CONTRACTS ENDPOINTS ====================

@app.get("/api/blockchain/analytics")
async def blockchain_analytics_endpoint(authorization: Optional[str] = Header(None)):
    """
    Get blockchain escrow analytics for the authenticated user.
    If the user has no wallet (not onboarded), returns blockchain_enabled=False.
    """
    try:
        user_id = get_user_id_from_token(authorization)

        from database import get_user_wallet_address, get_blockchain_analytics

        wallet = None
        blockchain_enabled = False
        if user_id is not None:
            wallet = get_user_wallet_address(user_id)
            blockchain_enabled = wallet is not None

        if not blockchain_enabled:
            return JSONResponse(content={
                "success": True,
                "blockchain_enabled": False,
                "data": None,
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "message": "User has not onboarded to blockchain"
                }
            })

        analytics = get_blockchain_analytics(wallet_address=wallet)

        return JSONResponse(content={
            "success": True,
            "blockchain_enabled": True,
            "wallet_address": wallet,
            "data": analytics,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "escrow_contracts"
            }
        })

    except Exception as e:
        logger.error(f"Blockchain analytics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Blockchain analytics failed: {e}")


@app.get("/api/blockchain/contracts")
async def blockchain_contracts_endpoint(
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(None)
):
    """
    Get escrow smart contracts for the authenticated user.
    Returns blockchain_enabled=False if user has no wallet address.
    """
    try:
        user_id = get_user_id_from_token(authorization)

        from database import get_user_wallet_address, get_escrow_contracts

        wallet = None
        blockchain_enabled = False
        if user_id is not None:
            wallet = get_user_wallet_address(user_id)
            blockchain_enabled = wallet is not None

        if not blockchain_enabled:
            return JSONResponse(content={
                "success": True,
                "blockchain_enabled": False,
                "data": [],
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "message": "User has not onboarded to blockchain"
                }
            })

        contracts = get_escrow_contracts(wallet_address=wallet, limit=limit)

        return JSONResponse(content={
            "success": True,
            "blockchain_enabled": True,
            "wallet_address": wallet,
            "data": contracts,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(contracts),
                "source": "escrow_contracts"
            }
        })

    except Exception as e:
        logger.error(f"Blockchain contracts failed: {e}")
        raise HTTPException(status_code=500, detail=f"Blockchain contracts failed: {e}")


@app.get("/api/blockchain/transactions")
async def blockchain_transactions_endpoint(
    limit: int = Query(50, ge=1, le=200),
    authorization: Optional[str] = Header(None)
):
    """
    Get blockchain payment proof records for the authenticated user.
    Returns blockchain_enabled=False if user has no wallet address.
    """
    try:
        user_id = get_user_id_from_token(authorization)

        from database import get_user_wallet_address, get_blockchain_transactions

        wallet = None
        blockchain_enabled = False
        if user_id is not None:
            wallet = get_user_wallet_address(user_id)
            blockchain_enabled = wallet is not None

        if not blockchain_enabled:
            return JSONResponse(content={
                "success": True,
                "blockchain_enabled": False,
                "data": [],
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "message": "User has not onboarded to blockchain"
                }
            })

        txns = get_blockchain_transactions(wallet_address=wallet, limit=limit)

        return JSONResponse(content={
            "success": True,
            "blockchain_enabled": True,
            "wallet_address": wallet,
            "data": txns,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "count": len(txns),
                "source": "payments"
            }
        })

    except Exception as e:
        logger.error(f"Blockchain transactions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Blockchain transactions failed: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "endpoints:app",
        host="0.0.0.0",
        port=int(os.getenv('PORT', 8000)),
        reload=os.getenv('ENVIRONMENT', 'development') == 'development',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )

