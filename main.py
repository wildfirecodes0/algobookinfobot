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
    print("⚠️  .env file nahi mili — environment variables manually set honi chahiye.")

# ── Validate required env vars ───────────────────────────────
required = {
    "BOT_TOKEN": "8888958542:AAEr0lXyJWEAc1Bk8aKhu2sp4pQcCU1e-Mc",
    "GEMINI_API_KEY": "AIzaSyB4ale6rlMo2bA7xHtbhCbvyzfrRFtwvp0",
    "ADMIN_IDS": "7736820791",
}

missing = []
for key, desc in required.items():
    if not os.getenv(key):
        missing.append(f"  ❌ {key} — {desc}")

if missing:
    print("\n🚨 Ye environment variables missing hain:\n")
    print("\n".join(missing))
    print("\n📄 .env file banao (example .env.example me diya hai)\n")
    sys.exit(1)

print("✅ Environment variables load ho gaye")
print(f"🤖 Bot Token: ...{os.getenv('BOT_TOKEN', '')[-6:]}")
print(f"🧠 Gemini Key: ...{os.getenv('GEMINI_API_KEY', '')[-6:]}")
print(f"👤 Admin IDs: {os.getenv('ADMIN_IDS')}")
print("─" * 40)

# ── Start Bot ────────────────────────────────────────────────
from bot import main
main()
