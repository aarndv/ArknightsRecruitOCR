@echo off
echo ========================================
echo  Arknights Recruit OCR - Build Script
echo ========================================
echo.

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found. Creating one...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Install PyInstaller if not present
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [*] Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo [*] Building executable...
echo.

:: Build using spec file
pyinstaller --clean ArknightsRecruitOCR.spec

echo.
if exist "dist\ArknightsRecruitOCR.exe" (
    echo ========================================
    echo  BUILD SUCCESSFUL!
    echo  Output: dist\ArknightsRecruitOCR.exe
    echo ========================================
) else (
    echo [X] Build failed. Check errors above.
)

echo.
pause
