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
    ContextTypes, CallbackQueryHandler, ChatMemberHandler
)
from telegram.constants import ParseMode
from google import genai

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
# PERSISTENCE
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
        return is_admin(user.id)
    return str(chat.id) in approved_chats and approved_chats[str(chat.id)].get("approved")

# ─────────────────────────────────────────────
# CHAT MEMBER HANDLER
# ─────────────────────────────────────────────

async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat = result.chat
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
                        f"🔔 *Bot Added to New Chat!*\n\n"
                        f"📛 *Name:* {chat.title or chat.username}\n"
                        f"🆔 *Chat ID:* `{chat.id}`\n"
                        f"📂 *Type:* {chat.type}\n\n"
                        f"To approve: `/algo_approve {chat.id}`\n"
                        f"To reject: `/algo_reject {chat.id}`"
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
    await update.message.reply_text(
        "👋 *ALGO-BOT is Active!*\n\n"
        "📚 Govt Exam Preparation Bot — Powered by Gemini AI\n\n"
        "*Admin Commands:*\n"
        "`/algo_post` — Post study material\n"
        "`/algo_quizzes` — Start a quiz session\n"
        "`/algo_list` — List all approved chats\n"
        "`/algo_approve <chat_id>` — Approve a chat\n"
        "`/algo_reject <chat_id>` — Reject a chat\n"
        "`/algo_stop` — Stop all running sessions\n"
        "`/algo_status` — View bot status",
        parse_mode=ParseMode.MARKDOWN
    )

# ─────────────────────────────────────────────
# /algo_approve  /algo_reject
# ─────────────────────────────────────────────

async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/algo_approve <chat_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    chat_id = context.args[0].strip()
    if chat_id in approved_chats:
        approved_chats[chat_id]["approved"] = True
        save_approved()
        await update.message.reply_text(f"✅ Chat `{chat_id}` has been approved!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ Chat `{chat_id}` not found in list.", parse_mode=ParseMode.MARKDOWN)

async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/algo_reject <chat_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    chat_id = context.args[0].strip()
    if chat_id in approved_chats:
        approved_chats.pop(chat_id)
        save_approved()
        await update.message.reply_text(f"🗑️ Chat `{chat_id}` has been rejected and removed!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ Chat `{chat_id}` not found in list.", parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
# /algo_list
# ─────────────────────────────────────────────

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not approved_chats:
        await update.message.reply_text("📭 No chats registered yet.")
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
# /algo_status
# ─────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    approved_count  = sum(1 for v in approved_chats.values() if v.get("approved"))
    pending_count   = len(approved_chats) - approved_count
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
# /algo_stop
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
    await update.message.reply_text(f"🛑 {stopped} session(s) have been stopped.")

# ─────────────────────────────────────────────
# DATA LISTS
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
    "English", "Hindi", "Mixed (All)"
]

LEVELS = ["Beginner", "Intermediate", "Advanced"]

# ─────────────────────────────────────────────
# /algo_post
# ─────────────────────────────────────────────

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["flow"] = "post"
    context.user_data["target_chat"] = None

    approved_list = [(cid, info) for cid, info in approved_chats.items() if info.get("approved")]
    if not approved_list:
        await update.message.reply_text(
            "⚠️ No approved chats found. Use `/algo_approve <chat_id>` first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    kb = [[InlineKeyboardButton(
        f"{info['type'].upper()}: {info['title'][:30]}",
        callback_data=f"target|{cid}"
    )] for cid, info in approved_list]
    kb.append([InlineKeyboardButton("📢 Post to All Approved Chats", callback_data="target|ALL")])
    await update.message.reply_text(
        "📌 *Select target chat:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# ─────────────────────────────────────────────
# /algo_quizzes
# ─────────────────────────────────────────────

async def cmd_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["flow"] = "quiz"
    context.user_data["target_chat"] = None

    approved_list = [(cid, info) for cid, info in approved_chats.items() if info.get("approved")]
    if not approved_list:
        await update.message.reply_text("⚠️ No approved chats found.", parse_mode=ParseMode.MARKDOWN)
        return

    kb = [[InlineKeyboardButton(
        f"{info['type'].upper()}: {info['title'][:30]}",
        callback_data=f"target|{cid}"
    )] for cid, info in approved_list]
    kb.append([InlineKeyboardButton("📢 Send Quiz to All Approved Chats", callback_data="target|ALL")])
    await update.message.reply_text(
        "🧩 *Select target chat for quiz:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# ─────────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    data = query.data
    flow = context.user_data.get("flow")

    if data.startswith("target|"):
        context.user_data["target_chat"] = data.split("|", 1)[1]
        subjects = SUBJECTS_STUDY if flow == "post" else SUBJECTS_QUIZ
        kb = [[InlineKeyboardButton(s, callback_data=f"subject|{s}")] for s in subjects]
        label = "Study Material" if flow == "post" else "Quiz"
        await query.edit_message_text(
            f"📚 *{label}* — Select a subject:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("subject|"):
        context.user_data["subject"] = data.split("|", 1)[1]
        kb = [[InlineKeyboardButton(e, callback_data=f"exam|{e}")] for e in EXAMS]
        await query.edit_message_text(
            f"✅ Subject: *{context.user_data['subject']}*\n\n🎯 Select exam:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("exam|"):
        context.user_data["exam"] = data.split("|", 1)[1]
        kb = [[InlineKeyboardButton(l, callback_data=f"level|{l}")] for l in LEVELS]
        await query.edit_message_text(
            f"✅ Exam: *{context.user_data['exam']}*\n\n📊 Select difficulty level:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("level|"):
        context.user_data["level"] = data.split("|", 1)[1]
        if flow == "post":
            kb = [
                [InlineKeyboardButton("5 Posts", callback_data="count|5"),
                 InlineKeyboardButton("10 Posts", callback_data="count|10")],
                [InlineKeyboardButton("15 Posts", callback_data="count|15"),
                 InlineKeyboardButton("20 Posts", callback_data="count|20")],
            ]
            await query.edit_message_text(
                f"✅ Level: *{context.user_data['level']}*\n\n📝 How many posts to send?",
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
                f"✅ Level: *{context.user_data['level']}*\n\n🧩 How many quizzes? (30 sec interval each)",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )

    elif data.startswith("count|"):
        context.user_data["count"] = int(data.split("|", 1)[1])
        subject = context.user_data["subject"]
        exam    = context.user_data["exam"]
        level   = context.user_data["level"]
        count   = context.user_data["count"]
        target  = context.user_data["target_chat"]
        mode_label = "Study Material Posts" if flow == "post" else "Quizzes"
        kb = [
            [InlineKeyboardButton("✅ Yes, Start!", callback_data="confirm|yes")],
            [InlineKeyboardButton("❌ Cancel", callback_data="confirm|no")],
        ]
        await query.edit_message_text(
            f"📋 *Confirm Session:*\n\n"
            f"📚 Subject: *{subject}*\n"
            f"🎯 Exam: *{exam}*\n"
            f"📊 Level: *{level}*\n"
            f"🔢 Count: *{count} {mode_label}*\n"
            f"📢 Target: *{'All Approved Chats' if target == 'ALL' else target}*\n\n"
            f"Ready to start?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("confirm|"):
        if data.split("|", 1)[1] == "no":
            await query.edit_message_text("❌ Session cancelled.")
            context.user_data.clear()
            return

        flow    = context.user_data["flow"]
        subject = context.user_data["subject"]
        exam    = context.user_data["exam"]
        level   = context.user_data["level"]
        count   = context.user_data["count"]
        target  = context.user_data["target_chat"]

        await query.edit_message_text(
            f"🚀 *Session Started!*\n"
            f"📚 {subject} | 🎯 {exam} | 📊 {level} | 🔢 {count}",
            parse_mode=ParseMode.MARKDOWN
        )

        target_chats = (
            [cid for cid, info in approved_chats.items() if info.get("approved")]
            if target == "ALL" else [target]
        )

        for cid in target_chats:
            sessions[cid] = {
                "mode": flow, "subject": subject, "exam": exam,
                "level": level, "count": count, "running": True, "done": 0
            }
        save_sessions()

        for cid in target_chats:
            if flow == "post":
                asyncio.create_task(run_study_session(context, int(cid), subject, exam, level, count))
            else:
                asyncio.create_task(run_quiz_session(context, int(cid), subject, exam, level, count))

        context.user_data.clear()

# ─────────────────────────────────────────────
# STUDY MATERIAL SESSION
# ─────────────────────────────────────────────

async def run_study_session(context, chat_id: int, subject: str, exam: str, level: str, total: int):
    logger.info(f"Study session started | chat={chat_id} | subject={subject} | exam={exam} | level={level} | total={total}")
    batch_size = 5
    posted = 0
    batch_num = 0

    while posted < total:
        if not sessions.get(str(chat_id), {}).get("running"):
            break
        this_batch = min(batch_size, total - posted)
        batch_num += 1

        prompt = f"""
You are an expert {exam} preparation coach. Generate {this_batch} detailed study material posts for Telegram.

Subject: {subject}
Exam: {exam}
Difficulty: {level}
Batch: {batch_num}

Rules:
- Each post must be unique and educational
- Write in clear English with simple language
- Format each post with emoji headings and bullet points
- Include: Topic name, Key concepts, Important facts, Memory tricks where applicable
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
                logger.error(f"Post send error | chat={chat_id} | error={e}")
                await asyncio.sleep(5)

    sessions[str(chat_id)]["running"] = False
    save_sessions()
    logger.info(f"Study session complete | chat={chat_id} | posted={posted}/{total}")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"✅ *Study Session Complete!*\n\n"
                f"📢 Chat: `{chat_id}`\n"
                f"📝 Posted: {posted}/{total}\n"
                f"📚 Subject: {subject} | 🎯 {exam}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

# ─────────────────────────────────────────────
# QUIZ SESSION
# ─────────────────────────────────────────────

async def run_quiz_session(context, chat_id: int, subject: str, exam: str, level: str, total: int):
    logger.info(f"Quiz session started | chat={chat_id} | subject={subject} | exam={exam} | level={level} | total={total}")
    batch_size = 10
    sent = 0
    batch_num = 0

    while sent < total:
        if not sessions.get(str(chat_id), {}).get("running"):
            break
        this_batch = min(batch_size, total - sent)
        batch_num += 1

        prompt = f"""
Generate {this_batch} multiple-choice quiz questions for {exam} exam preparation.

Subject: {subject}
Exam: {exam}
Difficulty: {level}
Batch: {batch_num}

Return ONLY a valid JSON array, no extra text, no markdown fences:
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Brief explanation of the correct answer"
  }}
]

correct = index of correct option (0 to 3)
Generate exactly {this_batch} questions:
"""
        raw = await gemini_ask(prompt)
        if not raw:
            await asyncio.sleep(10)
            continue

        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            questions = json.loads(clean)
        except Exception as e:
            logger.error(f"Quiz JSON parse error | chat={chat_id} | error={e}")
            await asyncio.sleep(5)
            continue

        for q in questions[:this_batch]:
            if not sessions.get(str(chat_id), {}).get("running"):
                break
            try:
                question_text = f"🎯 [{exam}] Quiz #{sent+1}/{total}\n\n{q['question']}"
                explanation   = q.get("explanation", "")
                await context.bot.send_poll(
                    chat_id=chat_id,
                    question=question_text[:300],
                    options=[o[:100] for o in q["options"][:4]],
                    type=Poll.QUIZ,
                    correct_option_id=int(q["correct"]),
                    explanation=f"✅ {explanation}"[:200] if explanation else None,
                    open_period=30,
                    is_anonymous=False
                )
                sent += 1
                sessions[str(chat_id)]["done"] = sent
                save_sessions()
                await asyncio.sleep(32)
            except Exception as e:
                logger.error(f"Quiz send error | chat={chat_id} | error={e}")
                await asyncio.sleep(5)

    sessions[str(chat_id)]["running"] = False
    save_sessions()
    logger.info(f"Quiz session complete | chat={chat_id} | sent={sent}/{total}")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"✅ *Quiz Session Complete!*\n\n"
                f"📢 Chat: `{chat_id}`\n"
                f"🧩 Sent: {sent}/{total}\n"
                f"📚 Subject: {subject} | 🎯 {exam}",
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
        raise ValueError("BOT_TOKEN is not set!")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set!")
    if not ADMIN_IDS:
        raise ValueError("ADMIN_IDS is not set!")

    logger.info(f"Starting ALGO-BOT | Admins: {ADMIN_IDS}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("algo_post",    cmd_post))
    app.add_handler(CommandHandler("algo_quizzes", cmd_quizzes))
    app.add_handler(CommandHandler("algo_list",    cmd_list))
    app.add_handler(CommandHandler("algo_approve", cmd_approve))
    app.add_handler(CommandHandler("algo_reject",  cmd_reject))
    app.add_handler(CommandHandler("algo_stop",    cmd_stop))
    app.add_handler(CommandHandler("algo_status",  cmd_status))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL, fallback_handler))

    logger.info("Bot polling started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
