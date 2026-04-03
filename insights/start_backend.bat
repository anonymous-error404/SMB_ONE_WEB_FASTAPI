@echo off
echo ========================================
echo  Business Insights Platform
echo  Database Integration Test
echo ========================================
echo.

echo Checking if database exists...
if exist "data\business_data.db" (
    echo [OK] Database found at data\business_data.db
) else (
    echo [ERROR] Database not found!
    echo Creating database now...
    python create_database.py
    if errorlevel 1 (
        echo [ERROR] Failed to create database
        pause
        exit /b 1
    )
)

echo.
echo Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn api.endpoints:app --reload --port 8000
