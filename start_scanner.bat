@echo off
title Passport Scanner Setup
echo ===================================================
echo     Passport Scanner Setup and Launcher
echo ===================================================
echo.

echo Step 1: Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Installing automatically via winget...
    winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    echo.
    echo ====================================================================
    echo IMPORTANT: Python has been installed!
    echo Please CLOSE this black window and double-click start_scanner.bat again.
    echo ====================================================================
    pause
    exit /b
) else (
    echo Python is already installed!
)

echo.
echo Step 2: Checking for Tesseract OCR Engine...
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo Tesseract OCR not found. Installing automatically via winget...
    winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
) else (
    echo Tesseract OCR is already installed!
)

echo.
echo Step 3: Installing required Python packages...
pip install -r requirements.txt

echo.
echo Step 4: Starting the local OCR Server...
echo The application will now start. Your browser will automatically open to http://localhost:5000
echo (If it doesn't open, manually go to http://localhost:5000 in your browser)
echo.
start http://localhost:5000
python app.py
pause
