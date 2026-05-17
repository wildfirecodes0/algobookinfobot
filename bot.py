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
                        f"🔔 *Bot naye chat me add hua!*\n\n"
                        f"📛 *Naam:* {chat.title or chat.username}\n"
                        f"🆔 *Chat ID:* `{chat.id}`\n"
                        f"📂 *Type:* {chat.type}\n\n"
                        f"Approve karne ke liye:\n`/algo-approve {chat.id}`\n"
                        f"Reject karne ke liye:\n`/algo-reject {chat.id}`"
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
            "👋 *ALGO-BOT Active Hai!*\n\n"
            "📚 Govt Exam Preparation Bot — Powered by Gemini AI\n\n"
            "*Admin Commands:*\n"
            "`/algo-post` — Study material post karo\n"
            "`/algo-quizzes` — Quiz session shuru karo\n"
            "`/algo-list` — Approved chats ki list\n"
            "`/algo-approve <chat_id>` — Chat approve karo\n"
            "`/algo-reject <chat_id>` — Chat reject karo\n"
            "`/algo-stop` — Chalu session band karo\n"
            "`/algo-status` — Bot ka status dekho",
            parse_mode=ParseMode.MARKDOWN
        )

# ─────────────────────────────────────────────
# /algo-approve  /algo-reject
# ─────────────────────────────────────────────

async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/algo-approve <chat_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    chat_id = context.args[0].strip()
    if chat_id in approved_chats:
        approved_chats[chat_id]["approved"] = True
        save_approved()
        await update.message.reply_text(f"✅ Chat `{chat_id}` approve ho gaya!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ Chat `{chat_id}` list me nahi hai.", parse_mode=ParseMode.MARKDOWN)

async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/algo-reject <chat_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    chat_id = context.args[0].strip()
    if chat_id in approved_chats:
        approved_chats.pop(chat_id)
        save_approved()
        await update.message.reply_text(f"🗑️ Chat `{chat_id}` reject & remove ho gaya!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ Chat `{chat_id}` list me nahi hai.", parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
# /algo-list
# ─────────────────────────────────────────────

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not approved_chats:
        await update.message.reply_text("📭 Abhi koi chat registered nahi hai.")
        return

    lines = ["📋 *Registered Chats List:*\n"]
    for idx, (cid, info) in enumerate(approved_chats.items(), 1):
        status = "✅ Approved" if info.get("approved") else "⏳ Pending Approval"
        lines.append(
            f"{idx}. *{info.get('title', 'Unknown')}*\n"
            f"   🆔 `{cid}`\n"
            f"   📂 Type: {info.get('type', '?')}\n"
            f"   📅 Added: {info.get('added_at', '?')[:10]}\n"
            f"   {status}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
# /algo-status
# ─────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    approved_count = sum(1 for v in approved_chats.values() if v.get("approved"))
    pending_count  = len(approved_chats) - approved_count
    active_sessions = sum(1 for s in sessions.values() if s.get("running"))
    await update.message.reply_text(
        f"📊 *ALGO-BOT Status*\n\n"
        f"✅ Approved Chats: {approved_count}\n"
        f"⏳ Pending Approval: {pending_count}\n"
        f"🎯 Active Sessions: {active_sessions}\n"
        f"🤖 Gemini AI: {'Connected ✅' if GEMINI_API_KEY else 'Missing ❌'}",
        parse_mode=ParseMode.MARKDOWN
    )

# ─────────────────────────────────────────────
# /algo-stop
# ─────────────────────────────────────────────

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    stopped = 0
    for cid in list(sessions.keys()):
        if sessions[cid].get("running"):
            sessions[cid]["running"] = False
            stopped += 1
    save_sessions()
    await update.message.reply_text(f"🛑 {stopped} session(s) band kar diye gaye.")

# ─────────────────────────────────────────────
# LISTS
# ─────────────────────────────────────────────

EXAMS = [
    "UPSC CSE", "SSC CGL", "SSC CHSL", "SSC MTS", "IBPS PO",
    "IBPS Clerk", "SBI PO", "SBI Clerk", "RRB NTPC", "RRB Group D",
    "UP Police", "Delhi Police", "CTET", "CUET", "NDA", "CDS", "CAPF"
]

SUBJECTS_STUDY = [
    "General Knowledge", "Current Affairs", "History", "Geography",
    "Polity", "Economy", "Science & Technology", "Environment",
    "Maths / Reasoning", "English", "Hindi"
]

SUBJECTS_QUIZ = [
    "General Knowledge", "Current Affairs", "History", "Geography",
    "Polity", "Economy", "Science & Technology", "Maths / Reasoning",
    "English", "Hindi", "Mixed (Sab)"
]

LEVELS = ["Beginner", "Intermediate", "Advanced"]

# ─────────────────────────────────────────────
# /algo-post
# ─────────────────────────────────────────────

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["flow"] = "post"
    context.user_data["step"] = "subject"
    context.user_data["target_chat"] = None

    approved_list = [(cid, info) for cid, info in approved_chats.items() if info.get("approved")]
    if not approved_list:
        await update.message.reply_text("⚠️ Koi approved chat nahi hai. Pehle `/algo-approve <chat_id>` se approve karo.", parse_mode=ParseMode.MARKDOWN)
        return

    kb = []
    for cid, info in approved_list:
        kb.append([InlineKeyboardButton(
            f"{info['type'].upper()}: {info['title'][:30]}",
            callback_data=f"target|{cid}"
        )])
    kb.append([InlineKeyboardButton("📢 Sab Approved Chats Me Post Karo", callback_data="target|ALL")])
    await update.message.reply_text(
        "📌 *Kis chat me post karna hai?*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# ─────────────────────────────────────────────
# /algo-quizzes
# ─────────────────────────────────────────────

async def cmd_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["flow"] = "quiz"
    context.user_data["step"] = "subject"
    context.user_data["target_chat"] = None

    approved_list = [(cid, info) for cid, info in approved_chats.items() if info.get("approved")]
    if not approved_list:
        await update.message.reply_text("⚠️ Koi approved chat nahi hai.", parse_mode=ParseMode.MARKDOWN)
        return

    kb = []
    for cid, info in approved_list:
        kb.append([InlineKeyboardButton(
            f"{info['type'].upper()}: {info['title'][:30]}",
            callback_data=f"target|{cid}"
        )])
    kb.append([InlineKeyboardButton("📢 Sab Approved Chats Me Quiz Bhejo", callback_data="target|ALL")])
    await update.message.reply_text(
        "🧩 *Kis chat me quiz bhejni hai?*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# ─────────────────────────────────────────────
# CALLBACK QUERY HANDLER
# ─────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    data = query.data
    flow = context.user_data.get("flow")

    if data.startswith("target|"):
        target = data.split("|", 1)[1]
        context.user_data["target_chat"] = target
        context.user_data["step"] = "subject"

        subjects = SUBJECTS_STUDY if flow == "post" else SUBJECTS_QUIZ
        kb = [[InlineKeyboardButton(s, callback_data=f"subject|{s}")] for s in subjects]
        label = "📚 Study Material" if flow == "post" else "🧩 Quiz"
        await query.edit_message_text(
            f"*{label}* — Konsa subject?\n\nEk subject chuniye:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("subject|"):
        subject = data.split("|", 1)[1]
        context.user_data["subject"] = subject
        context.user_data["step"] = "exam"

        kb = [[InlineKeyboardButton(e, callback_data=f"exam|{e}")] for e in EXAMS]
        await query.edit_message_text(
            f"✅ Subject: *{subject}*\n\n🎯 Konse exam ke liye?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("exam|"):
        exam = data.split("|", 1)[1]
        context.user_data["exam"] = exam
        context.user_data["step"] = "level"

        kb = [[InlineKeyboardButton(l, callback_data=f"level|{l}")] for l in LEVELS]
        await query.edit_message_text(
            f"✅ Exam: *{exam}*\n\n📊 Difficulty level kya ho?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("level|"):
        level = data.split("|", 1)[1]
        context.user_data["level"] = level
        context.user_data["step"] = "count"

        if flow == "post":
            kb = [
                [InlineKeyboardButton("5 Posts", callback_data="count|5"),
                 InlineKeyboardButton("10 Posts", callback_data="count|10")],
                [InlineKeyboardButton("15 Posts", callback_data="count|15"),
                 InlineKeyboardButton("20 Posts", callback_data="count|20")],
            ]
            await query.edit_message_text(
                f"✅ Level: *{level}*\n\n📝 Kitne study material posts bhejne hain?",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            kb = [
                [InlineKeyboardButton("25 Quizzes", callback_data="count|25"),
                 InlineKeyboardButton("50 Quizzes", callback_data="count|50")],
                [InlineKeyboardButton("75 Quizzes", callback_data="count|75"),
                 InlineKeyboardButton("100 Quizzes", callback_data="count|100")],
                [InlineKeyboardButton("150 Quizzes", callback_data="count|150"),
                 InlineKeyboardButton("200 Quizzes", callback_data="count|200")],
            ]
            await query.edit_message_text(
                f"✅ Level: *{level}*\n\n🧩 Kitne quizzes bhejne hain? (30 sec interval)",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        return

    if data.startswith("count|"):
        count = int(data.split("|", 1)[1])
        context.user_data["count"] = count

        subject = context.user_data["subject"]
        exam    = context.user_data["exam"]
        level   = context.user_data["level"]
        target  = context.user_data["target_chat"]

        kb = [
            [InlineKeyboardButton("✅ Haan, Shuru Karo!", callback_data="confirm|yes")],
            [InlineKeyboardButton("❌ Cancel", callback_data="confirm|no")],
        ]
        mode_label = "Study Material Posts" if flow == "post" else "Quizzes"
        await query.edit_message_text(
            f"📋 *Confirm karo:*\n\n"
            f"📚 Subject: *{subject}*\n"
            f"🎯 Exam: *{exam}*\n"
            f"📊 Level: *{level}*\n"
            f"🔢 Count: *{count} {mode_label}*\n"
            f"📢 Target: *{'Sab Chats' if target == 'ALL' else target}*\n\n"
            f"Kya aap shuru karna chahte hain?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("confirm|"):
        choice = data.split("|", 1)[1]
        if choice == "no":
            await query.edit_message_text("❌ Session cancel ho gaya.")
            context.user_data.clear()
            return

        flow    = context.user_data["flow"]
        subject = context.user_data["subject"]
        exam    = context.user_data["exam"]
        level   = context.user_data["level"]
        count   = context.user_data["count"]
        target  = context.user_data["target_chat"]

        await query.edit_message_text(
            f"🚀 *Session shuru ho raha hai!*\n"
            f"📚 {subject} | 🎯 {exam} | 📊 {level} | 🔢 {count}",
            parse_mode=ParseMode.MARKDOWN
        )

        if target == "ALL":
            target_chats = [cid for cid, info in approved_chats.items() if info.get("approved")]
        else:
            target_chats = [target]

        for cid in target_chats:
            sessions[cid] = {
                "mode": flow, "subject": subject, "exam": exam,
                "level": level, "count": count, "running": True,
                "done": 0
            }
        save_sessions()

        for cid in target_chats:
            if flow == "post":
                asyncio.create_task(run_study_session(context, int(cid), subject, exam, level, count))
            else:
                asyncio.create_task(run_quiz_session(context, int(cid), subject, exam, level, count))

        context.user_data.clear()
        return

# ─────────────────────────────────────────────
# STUDY MATERIAL SESSION
# ─────────────────────────────────────────────

async def run_study_session(context, chat_id: int, subject: str, exam: str, level: str, total: int):
    logger.info(f"Study session started: chat={chat_id} subject={subject} exam={exam} level={level} count={total}")
    batch_size = 5
    posted = 0
    batch_num = 0

    while posted < total:
        if not sessions.get(str(chat_id), {}).get("running"):
            break

        remaining = total - posted
        this_batch = min(batch_size, remaining)
        batch_num += 1

        prompt = f"""
You are an expert {exam} preparation coach. Generate {this_batch} detailed study material posts for Telegram.

Subject: {subject}
Exam: {exam}
Difficulty: {level}
Batch: {batch_num}

Rules:
- Each post must be unique and educational
- Use simple Hindi-English mix (Hinglish) that students understand
- Format each post with emoji headings, bullet points, key points
- Include: Topic name, Key concepts, Important facts, Memory tricks (where applicable)
- End each post with "💡 Pro Tip:" related to the topic
- Separate each post with exactly: ---NEXT---

Generate {this_batch} posts now:
"""
        raw = await gemini_ask(prompt)
        if not raw:
            await asyncio.sleep(10)
            continue

        posts = [p.strip() for p in raw.split("---NEXT---") if p.strip()]
        for post_text in posts[:this_batch]:
            if not sessions.get(str(chat_id), {}).get("running"):
                break
            try:
                msg = (
                    f"📖 *{exam} Study Material*\n"
                    f"📚 {subject} | 📊 {level} | #{posted+1}/{total}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{post_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤖 _ALGO-BOT — Powered by Gemini AI_"
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg[:4096],
                    parse_mode=ParseMode.MARKDOWN
                )
                posted += 1
                sessions[str(chat_id)]["done"] = posted
                save_sessions()
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Post send error (chat={chat_id}): {e}")
                await asyncio.sleep(5)

    sessions[str(chat_id)]["running"] = False
    save_sessions()
    logger.info(f"Study session done: chat={chat_id} posted={posted}")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"✅ Study session complete!\n📢 Chat: `{chat_id}`\n📝 Posted: {posted}/{total}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

# ─────────────────────────────────────────────
# QUIZ SESSION
# ─────────────────────────────────────────────

async def run_quiz_session(context, chat_id: int, subject: str, exam: str, level: str, total: int):
    logger.info(f"Quiz session started: chat={chat_id} subject={subject} exam={exam} level={level} count={total}")
    batch_size = 10
    sent = 0
    batch_num = 0

    while sent < total:
        if not sessions.get(str(chat_id), {}).get("running"):
            break

        remaining = total - sent
        this_batch = min(batch_size, remaining)
        batch_num += 1

        prompt = f"""
Generate {this_batch} multiple-choice quiz questions for {exam} exam preparation.

Subject: {subject}
Exam: {exam}
Difficulty: {level}
Batch: {batch_num}

STRICT FORMAT — Return ONLY valid JSON array, no other text:
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Brief explanation why this answer is correct"
  }}
]

correct = index of correct option (0-3)
Generate exactly {this_batch} questions now in JSON format:
"""
        raw = await gemini_ask(prompt)
        if not raw:
            await asyncio.sleep(10)
            continue

        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            questions = json.loads(clean)
        except Exception as e:
            logger.error(f"Quiz JSON parse error: {e}\nRaw: {raw[:200]}")
            await asyncio.sleep(5)
            continue

        for q in questions[:this_batch]:
            if not sessions.get(str(chat_id), {}).get("running"):
                break
            try:
                question_text = f"🎯 *{exam}* Quiz #{sent+1}/{total}\n\n{q['question']}"
                options = q["options"]
                correct_idx = int(q["correct"])
                explanation = q.get("explanation", "")

                await context.bot.send_poll(
                    chat_id=chat_id,
                    question=question_text[:300],
                    options=[o[:100] for o in options[:4]],
                    type=Poll.QUIZ,
                    correct_option_id=correct_idx,
                    explanation=f"✅ {explanation}"[:200] if explanation else None,
                    open_period=30,
                    is_anonymous=False
                )
                sent += 1
                sessions[str(chat_id)]["done"] = sent
                save_sessions()
                await asyncio.sleep(32)
            except Exception as e:
                logger.error(f"Quiz send error (chat={chat_id}): {e}")
                await asyncio.sleep(5)

    sessions[str(chat_id)]["running"] = False
    save_sessions()
    logger.info(f"Quiz session done: chat={chat_id} sent={sent}")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"✅ Quiz session complete!\n📢 Chat: `{chat_id}`\n🧩 Sent: {sent}/{total}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

# ─────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set!")
    if not ADMIN_IDS:
        raise ValueError("ADMIN_IDS environment variable not set!")

    logger.info(f"Starting ALGO-BOT | Admins: {ADMIN_IDS}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("algo-post", cmd_post))
    app.add_handler(CommandHandler("algo-quizzes", cmd_quizzes))
    app.add_handler(CommandHandler("algo-list", cmd_list))
    app.add_handler(CommandHandler("algo-approve", cmd_approve))
    app.add_handler(CommandHandler("algo-reject", cmd_reject))
    app.add_handler(CommandHandler("algo-stop", cmd_stop))
    app.add_handler(CommandHandler("algo-status", cmd_status))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL, fallback_handler))

    from telegram.ext import ChatMemberHandler
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    logger.info("Bot polling started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
