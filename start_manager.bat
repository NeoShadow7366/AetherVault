@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo Generative AI Manager
echo ===========================================

set "ROOT_DIR=%~dp0"
set "BIN_DIR=%ROOT_DIR%bin"
set "PYTHON_EXE=%BIN_DIR%\python\python.exe"

:: Fallback to system python if portable does not exist
if not exist "%PYTHON_EXE%" (
    echo [INFO] Portable Python not found in %BIN_DIR%. Defaulting to system python...
    set "PYTHON_EXE=python"
)

echo [1/2] Launching local Web Dashboard...
start http://localhost:8080

echo [2/2] Starting server (embedding engine launches automatically)...
echo Please keep this window open to serve UI packages!
"%PYTHON_EXE%" "%ROOT_DIR%.backend\server.py"

pause
