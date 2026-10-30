@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py

echo [1/3] Installing Python packages...
%PY% -m pip install -U pip
%PY% -m pip install -U "yt-dlp[default]" imageio-ffmpeg numpy opencv-python-headless rapidocr onnxruntime
if errorlevel 1 (
  echo.
  echo Package install failed. Please read README.txt
  pause
  exit /b 1
)

echo.
echo [2/3] Installing Deno - needed by yt-dlp for YouTube...
where deno >nul 2>nul && echo Deno is already installed.
where deno >nul 2>nul || winget install --id DenoLand.Deno -e --accept-source-agreements --accept-package-agreements

echo.
echo [3/3] Downloading text recognition models - first time only...
%PY% -c "from rapidocr import RapidOCR; RapidOCR(); print('OK')"

echo.
echo Done. Next, double-click run.bat
pause
