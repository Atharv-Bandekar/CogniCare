@echo off
REM CogniCare Local Stack Startup Script (Windows)
REM Run from project root: start-local.bat

echo 🚀 Starting CogniCare local stack...

REM 1. Build and start Docker services
echo 📦 Building and starting Docker services...
docker compose up --build -d

REM 2. Wait for API to be healthy
echo ⏳ Waiting for API to be ready...
set "API_READY=0"
for /L %%i in (1,1,30) do (
  curl -sf http://localhost:8000/openapi.json >nul 2>&1 && set "API_READY=1" && goto :api_ready
  timeout /t 2 /nobreak >nul
)
:api_ready
if "%API_READY%"=="0" (
  echo ❌ API failed to start
  exit /b 1
)
echo ✅ API is up

REM 3. Start cloudflared tunnel in background
echo 🌐 Starting cloudflared tunnel...
start "cloudflared" /B cloudflared tunnel --url http://localhost:8000 ^> %TEMP%\cloudflared.log 2^>^&1
timeout /t 3 /nobreak >nul

REM 4. Extract tunnel URL
for /F "tokens=*" %%A in ('findstr /R "https://[a-zA-Z0-9.-]*\.trycloudflare\.com" %TEMP%\cloudflared.log') do (
  set "TUNNEL_URL=%%A"
  goto :found_url
)
:found_url
if "%TUNNEL_URL%"=="" (
  echo ❌ Could not detect tunnel URL. Check %TEMP%\cloudflared.log
  exit /b 1
)
echo 🔗 Tunnel: %TUNNEL_URL%

REM 5. Update .env with webhook URL
set "WEBHOOK_URL=%TUNNEL_URL%/webhooks/telegram/inbound"
echo 📝 Updating TELEGRAM_WEBHOOK_URL in .env...
powershell -Command "(Get-Content .env) -replace '^TELEGRAM_WEBHOOK_URL=.*', 'TELEGRAM_WEBHOOK_URL=%WEBHOOK_URL%' | Set-Content .env"

REM 6. Register Telegram webhook
echo 🤖 Registering Telegram webhook...
docker compose exec -T api python -c "
import httpx, os
token = os.getenv('TELEGRAM_BOT_TOKEN')
url = os.getenv('TELEGRAM_WEBHOOK_URL')
r = httpx.post(f'https://api.telegram.org/bot{token}/setWebhook', json={'url': url}, timeout=10)
print(r.json())
"

echo.
echo ✅ Backend stack is running!
echo    API:       http://localhost:8000
echo    Docs:      http://localhost:8000/docs
echo    Tunnel:    %TUNNEL_URL%
echo    Webhook:   %WEBHOOK_URL%
echo.
echo 📋 Next steps:
echo    1. cd frontend && npm install && npm run dev
echo    2. Open http://localhost:3000
echo    3. Sign up -> Add Elder -> Open deep-link in Telegram
echo.
echo 🛑 To stop: docker compose down && taskkill /IM cloudflared.exe /F
pause