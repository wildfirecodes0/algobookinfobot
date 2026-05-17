#!/usr/bin/env python3

import os
import sys
import asyncio
from pathlib import Path

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

required = {
    "BOT_TOKEN": "Telegram Bot Token (from BotFather)",
    "GEMINI_API_KEY": "Gemini API Key (from aistudio.google.com)",
    "ADMIN_IDS": "Admin Telegram User IDs (comma separated)",
}

missing = []
for key, desc in required.items():
    if not os.getenv(key):
        missing.append(f"  ❌ {key} — {desc}")

if missing:
    print("\n🚨 Missing environment variables:\n")
    print("\n".join(missing))
    sys.exit(1)

print("✅ Environment variables loaded successfully")
print(f"🤖 Bot Token: ...{os.getenv('BOT_TOKEN', '')[-6:]}")
print(f"🧠 Gemini Key: ...{os.getenv('GEMINI_API_KEY', '')[-6:]}")
print(f"👤 Admin IDs: {os.getenv('ADMIN_IDS')}")
print("─" * 40)

from bot import main

if __name__ == "__main__":
    asyncio.run(main())
