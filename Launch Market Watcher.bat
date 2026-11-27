@echo off
setlocal
pushd "%~dp0" || exit /b 1

set "WATCHER_PYTHON=.venv\Scripts\python.exe"
if exist "%WATCHER_PYTHON%" goto dependencies

echo Setting up Market Watcher...
py -3 -c "import sys; sys.exit(not (sys.version_info >= (3, 9)))" >nul 2>&1
if errorlevel 1 goto try_python
py -3 -m venv .venv
if errorlevel 1 goto setup_failed
goto dependencies

:try_python
python -c "import sys; sys.exit(not (sys.version_info >= (3, 9)))" >nul 2>&1
if errorlevel 1 goto python_missing
python -m venv .venv
if errorlevel 1 goto setup_failed

:dependencies
"%WATCHER_PYTHON%" -c "import tkinter, pymem; from PIL import Image, ImageTk" >nul 2>&1
if not errorlevel 1 goto launch
echo Installing Market Watcher dependencies...
"%WATCHER_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed
"%WATCHER_PYTHON%" -c "import tkinter, pymem; from PIL import Image, ImageTk"
if errorlevel 1 goto setup_failed

:launch
"%WATCHER_PYTHON%" main.py
if errorlevel 1 goto failed
popd
exit /b 0

:python_missing
echo Install Python 3.9 or newer from https://www.python.org/downloads/windows/ and try again.
goto failed

:setup_failed
echo Market Watcher setup failed. Review the error above and try again.

:failed
pause
popd
exit /b 1
