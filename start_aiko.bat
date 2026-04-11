@echo off
TITLE Aiko Desktop Launcher
CHCP 65001 > nul

:: Check for .venv
if not exist ".venv\Scripts\python.exe" (
    echo [!] Warning: .venv not found. Attempting to use system python...
    SET PY_CMD=python
) else (
    SET PY_CMD=.venv\Scripts\python.exe
)

echo ==========================================
echo    AIKO DESKTOP - UNIFIED LAUNCHER
echo ==========================================
echo.
%PY_CMD% AikoLauncher.py
echo.
echo ==========================================
pause
