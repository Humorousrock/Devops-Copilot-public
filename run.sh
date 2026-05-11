#!/bin/bash

# ── DevOps Copilot — One-Click Launcher ──────────────────
set -e

echo ""
echo "  ██████╗ ██████╗ ██████╗ ██╗██╗      ██████╗ ████████╗"
echo "  ██╔════╝██╔═══██╗██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝"
echo "  ██║     ██║   ██║██████╔╝██║██║     ██║   ██║   ██║   "
echo "  ██║     ██║   ██║██╔═══╝ ██║██║     ██║   ██║   ██║   "
echo "  ╚██████╗╚██████╔╝██║     ██║███████╗╚██████╔╝   ██║   "
echo "   ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝   "
echo ""
echo "  DevOps Copilot — Agentic AI Assistant"
echo "────────────────────────────────────────────────────────"
echo ""

# Load .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "  ✓ Loaded .env"
else
  echo "  ✗ .env file not found!"
  echo "  Create a .env file with: GEMINI_API_KEY=your_key"
  exit 1
fi

# Check API key
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_new_gemini_key_here" ]; then
  echo ""
  echo "  ✗ GEMINI_API_KEY not set in .env!"
  echo "  Edit .env and add your key from: https://aistudio.google.com/apikey"
  exit 1
fi

echo "  ✓ Gemini API key loaded"

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "  ⟳ Installing Python dependencies..."
  pip install -r backend/requirements.txt -q
fi

echo "  ✓ Dependencies ready"
echo ""
echo "  Starting backend on http://localhost:8000"
echo "  Open frontend: frontend/copilot.html in your browser"
echo ""
echo "────────────────────────────────────────────────────────"
echo ""

# Run backend
cd backend
uvicorn copilot:app --host 0.0.0.0 --port 8000 --reload
