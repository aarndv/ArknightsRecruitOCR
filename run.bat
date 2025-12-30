@echo off
:: Quick run script for development
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
python main.py
