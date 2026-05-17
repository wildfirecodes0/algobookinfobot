"""
ALGO-BOT - Govt Exam Preparation Telegram Bot
Powered by Gemini AI
"""

import os
import asyncio
import logging
import json
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, PollAnswerHandler
)
from telegram.constants import ParseMode
from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("algo_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ADMIN_IDS_RAW  = os.getenv("ADMIN_IDS", "")
APPROVED_CHATS_FILE = "approved_chats.json"
SESSION_FILE        = "sessions.json"

ADMIN_IDS: set[int] = set()

for _id in ADMIN_IDS_RAW.split(","):
    _id = _id.strip()

    if _id.lstrip("-").isdigit():
        ADMIN_IDS.add(int(_id))

# ─────────────────────────────────────────────
# GEMINI SETUP
# ─────────────────────────────────────────────
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
# PERSISTENCE HELPERS
# ─────────────────────────────────────────────

def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

approved_chats: dict = load_json(APPROVED_CHATS_FILE, {})
sessions: dict = load_json(SESSION_FILE, {})

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_approved(chat_id: int) -> bool:
    return str(chat_id) in approved_chats

def save_approved():
    save_json(APPROVED_CHATS_FILE, approved_chats)

def save_sessions():
    save_json(SESSION_FILE, sessions)

async def gemini_ask(prompt: str) -> str:
    try:
        resp = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt
        )

        return resp.text.strip()

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return ""

# ─────────────────────────────────────────────
# GUARD
# ─────────────────────────────────────────────

async def guard(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        if is_admin(user.id):
            return True

        return False

    if not is_approved(chat.id):
        return False

    return True

# ─────────────────────────────────────────────
# BOT ADDED TO A NEW CHAT
# ─────────────────────────────────────────────

async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat   = result.chat
    new_status = result.new_chat_member.status

    if new_status in ("member", "administrator"):
        key = str(chat.id)

        if key not in approved_chats:
            approved_chats[key] = {
                "title": chat.title or chat.username or str(chat.id),
                "type": chat.type,
                "added_at": datetime.now().isoformat(),
                "approved": False
            }

            save_approved()

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🔔 *Bot Added To A New Chat!*\n\n"
                        f"📛 *Name:* {chat.title or chat.username}\n"
                        f"🆔 *Chat ID:* `{chat.id}`\n"
                        f"📂 *Type:* {chat.type}\n\n"
                        f"To approve:\n`/algo-approve {chat.id}`\n"
                        f"To reject:\n`/algo-reject {chat.id}`"
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )

            except Exception:
                pass

    elif new_status in ("left", "kicked"):
        key = str(chat.id)

        if key in approved_chats:
            approved_chats.pop(key)
            save_approved()

# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return

    user = update.effective_user

    if is_admin(user.id):
        await update.message.reply_text(
            "👋 *ALGO-BOT Is Active!*\n\n"
            "📚 Govt Exam Preparation Bot — Powered by Gemini AI\n\n"
            "*Admin Commands:*\n"
            "`/algo-post` — Post study material\n"
            "`/algo-quizzes` — Start quiz session\n"
            "`/algo-list` — View approved chats\n"
            "`/algo-approve <chat_id>` — Approve chat\n"
            "`/algo-reject <chat_id>` — Reject chat\n"
            "`/algo-stop` — Stop active session\n"
            "`/algo-status` — Check bot status",
            parse_mode=ParseMode.MARKDOWN
        )
