#!/usr/bin/env bash
# CogniCare Local Stack Startup Script
# Run from project root: ./start-local.sh

set -euo pipefail

echo "🚀 Starting CogniCare local stack..."

# 1. Build and start Docker services
echo "📦 Building and starting Docker services..."
docker compose up --build -d

# 2. Wait for API to be healthy
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
  if curl -sf http://localhost:8000/openapi.json >/dev/null 2>&1; then
    echo "✅ API is up"
    break
  fi
  sleep 2
done

# 3. Start cloudflared tunnel in background
echo "🌐 Starting cloudflared tunnel..."
cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!
sleep 3

# 4. Extract tunnel URL
TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared.log | head -1)
if [[ -z "$TUNNEL_URL" ]]; then
  echo "❌ Could not detect tunnel URL. Check /tmp/cloudflared.log"
  kill $TUNNEL_PID 2>/dev/null || true
  exit 1
fi
echo "🔗 Tunnel: $TUNNEL_URL"

# 5. Update .env with webhook URL
WEBHOOK_URL="${TUNNEL_URL}/webhooks/telegram/inbound"
echo "📝 Updating TELEGRAM_WEBHOOK_URL in .env..."
sed -i "s|^TELEGRAM_WEBHOOK_URL=.*|TELEGRAM_WEBHOOK_URL=${WEBHOOK_URL}|" .env

# 6. Register Telegram webhook
echo "🤖 Registering Telegram webhook..."
docker compose exec -T api python -c "
import httpx, os
token = os.getenv('TELEGRAM_BOT_TOKEN')
url = os.getenv('TELEGRAM_WEBHOOK_URL')
r = httpx.post(f'https://api.telegram.org/bot{token}/setWebhook', json={'url': url}, timeout=10)
print(r.json())
"

echo ""
echo "✅ Backend stack is running!"
echo "   API:       http://localhost:8000"
echo "   Docs:      http://localhost:8000/docs"
echo "   Tunnel:    $TUNNEL_URL"
echo "   Webhook:   $WEBHOOK_URL"
echo ""
echo "📋 Next steps:"
echo "   1. cd frontend && npm install && npm run dev"
echo "   2. Open http://localhost:3000"
echo "   3. Sign up → Add Elder → Open deep-link in Telegram"
echo ""
echo "🛑 To stop: docker compose down && kill $TUNNEL_PID"