@echo off
echo Starting Smart Document Review System (Improved Version)
echo ================================================

REM Check if Streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Error: Streamlit is not installed.
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Start the application
REM Optionally start the FastAPI backend with Uvicorn
echo To run the FastAPI backend, uncomment the next line:
REM start "FastAPI" python -m uvicorn app:app --reload --port 8000
REM Start the Streamlit frontend
echo Starting the Streamlit frontend...
start "Streamlit" streamlit run review_app.py

pause

