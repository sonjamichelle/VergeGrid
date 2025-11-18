@echo off
setlocal enabledelayedexpansion
title VergeGrid Installer Bootstrap

:: ==========================================================
:: STEP 0: Set working directory and local log directory
:: ==========================================================
set "SETUPDIR=%~dp0"
cd /d "%SETUPDIR%"
set "LOGDIR=%SETUPDIR%Installer_Logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\vergegrid-bootstrap.log"

echo [Bootstrap] Starting VergeGrid installer... > "%LOG%"
echo ==========================================================
echo     VergeGrid Installer Bootstrap
echo ==========================================================
echo Using setup folder: %SETUPDIR%
echo Logs will be saved in: %LOGDIR%
echo [Bootstrap] Log directory initialized at %LOGDIR% >> "%LOG%"

:: ==========================================================
:: STEP 1: Check / Install Python
:: ==========================================================
where python >nul 2>nul
if %errorlevel% equ 0 (
    for /f "usebackq delims=" %%i in (`where python`) do set "PYTHON_PATH=%%i"
    for /f "tokens=2 delims= " %%v in ('python -V 2^>^&1 ^| findstr /R "[0-9]\.[0-9]"') do set "PYTHON_VER=%%v"

    echo [Bootstrap] Python found at: !PYTHON_PATH! >> "%LOG%"
    echo [Bootstrap] Python version: !PYTHON_VER! >> "%LOG%"
    echo Python detected at !PYTHON_PATH! (version !PYTHON_VER!)
    echo Continuing in 3 seconds...
    timeout /t 3 >nul
    goto :checkdeps
)

echo Python 3.11+ is required. Installing 3.12.3 automatically...
echo [Bootstrap] Installing Python 3.12.3... >> "%LOG%"
set "PYTMP=%TEMP%\python_installer.exe"
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe' -OutFile '%PYTMP%'"
start /wait "" "%PYTMP%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del "%PYTMP%" 2>nul
where python >nul 2>nul || (
    echo [Bootstrap ERROR] Python install failed. >> "%LOG%"
    echo Python installation failed. Exiting.
    pause
    exit /b 1
)
echo [Bootstrap] Python installation complete. >> "%LOG%"
timeout /t 2 >nul

:: ==========================================================
:checkdeps
:: STEP 2: Run dependency checks
:: ==========================================================
echo [Bootstrap] Running dependency check... >> "%LOG%"
python "%SETUPDIR%check_dependencies_win.py"
echo [Bootstrap] Dependency check complete. >> "%LOG%"

:: ==========================================================
:: STEP 3: Run build tools
:: ==========================================================
echo [Bootstrap] Running build tools installer... >> "%LOG%"
python "%SETUPDIR%install_build_tools.py"
echo [Bootstrap] Build tools stage complete. >> "%LOG%"

:: ==========================================================
:runinstaller
:: STEP 4: Launch VergeGrid Python installer
:: ==========================================================
echo [Bootstrap] Launching VergeGrid Python installer... >> "%LOG%"

set "REALPY=C:\Python311\python.exe"
if exist "%REALPY%" (
    echo [Bootstrap] Using verified Python: %REALPY% >> "%LOG%"
    "%REALPY%" "%SETUPDIR%vergegrid-installer.py" --logdir "%LOGDIR%"
) else (
    echo [Bootstrap] Using active Python fallback >> "%LOG%"
    python "%SETUPDIR%vergegrid-installer.py" --logdir "%LOGDIR%"
)

if %errorlevel% neq 0 (
    echo [Bootstrap ERROR] Python script returned error code %errorlevel% >> "%LOG%"
    echo Installer failed. Check log for details: %LOG%
    pause
    exit /b %errorlevel%
)

echo VergeGrid installation complete!
echo [Bootstrap] Installation complete. >> "%LOG%"
echo Logs saved in: %LOGDIR%
endlocal
exit /b 0
