@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=9100"

where python >nul 2>nul
if errorlevel 1 (
  echo [x] Python не найден в PATH.
  pause
  exit /b 1
)

if exist "deepai-key.txt" (
  for /f "usebackq delims=" %%a in ("deepai-key.txt") do set "DEEPAI_API_KEY=%%a"
) else (
  set /p DEEPAI_API_KEY=Вставь Api-Key и нажми Enter: 
  if defined DEEPAI_API_KEY >"deepai-key.txt" echo !DEEPAI_API_KEY!
)

if not defined DEEPAI_API_KEY (
  echo [x] Ключ не задан.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   DeepAI local API
echo ------------------------------------------------------------
echo   base_url : http://127.0.0.1:%PORT%/v1
echo   api_key  : sk-local        (любая непустая строка)
echo   model    : glm-5.3-flash   (или другие из /v1/models)
echo ------------------------------------------------------------
echo   Остановить: Ctrl+C в этом окне или просто закрой окно.
echo ============================================================
echo.

python "%~dp0deepai-shim.py" %PORT%
echo.
echo [i] Шим остановлен.
pause