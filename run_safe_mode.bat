@echo off
echo Starting Smart Document Review System (Safe Mode)
echo ================================================

REM Check if Streamlit is installed
python -c "import streamlit; print('✅ Streamlit version:', streamlit.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ Error: Streamlit is not installed.
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if the app imports correctly
echo Checking app imports...
python -c "import review_app; print('✅ App imports successfully')" 2>nul
if errorlevel 1 (
    echo ❌ App import failed. Please check the error above.
    pause
    exit /b 1
)

REM Check for nested expanders and other issues
echo Checking for code quality issues...
python check_expanders.py

REM Check Streamlit component requirements
echo Checking Streamlit component validation...
python validate_components.py
if errorlevel 1 (
    echo ❌ Component validation failed. Please fix the issues above.
    pause
    exit /b 1
)

echo.
echo ✅ All checks passed! Starting the application...
echo.
echo 📋 Application Features:
echo    • Flexible criteria and prompt management
echo    • Multiple domain support (General, Healthcare, Technology, etc.)
echo    • AI-powered document analysis
echo    • Comprehensive analytics dashboard
echo    • No nested expander issues (FIXED!)
echo.

REM Start the application with optimal settings
streamlit run review_app.py --server.address=localhost --server.port=8501

echo.
echo Application stopped.
pause
