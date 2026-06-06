@echo off
title Product Finder Pro

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python from https://python.org
    pause
    exit /b
)

echo Installing required packages...
pip install streamlit pandas --quiet

echo.
echo Starting Product Finder Pro...
echo The app will open in your browser automatically.
echo To stop the app, close this window or press Ctrl+C
echo.

streamlit run app.py --server.headless false
pause
