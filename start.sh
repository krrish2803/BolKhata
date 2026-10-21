#!/bin/bash
# Kill any existing processes on ports 8000 and 5173
lsof -ti:8000 -ti:5173 | xargs kill -9 2>/dev/null || true

echo "Starting BolKhata backend on http://127.0.0.1:8000..."
cd /Users/krrishyaduka/Documents/BolKhata/backend
PYTHONPATH=. ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Starting BolKhata frontend on http://localhost:5173..."
cd /Users/krrishyaduka/Documents/BolKhata
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Servers started successfully! Press Ctrl+C to terminate both."

wait $BACKEND_PID $FRONTEND_PID
