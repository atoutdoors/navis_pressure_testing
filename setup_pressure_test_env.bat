@echo off
setlocal

rem Create/use a project-local virtual environment.
cd /d "%~dp0"
set "VENV_DIR=%~dp0.venv"

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3 was not found. Install Python 3 and try again.
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment in "%VENV_DIR%"...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        exit /b 1
    )
)

echo Installing/updating required packages...
call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

python -m pip install numpy pandas plotly openpyxl gsw requests
if errorlevel 1 (
    echo Failed to install one or more required packages.
    exit /b 1
)

echo.
echo Environment ready.
echo To activate it later, run: .venv\Scripts\activate

if /i "%~1"=="run" (
    echo.
    echo Running ptest_visualization_optimized.py...
    python ptest_visualization_optimized.py
    if errorlevel 1 exit /b 1
)

echo To run the script now, use: setup_pressure_test_env.bat run
exit /b 0
