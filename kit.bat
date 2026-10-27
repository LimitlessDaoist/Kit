@echo off
setlocal
set "KIT_DIR=%~dp0"
if not exist "%KIT_DIR%.kit_deps_ok" (
    echo [Kit] Auto-installing required Python packages (yt-dlp, Pillow, pypdf, qrcode)...
    python -m pip install --upgrade yt-dlp Pillow pypdf qrcode
    echo ok > "%KIT_DIR%.kit_deps_ok"
)
if exist "%KIT_DIR%target\release\kit.exe" (
    "%KIT_DIR%target\release\kit.exe" %*
) else (
    set "PYTHONPATH=%KIT_DIR%python;%PYTHONPATH%"
    python -m kit_py.cli %*
)
