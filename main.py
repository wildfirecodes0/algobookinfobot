#!/usr/bin/env python3
"""
ALGO-BOT Main Entry Point
Usage: python main.py
"""

import os
import sys
from pathlib import Path

# ── Load .env file ──────────────────────────────────────────
env_file = Path(__file__).parent / ".env"

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()

            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

else:
    print("⚠️  .env file not found — environment variables must be set manually.")

# ── Validate required env vars ───────────────────────────────
required = {
    "BOT_TOKEN": "Telegram Bot Token (available from BotFather)",
    "GEMINI_API_KEY": "Gemini API Key (available from aistudio.google.com)",
    "ADMIN_IDS": "Admin Telegram User IDs (comma separated)",
}

missing = []

for key, desc in required.items():
    if not os.getenv(key):
        missing.append(f"  ❌ {key} — {desc}")

if missing:
    print("\n🚨 The following environment variables are missing:\n")
    print("\n".join(missing))
    print("\n📄 Create a .env file (example provided in .env.example)\n")
    sys.exit(1)

print("✅ Environment variables loaded successfully")
print(f"🤖 Bot Token: ...{os.getenv('BOT_TOKEN', '')[-6:]}")
print(f"🧠 Gemini Key: ...{os.getenv('GEMINI_API_KEY', '')[-6:]}")
print(f"👤 Admin IDs: {os.getenv('ADMIN_IDS')}")
print("─" * 40)

# ── Start Bot ────────────────────────────────────────────────
from bot import main

main()
