@echo off
setlocal
set "KIT_DIR=%~dp0"
if exist "%KIT_DIR%.kit_deps_ok" goto :deps_done
echo [Kit] Auto-installing required Python packages: yt-dlp, Pillow, pypdf, qrcode...
python -m pip install --upgrade yt-dlp Pillow pypdf qrcode
if errorlevel 1 exit /b %errorlevel%
echo ok > "%KIT_DIR%.kit_deps_ok"
:deps_done
if exist "%KIT_DIR%target\release\kit.exe" goto :run_rust
set "PYTHONPATH=%KIT_DIR%python;%PYTHONPATH%"
python -m kit_py.cli %*
exit /b %errorlevel%
:run_rust
"%KIT_DIR%target\release\kit.exe" %*
exit /b %errorlevel%
