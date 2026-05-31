#!/bin/bash
set -e

# Set your tokens before running:
# export VERCEL_TOKEN=your_vercel_token
# export RAILWAY_TOKEN=your_railway_token

if [ -z "$VERCEL_TOKEN" ] || [ -z "$RAILWAY_TOKEN" ]; then
  echo "❌ Please set VERCEL_TOKEN and RAILWAY_TOKEN environment variables first."
  echo "   export VERCEL_TOKEN=your_vercel_token"
  echo "   export RAILWAY_TOKEN=your_railway_token"
  exit 1
fi

echo "============================================"
echo "  Store Intelligence System - Deployer"
echo "============================================"

# ── 1. RAILWAY BACKEND ──────────────────────────
echo ""
echo "▶ Step 1: Logging into Railway..."
railway login --token $RAILWAY_TOKEN

echo "▶ Step 2: Creating Railway project..."
cd backend
railway init --name store-intelligence-backend

echo "▶ Step 3: Adding PostgreSQL..."
railway add --plugin postgresql

echo "▶ Step 4: Adding Redis..."
railway add --plugin redis

echo "▶ Step 5: Deploying backend..."
railway up --detach

BACKEND_URL=$(railway domain)
echo "✅ Backend deployed at: https://$BACKEND_URL"
cd ..

# ── 2. VERCEL FRONTEND ──────────────────────────
echo ""
echo "▶ Step 6: Deploying frontend to Vercel..."
cd frontend

vercel deploy --prod \
  --token $VERCEL_TOKEN \
  --yes \
  --env VITE_API_URL=https://$BACKEND_URL \
  --env VITE_WS_URL=wss://$BACKEND_URL

FRONTEND_URL=$(vercel ls --token $VERCEL_TOKEN | grep store | awk '{print $2}' | head -1)
echo "✅ Frontend deployed at: https://$FRONTEND_URL"
cd ..

# ── 3. OUTPUT URLS ──────────────────────────────
echo ""
echo "============================================"
echo "  🚀 DEPLOYMENT COMPLETE"
echo "============================================"
echo "  Frontend:  https://$FRONTEND_URL"
echo "  Backend:   https://$BACKEND_URL"
echo "  API Docs:  https://$BACKEND_URL/docs"
echo "  WebSocket: wss://$BACKEND_URL/ws/events"
echo "============================================"
