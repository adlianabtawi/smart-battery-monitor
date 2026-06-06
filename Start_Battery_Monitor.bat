@echo off
cd /d "%~dp0"

:: Try pythonw first (no console window)
where pythonw >nul 2>&1
if %errorlevel% == 0 (
    pythonw "%~dp0battery_monitor.py"
    exit /b
)

:: Try python from common install locations
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
    "C:\Python313\pythonw.exe"
    "C:\Python312\pythonw.exe"
    "C:\Python311\pythonw.exe"
) do (
    if exist %%p (
        %%p "%~dp0battery_monitor.py"
        exit /b
    )
)

:: Nothing found - show error
echo Python hittades inte. Installera Python fran python.org
echo Se till att kryssa i "Add Python to PATH" vid installationen.
pause
