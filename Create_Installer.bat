@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  py -3 bootstrap.py installer
  goto :done
)
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  python bootstrap.py installer
  goto :done
)
echo Python 3.10 or newer is required.
choice /C YN /M "Install Python 3.13 using winget"
if errorlevel 2 goto :manual
winget install --id Python.Python.3.13 --exact --source winget
if errorlevel 1 goto :manual
echo Close this window and run this BAT again to refresh PATH.
pause
exit /b 0
:manual
start "" "https://www.python.org/downloads/windows/"
echo Install Python with pip and Tcl/Tk enabled, then rerun this BAT.
pause
exit /b 1
:done
set "result=%errorlevel%"
if not "%result%"=="0" echo Operation failed. Read the error above.
pause
exit /b %result%
