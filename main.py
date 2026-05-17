#!/usr/bin/env python3

import os
import sys
import asyncio
from pathlib import Path

# Load .env locally only
env_file = Path(__file__).parent / ".env"

if env_file.exists():
    print("📄 Loading local .env file...")
    
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            # Render env vars overwrite na ho
            if key not in os.environ:
                os.environ[key.strip()] = value.strip()

else:
    print("⚠️ No .env file found. Using Render environment variables.")

# Required vars
required_vars = [
    "BOT_TOKEN",
    "GEMINI_API_KEY",
    "ADMIN_IDS"
]

missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print("\n🚨 Missing Required Environment Variables:\n")

    for var in missing:
        print(f"❌ {var}")

    print("\n👉 Fix this in Render Dashboard → Environment")
    sys.exit(1)

print("\n✅ Environment variables loaded successfully")
print(f"🤖 BOT_TOKEN Loaded")
print(f"🧠 GEMINI_API_KEY Loaded")
print(f"👤 ADMIN_IDS = {os.getenv('ADMIN_IDS')}")
print("-" * 50)

# Import after env loaded
from bot import main

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped manually")

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        sys.exit(1)
