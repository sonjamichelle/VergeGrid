@echo off
setlocal enabledelayedexpansion
title VergeGrid Installer Bootstrap
set LOG=%TEMP%\vergegrid-bootstrap.log

echo [Bootstrap] Starting VergeGrid installer... > "%LOG%"
echo.
echo ==========================================================
echo     VergeGrid Installer Bootstrap
echo ==========================================================

:: ==========================================================
:: STEP 0: Set working directory
:: ==========================================================
set "SETUPDIR=%~dp0"
cd /d "%SETUPDIR%"
echo [Bootstrap] Working directory: %SETUPDIR% >> "%LOG%"
echo Using setup folder: %SETUPDIR%

:: ==========================================================
:: STEP 1: Check / Install Python
:: ==========================================================
where python >nul 2>nul
if %errorlevel% equ 0 (
    for /f "usebackq delims=" %%i in (`where python`) do set "PYTHON_PATH=%%i"
    for /f "tokens=2 delims= " %%v in ('python -V 2^>^&1 ^| findstr /R "[0-9]\.[0-9]"') do set "PYTHON_VER=%%v"

    echo [Bootstrap] Python found at: !PYTHON_PATH! >> "%LOG%"
    echo [Bootstrap] Python version: !PYTHON_VER! >> "%LOG%"
    echo.
    echo Python detected!
    echo Location: !PYTHON_PATH!
    echo Version:  !PYTHON_VER!
    echo Continuing in 3 seconds...
    timeout /t 3 >nul
    goto :checkdeps
)

:: If not found, prompt user
echo.
echo Python 3.11 (or newer) is required for VergeGrid.
set /p USERCHOICE=Would you like to install Python 3.12.3 automatically? [Y/N]: 
if /i "%USERCHOICE%"=="Y" goto :installpython
if /i "%USERCHOICE%"=="y" goto :installpython

echo.
echo Python installation declined.
echo You must install Python 3.11 or newer manually before running this installer.
echo Installer will now exit.
echo [Bootstrap] Python installation declined by user. Exiting... >> "%LOG%"
pause
exit /b 1

:installpython
echo [Bootstrap] Python not found. Installing Python 3.12.3... >> "%LOG%"
set "PYTMP=%TEMP%\python_installer.exe"
echo Downloading Python installer...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe' -OutFile '%PYTMP%'"
echo [Bootstrap] Running silent Python install... >> "%LOG%"
start /wait "" "%PYTMP%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del "%PYTMP%" 2>nul

:: Verify install after installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [Bootstrap ERROR] Python installation failed. >> "%LOG%"
    echo.
    echo Python installation failed. Please install manually and rerun this installer.
    pause
    exit /b 1
)

echo [Bootstrap] Python installation completed successfully. >> "%LOG%"
echo Python installed successfully!
timeout /t 2 >nul

:: ==========================================================
:checkdeps
:: STEP 2: Run Python dependency checker
:: ==========================================================
echo [Bootstrap] Checking system dependencies... >> "%LOG%"
echo Running: python "%SETUPDIR%check_dependencies_win.py" >> "%LOG%"
python "%SETUPDIR%check_dependencies_win.py"
if %errorlevel% neq 0 (
    echo [Bootstrap WARN] Dependency check returned %errorlevel% >> "%LOG%"
    echo.
    echo Dependencies were installed or verified; review console for any warnings.
    timeout /t 2 >nul
)

:: ==========================================================
:: STEP 3: Run build tools installer (modular)
:: ==========================================================
echo [Bootstrap] Checking and installing build tools... >> "%LOG%"
echo Running: python "%SETUPDIR%install_build_tools.py" >> "%LOG%"
python "%SETUPDIR%install_build_tools.py"
if %errorlevel% neq 0 (
    echo [Bootstrap WARN] Build tools setup returned %errorlevel% >> "%LOG%"
    echo.
    echo Build tools installation may require a restart to fully detect.
    timeout /t 2 >nul
)

:: ==========================================================
:: STEP 3.5: Check for existing VergeGrid installation
:: ==========================================================
echo [Bootstrap] Checking for existing VergeGrid installation... >> "%LOG%"
echo Running: python "%SETUPDIR%vergegrid_cleanup.py" >> "%LOG%"
python "%SETUPDIR%vergegrid_cleanup.py"
if %errorlevel% equ 99 (
    echo [Bootstrap INFO] No previous installation detected or user cancelled cleanup. >> "%LOG%"
) else if %errorlevel% equ 0 (
    echo [Bootstrap INFO] Cleanup or reset completed successfully. >> "%LOG%"
) else if %errorlevel% geq 2 (
    echo [Bootstrap ERROR] Cleanup encountered an error. >> "%LOG%"
    echo.
    echo Cleanup process failed. Check cleanup log for details:
    echo %TEMP%\vergegrid_cleanup.log
    pause
)

:: ==========================================================
:runinstaller
:: STEP 4: Launch VergeGrid main installer
:: ==========================================================
echo [Bootstrap] Launching VergeGrid Python installer... >> "%LOG%"

:: Prefer a known good Python install
set "REALPY=C:\Python311\python.exe"
if exist "%REALPY%" (
    echo [Bootstrap] Using verified Python: %REALPY% >> "%LOG%"
    "%REALPY%" "%SETUPDIR%vergegrid-installer.py"
) else (
    echo [Bootstrap] Using active Python fallback >> "%LOG%"
    python "%SETUPDIR%vergegrid-installer.py"
)

if %errorlevel% neq 0 (
    echo [Bootstrap ERROR] Python script returned error code %errorlevel% >> "%LOG%"
    echo.
    echo Installer failed. Check log for details:
    echo %LOG%
    pause
    exit /b %errorlevel%
)

echo.
echo VergeGrid installation complete!
echo [Bootstrap] Installation complete. >> "%LOG%"
endlocal
exit /b 0
