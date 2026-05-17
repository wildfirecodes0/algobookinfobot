# 🤖 ALGO-BOT — Govt Exam Preparation Telegram Bot

**Powered by Gemini AI** | UPSC, SSC, IBPS, RRB aur baaki sab exams ke liye

---

## ✨ Features

- ✅ **Sirf approved chats me post karta hai** — unauthorized chats/groups me kuch nahi
- ✅ **Personal messages me sirf admin ko response** — baki sabko total silence
- ✅ **Admin Approval System** — har naye channel/group ko manually approve karna padega
- ✅ **AI-Powered Study Material** — Gemini AI se generate hota hai real-time
- ✅ **100+ Quiz Support** — 30 second interval par automatic quiz polls
- ✅ **Multi-Chat Support** — ek saath multiple channels me post kar sakta hai
- ✅ **Session Management** — istop karo jab chahein

---

## 📁 File Structure

```
algo_bot/
├── bot.py              # Main bot code
├── run.py              # Launcher (loads .env automatically)
├── requirements.txt    # Python dependencies
├── .env                # Aapki secret keys (khud banao)
├── .env.example        # Template
├── approved_chats.json # Auto-created: approved channels list
└── sessions.json       # Auto-created: active sessions
```

---

## 🚀 Setup Guide

### Step 1: Requirements Install Karo

```bash
pip install -r requirements.txt
```

### Step 2: Bot Token Banao

1. Telegram me `@BotFather` ko open karo
2. `/newbot` command bhejo
3. Naam aur username do
4. Token copy karo

### Step 3: Gemini API Key Lo

1. https://aistudio.google.com/ pe jao
2. "Get API Key" pe click karo
3. Key copy karo

### Step 4: Apna Telegram User ID Nikalo

- `@userinfobot` ko Telegram me message karo — wo aapka numeric ID batayega

### Step 5: .env File Banao

```bash
cp .env.example .env
```

`.env` file kholo aur fill karo:

```
BOT_TOKEN=1234567890:ABCdef...
GEMINI_API_KEY=AIzaSy...
ADMIN_IDS=123456789
```

### Step 6: Bot Start Karo

```bash
python run.py
```

---

## 📋 Commands

| Command | Kaun use kar sakta hai | Kya karta hai |
|---|---|---|
| `/start` | Admin (private chat me) | Bot ka welcome message |
| `/algo-post` | Admin | Study material post karna shuru karo |
| `/algo-quizzes` | Admin | Quiz session shuru karo |
| `/algo-list` | Admin | Sab registered channels/groups ki list |
| `/algo-approve <id>` | Admin | Kisi chat ko approve karo |
| `/algo-reject <id>` | Admin | Kisi chat ko reject/remove karo |
| `/algo-stop` | Admin | Sab running sessions band karo |
| `/algo-status` | Admin | Bot ka current status dekho |

---

## 🔄 Workflow

```
Admin → /algo-post ya /algo-quizzes
         ↓
    Chat select karo (inline buttons)
         ↓
    Subject chuniye (GK, History, Polity, etc.)
         ↓
    Exam chuniye (UPSC, SSC, IBPS, etc.)
         ↓
    Level chuniye (Beginner / Intermediate / Advanced)
         ↓
    Count chuniye (kitne posts/quizzes)
         ↓
    Confirm → Bot automatically post karna shuru kar deta hai!
```

---

## 🔐 Security Rules

1. **Private chats** → Sirf admin ko response, baaki sab ko complete silence
2. **Groups/Channels** → Sirf approved wale groups me post hoga
3. **New chat join** → Admin ko notification milegi, manually approve karna hoga
4. **Unauthorized chat** → Bot kuch bhi nahi bolega, silently ignore

---

## 🆕 Bot Ko Channel Me Add Kaise Kare

1. Bot ko channel admin banao (Telegram channel settings me)
2. Bot automatically admin ko notification bhejega
3. Admin `/algo-approve <chat_id>` se approve kare
4. Ab uss channel me post ho sakta hai!

---

## ⚙️ Advanced Tips

- **Multiple admins** — `ADMIN_IDS=111,222,333` (comma se alag karo)
- **Session during posting** — `/algo-stop` se kisi bhi waqt band kar sakte ho
- **Quiz format** — Ye Telegram native Quiz polls use karta hai (timer ke saath)
- **Study material** — Hinglish me hota hai, students ke liye easy

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| Bot respond nahi kar raha | `.env` file check karo, BOT_TOKEN sahi hai? |
| Gemini error aa raha hai | GEMINI_API_KEY sahi hai? Quota check karo |
| Channel me post nahi ho raha | Bot ko admin banao aur `/algo-approve` karo |
| Quiz nahi aa raha | Bot ko group admin hona chahiye (poll bhejne ke liye) |

---

## 📞 Support

Koi problem ho to log file dekho: `algo_bot.log`
