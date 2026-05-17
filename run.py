#!/usr/bin/env python3
"""
ALGO-BOT Launcher
Ye script .env file load karke bot start karta hai
"""

import os
from pathlib import Path

# Load .env file manually (python-dotenv optional)
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from bot import main
main()
