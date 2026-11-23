@echo off
setlocal
pushd "%~dp0" || exit /b 1

curl.exe --silent --fail --max-time 2 http://127.0.0.1:8000/api/health 2>nul | findstr /C:"SWILLM" >nul
if not errorlevel 1 (
    echo SWILLM is already running at http://127.0.0.1:8000/
    start "" "http://127.0.0.1:8000/"
    popd
    exit /b 0
)

set "SWILLM_BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%SWILLM_BUNDLED_PYTHON%" goto bundled

py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" 2>nul
if not errorlevel 1 goto launcher
python -c "import sys; sys.exit(sys.version_info < (3, 10))" 2>nul
if not errorlevel 1 goto path_python

echo Python 3.10 or newer is required to run SWILLM.
goto failed

:bundled
"%SWILLM_BUNDLED_PYTHON%" -B -u server.py
goto finished

:launcher
py -3 -B -u server.py
goto finished

:path_python
python -B -u server.py

:finished
if not errorlevel 1 (
    popd
    exit /b 0
)
echo The SWILLM server stopped. Check the message above and try again.

:failed
pause
popd
exit /b 1
