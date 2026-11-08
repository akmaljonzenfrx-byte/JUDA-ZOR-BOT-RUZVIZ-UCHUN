# -*- coding: utf-8 -*-
"""
KAROCHI — sodda versiya (BITTA FAYL)
python-telegram-bot 21.6 | SQLite | Flask keep-alive
ENV: BOT_TOKEN, ADMIN_IDS (vergul bilan), SUPPORT (ixtiyoriy), GROQ_API_KEY / OPENROUTER_API_KEY (ixtiyoriy)
"""
import os, re, html, time, random, string, sqlite3, asyncio, logging, threading
import httpx
from flask import Flask
from telegram import InlineKeyboardButton as IB, InlineKeyboardMarkup as IM, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x) for x in re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))}
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "karochi.db")
SUPPORT = os.getenv("SUPPORT", "@ruzvix")
PORT = int(os.getenv("PORT", "8080"))

WELCOME_BONUS = 10
REF_ALMAZ = 7
DAILY_SEC = 24 * 3600
SPIN_SEC = 3600
ZAR_COST = 5
GUESS_COST = 2
GUESS_WIN = 8
AI_DAILY = 30

SPIN_PRIZES = [(0, 40), (5, 30), (10, 20), (25, 8), (100, 2)]
PKGS = [("BASE", "🟢", 1, 50), ("PREMIUM", "🟡", 2, 120), ("VIP", "🔴", 3, 250)]
BRANDS = {
    "iPhone": ["iPhone 11", "iPhone 12", "iPhone 13", "iPhone 14", "iPhone 15"],
    "Samsung": ["Galaxy A15", "Galaxy A25", "Galaxy A55", "Galaxy S23 Ultra", "Galaxy S24 Ultra"],
    "Xiaomi": ["Xiaomi 13", "Xiaomi 14", "Xiaomi 14 Pro", "Xiaomi 15"],
    "Redmi": ["Redmi 12", "Redmi Note 12", "Redmi Note 13", "Redmi Note 14 Pro"],
    "POCO": ["POCO X5 Pro", "POCO X6", "POCO X7 Pro", "POCO F6"],
    "Realme": ["Realme 12", "Realme 13", "Realme GT 6"],
    "Infinix": ["Hot 30", "Hot 40", "Note 40", "GT 20 Pro"],
    "Tecno": ["Spark 20", "Spark 30", "Camon 30", "Pova 6"],
    "OPPO": ["A58", "A78", "Reno 11", "Reno 12"],
    "Vivo": ["Y36", "V30", "V40", "X100"],
}

FACTS = [
    "🍯 Qadimgi Misr qabrlaridan 3000 yillik asal topilgan, va u hali ham yeyishga yaroqli bo'lgan.",
    "🐙 Oktopusning uchta yuragi bor va qoni ko'k rangda.",
    "🍌 Botanika nuqtai nazaridan banan berry hisoblanadi, qulupnay esa emas.",
    "🪐 Venerada bir kun, bir yildan uzunroq davom etadi.",
    "🧠 Uyqu paytida miya kun davomida to'plangan xotiralarni saralaydi.",
]
STORIES = [
    "🕯 Qishloqdagi eski masjid hovlisida har tunda bir chiroq yonadi. Bolalar aytishadi: uni hech kim yoqmaydi...",
    "📞 Bu kecha telefon jiringladi. Trubkada faqat sizning ismingiz aytildi, lekin ovoz o'zingizniki edi.",
    "🪞 Oynadagi odam sizdan bir soniya kechikib qo'lini ko'tardi. Siz tushirdingiz... u tushirmadi.",
    "🌑 Metroning oxirgi bekatida ikki eshik ochildi. Bittasidan odamlar tushdi, ikkinchisidan hech kim chiqmadi.",
]
CURSES = [
    "🔮 Bugun ichingdagi tun seni kuzatadi. Ertalab ikki marta orqangga qarab ol.",
    "🕷 Oynaga qaramagin. U sendan oldin uyg'onadi.",
    "👁 Sirli xabar yetib keladi. Javob bermasang, o'zi keladi.",
]

HELP_SYS = ("Sen KAROCHI botining yordamchisisan. Faqat o'zbek tilida (lotin) qisqa va aniq javob ber. "
            "Bot: /start da 3 ta tugma bor. ⚙️ Tekin nastroyka: brend, model, paket tanlanadi, "
            "paket referral yoki almaz bilan ochiladi, maxfiy kod chiqadi va uni supportga yuborasiz. "
            "💎 Tekin almaz: do'st taklif qilib almaz ishlash, kunlik sovg'a, promo kod, spin, zar, son tanlash, "
            "Qorong'u dunyo. 🤖 Murojaat: shu yerda savol berasiz.")

WELCOME = "🔥 <b>KAROCHI</b>\n\nQuyidagilardan birini tanlang 👇"

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("karochi")

# ───────────────────────── DB ─────────────────────────
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, name TEXT,
 almaz INTEGER DEFAULT 0, refs INTEGER DEFAULT 0, ref_by INTEGER, last_daily INTEGER DEFAULT 0,
 last_spin INTEGER DEFAULT 0, ai_day TEXT DEFAULT '', ai_count INTEGER DEFAULT 0, joined INTEGER);
CREATE TABLE IF NOT EXISTS brands(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS models(id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER, name TEXT,
 UNIQUE(brand_id, name));
CREATE TABLE IF NOT EXISTS packages(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, emoji TEXT,
 refs INTEGER, price INTEGER);
CREATE TABLE IF NOT EXISTS codes(code TEXT PRIMARY KEY, user_id INTEGER, phone TEXT, pkg TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, amount INTEGER, max_uses INTEGER DEFAULT 0,
 used INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS promo_uses(user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code));
"""


def q(sql, a=(), one=False):
    with LOCK:
        cur = db.execute(sql, a)
        db.commit()
        return cur.fetchone() if one else cur.fetchall()


def init_db():
    db.executescript(SCHEMA)
    for b, models in BRANDS.items():
        q("INSERT OR IGNORE INTO brands(name) VALUES(?)", (b,))
        bid = q("SELECT id FROM brands WHERE name=?", (b,), True)["id"]
        for m in models:
            q("INSERT OR IGNORE INTO models(brand_id, name) VALUES(?,?)", (bid, m))
    if not q("SELECT 1 FROM packages", (), True):
        for p in PKGS:
            q("INSERT INTO packages(name, emoji, refs, price) VALUES(?,?,?,?)", p)


# ───────────────────────── YORDAMCHILAR ─────────────────────────
def C(text, data):
    return IB(text, callback_data=data)


def now():
    return int(time.time())


def esc(s):
    return html.escape(str(s if s is not None else ""))


def fmt(sec):
    h, rem = divmod(max(0, int(sec)), 3600)
    m = rem // 60
    return f"{h} soat {m} daqiqa" if h else f"{m} daqiqa"


def user(uid):
    return q("SELECT * FROM users WHERE id=?", (uid,), True)


def add_almaz(uid, n):
    q("UPDATE users SET almaz=almaz+? WHERE id=?", (n, uid))


def ensure(u, ref=None):
    """Yangi bo'lsa taklif qilgan foydalanuvchi id sini qaytaradi (yo'q bo'lsa None)."""
    r = user(u.id)
    name = (u.first_name or "")[:40]
    if r:
        q("UPDATE users SET username=?, name=? WHERE id=?", (u.username, name, u.id))
        return None
    inv = ref if (ref and ref != u.id and user(ref)) else None
    q("INSERT INTO users(id, username, name, almaz, ref_by, joined) VALUES(?,?,?,?,?,?)",
      (u.id, u.username, name, WELCOME_BONUS, inv, now()))
    if inv:
        q("UPDATE users SET almaz=almaz+?, refs=refs+1 WHERE id=?", (REF_ALMAZ, inv))
    return inv


def grid(btns, back_to="home", per=2):
    rows_ = [btns[i:i + per] for i in range(0, len(btns), per)]
    rows_.append([C("⬅️ Orqaga", back_to)])
    return IM(rows_)


def main_kb():
    return IM([[C("⚙️ Tekin nastroyka", "nast")],
               [C("💎 Tekin almaz", "almaz")],
               [C("🤖 Murojaat", "ai")]])


def almaz_kb():
    return IM([
        [C("🎁 Kunlik sovg'a", "daily"), C("👥 Do'st taklif", "invite")],
        [C("🎟 Promo kod", "promo"), C("🏆 Reyting", "top")],
        [C("🎰 Spin", "spin"), C("🎲 Zar (5 💎)", "zar")],
        [C("🔢 Son tanlash (2 💎)", "guess"), C("🌑 Qorong'u dunyo", "dark")],
        [C("⬅️ Orqaga", "home")],
    ])


DARK_KB = IM([
    [C("🤯 Dahshat fakt", "dk:f"), C("👻 Hikoya", "dk:s")],
    [C("🔮 Qarg'ish", "dk:c")],
    [C("⬅️ Orqaga", "almaz")],
])


async def edit(cq, text, kb=None):
    try:
        await cq.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except BadRequest:
        pass


# ───────────────────────── /START va ADMIN ─────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref = None
    if ctx.args and ctx.args[0].startswith("ref_"):
        try:
            ref = int(ctx.args[0][4:])
        except ValueError:
            ref = None
    inv = ensure(u, ref)
    ctx.user_data.clear()
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_kb())
    if inv:
        try:
            await ctx.bot.send_message(inv, f"🎉 Yangi do'st qo'shildi: <b>{esc(u.first_name)}</b>\n"
                                            f"💎 +{REF_ALMAZ} almaz!", parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def cmd_admin(update, ctx):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text(
        "👑 Admin buyruqlari:\n"
        "/addbrand Nom\n"
        "/addmodel Brend | Model\n"
        "/addpromo KOD MIQDOR LIMIT (0 = cheksiz)\n"
        "/stats")


async def cmd_addbrand(update, ctx):
    if update.effective_user.id not in ADMIN_IDS:
        return
    name = " ".join(ctx.args).strip()
    if not name:
        return await update.message.reply_text("Format: /addbrand Nom")
    q("INSERT OR IGNORE INTO brands(name) VALUES(?)", (name,))
    await update.message.reply_text(f"✅ {name} qo'shildi")


async def cmd_addmodel(update, ctx):
    if update.effective_user.id not in ADMIN_IDS:
        return
    parts = " ".join(ctx.args).split("|")
    if len(parts) != 2:
        return await update.message.reply_text("Format: /addmodel Brend | Model")
    b = q("SELECT id FROM brands WHERE LOWER(name)=LOWER(?)", (parts[0].strip(),), True)
    if not b:
        return await update.message.reply_text("❌ Brend topilmadi. Avval /addbrand qiling.")
    q("INSERT OR IGNORE INTO models(brand_id, name) VALUES(?,?)", (b["id"], parts[1].strip()))
    await update.message.reply_text(f"✅ {parts[1].strip()} qo'shildi")


async def cmd_addpromo(update, ctx):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(ctx.args) != 3 or not ctx.args[1].isdigit() or not ctx.args[2].isdigit():
        return await update.message.reply_text("Format: /addpromo KOD MIQDOR LIMIT")
    code, amt, lim = ctx.args[0].upper(), int(ctx.args[1]), int(ctx.args[2])
    q("INSERT OR REPLACE INTO promos(code, amount, max_uses, used) VALUES(?,?,?,0)", (code, amt, lim))
    await update.message.reply_text(f"✅ Promo: {code} (+{amt} 💎)")


async def cmd_stats(update, ctx):
    if update.effective_user.id not in ADMIN_IDS:
        return
    u = q("SELECT COUNT(*) AS c, COALESCE(SUM(almaz),0) AS s FROM users", (), True)
    c = q("SELECT COUNT(*) AS c FROM codes", (), True)
    await update.message.reply_text(f"📊 Foydalanuvchilar: {u['c']}\n💎 Jami almaz: {u['s']}\n"
                                    f"🔐 Berilgan kodlar: {c['c']}")


# ───────────────────────── 1) TEKIN NASTROYKA ─────────────────────────
async def h_home(cq, ctx, uid, a):
    await edit(cq, WELCOME, main_kb())


async def h_nast(cq, ctx, uid, a):
    bs = q("SELECT id, name FROM brands ORDER BY id")
    btns = [C(f"📱 {b['name']}", f"nb:{b['id']}") for b in bs]
    await edit(cq, "⚙️ <b>Tekin nastroyka</b>\n\nTelefon brendingizni tanlang 👇", grid(btns, "home"))


async def h_nb(cq, ctx, uid, a):
    bid = int(a[1])
    b = q("SELECT name FROM brands WHERE id=?", (bid,), True)
    if not b:
        return "Brend topilmadi"
    ms = q("SELECT id, name FROM models WHERE brand_id=? ORDER BY id", (bid,))
    btns = [C(f"📱 {m['name']}", f"nm:{m['id']}") for m in ms]
    await edit(cq, f"📱 <b>{esc(b['name'])}</b>\n\nModelingizni tanlang 👇", grid(btns, "nast"))


async def h_nm(cq, ctx, uid, a):
    mid = int(a[1])
    m = q("SELECT m.name, m.brand_id, b.name AS bn FROM models m JOIN brands b ON b.id=m.brand_id "
          "WHERE m.id=?", (mid,), True)
    if not m:
        return "Model topilmadi"
    pk = q("SELECT * FROM packages ORDER BY id")
    r = user(uid)
    lines = [f"{p['emoji']} <b>{esc(p['name'])}</b> — {p['refs']} referral yoki {p['price']} 💎" for p in pk]
    text = (f"📱 <b>{esc(m['bn'])} {esc(m['name'])}</b>\n\nSozlama paketini tanlang:\n\n" + "\n".join(lines) +
            f"\n\n👥 Referral: <b>{r['refs']}</b> | 💎 Balans: <b>{r['almaz']}</b>")
    btns = [C(f"{p['emoji']} {p['name']}", f"np:{mid}:{p['id']}") for p in pk]
    await edit(cq, text, grid(btns, f"nb:{m['brand_id']}", per=1))


async def h_np(cq, ctx, uid, a):
    mid, pid = int(a[1]), int(a[2])
    m = q("SELECT m.name, b.name AS bn FROM models m JOIN brands b ON b.id=m.brand_id WHERE m.id=?",
          (mid,), True)
    p = q("SELECT * FROM packages WHERE id=?", (pid,), True)
    r = user(uid)
    if not m or not p:
        return "Topilmadi"
    pay = None
    if r["refs"] >= p["refs"]:
        q("UPDATE users SET refs=refs-? WHERE id=?", (p["refs"], uid))
        pay = f"{p['refs']} referral"
    elif r["almaz"] >= p["price"]:
        add_almaz(uid, -p["price"])
        pay = f"{p['price']} 💎"
    if not pay:
        need_r = max(0, p["refs"] - r["refs"])
        need_a = max(0, p["price"] - r["almaz"])
        text = (f"🔐 <b>Yetarli emas</b>\n\n📱 {esc(m['bn'])} {esc(m['name'])}\n{p['emoji']} {esc(p['name'])}\n\n"
                f"👥 Yana <b>{need_r}</b> referral kerak\nyoki 💎 yana <b>{need_a}</b> almaz kerak")
        await edit(cq, text, grid([], f"nm:{mid}"))
        return None
    code = "KRC-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    q("INSERT INTO codes(code, user_id, phone, pkg, ts) VALUES(?,?,?,?,?)",
      (code, uid, f"{m['bn']} {m['name']}", p["name"], now()))
    text = (f"🎉 <b>Tayyor!</b>\n\n📱 {esc(m['bn'])} {esc(m['name'])}\n{p['emoji']} {esc(p['name'])} — sarflandi: {pay}\n\n"
            f"🔐 Kod: <code>{code}</code>\n\n⚠️ Kod bir martalik. Supportga yuboring: <b>{esc(SUPPORT)}</b>")
    await edit(cq, text, grid([], "nast"))
    return "✅ Kod yaratildi"


# ───────────────────────── 2) TEKIN ALMAZ ─────────────────────────
async def h_almaz(cq, ctx, uid, a):
    r = user(uid)
    text = f"💎 <b>Tekin almaz</b>\n\nBalans: <b>{r['almaz']}</b> 💎\n👥 Takliflar: {r['refs']}"
    await edit(cq, text, almaz_kb())


async def h_daily(cq, ctx, uid, a):
    r = user(uid)
    left = DAILY_SEC - (now() - r["last_daily"])
    if left > 0:
        return f"⏳ Kunlik sovg'a olingan. {fmt(left)}dan keyin."
    n = random.randint(5, 30)
    q("UPDATE users SET almaz=almaz+?, last_daily=? WHERE id=?", (n, now(), uid))
    await h_almaz(cq, ctx, uid, a)
    return f"🎁 +{n} almaz!"


async def h_invite(cq, ctx, uid, a):
    link = f"https://t.me/{ctx.bot.username}?start=ref_{uid}"
    text = (f"👥 <b>Do'st taklif qiling</b>\n\nHar bir do'stingiz uchun <b>+{REF_ALMAZ} 💎</b>\n\n"
            f"<code>{link}</code>")
    kb = IM([[IB("📤 Ulashish", url=f"https://t.me/share/url?url={link}&text=KAROCHI")],
             [C("⬅️ Orqaga", "almaz")]])
    await edit(cq, text, kb)


async def h_promo(cq, ctx, uid, a):
    ctx.user_data["await"] = "promo"
    await edit(cq, "🎟 <b>Promo kodni yuboring</b>\n\nKodni chatga yozing 👇", grid([], "almaz"))


async def h_top(cq, ctx, uid, a):
    rs = q("SELECT name, almaz FROM users ORDER BY almaz DESC LIMIT 10")
    lines = [f"{i + 1}. {esc(r['name'] or 'Noma’lum')} — {r['almaz']} 💎" for i, r in enumerate(rs)]
    await edit(cq, "🏆 <b>Reyting</b>\n\n" + ("\n".join(lines) or "Hali bo'sh"), grid([], "almaz"))


async def h_spin(cq, ctx, uid, a):
    r = user(uid)
    left = SPIN_SEC - (now() - r["last_spin"])
    status = "🟢 Hozir aylantirsa bo'ladi!" if left <= 0 else f"⏳ {fmt(left)}dan keyin"
    await edit(cq, f"🎰 <b>Spin</b>\n\nJackpot: 100 💎\n\n{status}\n💎 Balans: <b>{r['almaz']}</b>",
               IM([[C("🎰 Aylantirish", "spgo")], [C("⬅️ Orqaga", "almaz")]]))


async def h_spgo(cq, ctx, uid, a):
    r = user(uid)
    left = SPIN_SEC - (now() - r["last_spin"])
    if left > 0:
        return f"⏳ {fmt(left)}dan keyin"
    prize = random.choices([x for x, _ in SPIN_PRIZES], weights=[w for _, w in SPIN_PRIZES])[0]
    q("UPDATE users SET almaz=almaz+?, last_spin=? WHERE id=?", (prize, now(), uid))
    res = f"🎉 <b>+{prize} 💎!</b>" if prize else "😅 Omad kelmadi..."
    await edit(cq, f"🎰 <b>Natija</b>\n\n{res}\n💎 Balans: <b>{user(uid)['almaz']}</b>",
               IM([[C("⬅️ Orqaga", "almaz")]]))


async def h_zar(cq, ctx, uid, a):
    r = user(uid)
    if r["almaz"] < ZAR_COST:
        return f"❌ Kerak: {ZAR_COST} 💎"
    me, bot_ = random.randint(1, 6), random.randint(1, 6)
    add_almaz(uid, -ZAR_COST)
    if me > bot_:
        add_almaz(uid, 2 * ZAR_COST)
        res = f"🎉 Yutdingiz! +{ZAR_COST} 💎"
    elif me == bot_:
        add_almaz(uid, ZAR_COST)
        res = "🤝 Durang, stavka qaytdi."
    else:
        res = f"😔 Yutqazdingiz. -{ZAR_COST} 💎"
    text = (f"🎲 Siz: <b>{me}</b> | Bot: <b>{bot_}</b>\n\n{res}\n💎 Balans: <b>{user(uid)['almaz']}</b>")
    await edit(cq, text, IM([[C("🎲 Yana", "zar")], [C("⬅️ Orqaga", "almaz")]]))


async def h_guess(cq, ctx, uid, a):
    btns = [C(str(n), f"gs:{n}") for n in range(1, 6)]
    text = (f"🔢 <b>Son tanlash</b>\n\nBot 1 dan 5 gacha bitta son o'yladi.\n"
            f"Urinish: {GUESS_COST} 💎. To'g'ri topsangiz +{GUESS_WIN} 💎!")
    await edit(cq, text, grid(btns, "almaz", per=5))


async def h_gs(cq, ctx, uid, a):
    n = int(a[1])
    r = user(uid)
    if r["almaz"] < GUESS_COST:
        return f"❌ Kerak: {GUESS_COST} 💎"
    add_almaz(uid, -GUESS_COST)
    secret = random.randint(1, 5)
    if n == secret:
        add_almaz(uid, GUESS_WIN)
        res = f"🎉 To'g'ri! Bot {secret} deb o'ylagan edi. +{GUESS_WIN} 💎"
    else:
        res = f"😔 Noto'g'ri. Bot {secret} deb o'ylagan edi."
    await edit(cq, f"🔢 {res}\n💎 Balans: <b>{user(uid)['almaz']}</b>",
               IM([[C("🔁 Yana", "guess")], [C("⬅️ Orqaga", "almaz")]]))


async def h_dark(cq, ctx, uid, a):
    await edit(cq, "🌑 <b>Qorong'u dunyo</b>\n\nTanlang... ehtiyot bo'ling 👁", DARK_KB)


async def h_dk(cq, ctx, uid, a):
    pool = {"f": FACTS, "s": STORIES, "c": CURSES}[a[1]]
    await edit(cq, f"🌑 {esc(random.choice(pool))}", DARK_KB)


# ───────────────────────── 3) MUROJAAT (AI) ─────────────────────────
async def h_ai(cq, ctx, uid, a):
    ctx.user_data["await"] = "ai"
    await edit(cq, "🤖 <b>Murojaat</b>\n\nBot qanday ishlatilishini yoki savolingizni yozing 👇",
               grid([], "home"))


async def ask_ai(messages):
    async with httpx.AsyncClient(timeout=60) as c:
        for url, key, model in (
            ("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY, "llama-3.3-70b-versatile"),
            ("https://openrouter.ai/api/v1/chat/completions", OR_KEY, "meta-llama/llama-3.3-70b-instruct:free"),
        ):
            if not key:
                continue
            try:
                r = await c.post(url, headers={"Authorization": f"Bearer {key}"},
                                 json={"model": model, "messages": messages, "max_tokens": 600,
                                       "temperature": 0.6})
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"].strip()
                log.warning("AI %s: %s", r.status_code, r.text[:200])
            except Exception as e:
                log.warning("AI xato: %s", e)
    return None


async def ai_reply(update, ctx, uid, text):
    today = time.strftime("%Y-%m-%d")
    r = user(uid)
    count = r["ai_count"] if r["ai_day"] == today else 0
    if count >= AI_DAILY and uid not in ADMIN_IDS:
        await update.message.reply_text(f"⛔ Bugungi limit tugadi ({AI_DAILY} ta). Ertaga qaytib keling.")
        ctx.user_data["await"] = "ai"
        return
    q("UPDATE users SET ai_day=?, ai_count=? WHERE id=?", (today, count + 1, uid))
    hist = ctx.user_data.setdefault("hist", [])
    msgs = [{"role": "system", "content": HELP_SYS}] + hist[-6:] + [{"role": "user", "content": text}]
    ans = await ask_ai(msgs) or "⚠️ AI hozircha javob bera olmadi. Keyinroq urinib ko'ring."
    hist += [{"role": "user", "content": text}, {"role": "assistant", "content": ans}]
    del hist[:-6]
    await update.message.reply_text(ans, reply_markup=IM([[C("⬅️ Orqaga", "home")]]))
    ctx.user_data["await"] = "ai"


# ───────────────────────── MATN VA PROMO ─────────────────────────
async def redeem(update, uid, text):
    code = text.upper()
    p = q("SELECT * FROM promos WHERE code=?", (code,), True)
    if not p:
        msg = "❌ Bunday promo kod topilmadi."
    elif p["max_uses"] and p["used"] >= p["max_uses"]:
        msg = "😔 Bu promo kodning limiti tugagan."
    elif q("SELECT 1 FROM promo_uses WHERE user_id=? AND code=?", (uid, code), True):
        msg = "⚠️ Bu kodni allaqachon ishlatgansiz."
    else:
        q("UPDATE promos SET used=used+1 WHERE code=?", (code,))
        q("INSERT INTO promo_uses(user_id, code) VALUES(?,?)", (uid, code))
        add_almaz(uid, p["amount"])
        msg = f"🎉 Promo faollashtirildi! +{p['amount']} 💎"
    await update.message.reply_text(f"{msg}\n💎 Balans: {user(uid)['almaz']}", reply_markup=main_kb())


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ensure(u)
    mode = ctx.user_data.pop("await", None)
    text = (update.message.text or "").strip()
    if mode == "promo":
        return await redeem(update, u.id, text)
    if mode == "ai":
        return await ai_reply(update, ctx, u.id, text)
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_kb())


# ───────────────────────── ROUTER ─────────────────────────
ROUTES = {
    "home": h_home, "nast": h_nast, "nb": h_nb, "nm": h_nm, "np": h_np,
    "almaz": h_almaz, "daily": h_daily, "invite": h_invite, "promo": h_promo, "top": h_top,
    "spin": h_spin, "spgo": h_spgo, "zar": h_zar, "guess": h_guess, "gs": h_gs,
    "dark": h_dark, "dk": h_dk, "ai": h_ai,
}


async def on_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cq = update.callback_query
    ctx.user_data.pop("await", None)
    ensure(cq.from_user)
    a = (cq.data or "").split(":")
    alert = None
    try:
        h = ROUTES.get(a[0])
        if h:
            alert = await h(cq, ctx, cq.from_user.id, a)
    except Exception:
        log.exception("callback xato: %s", cq.data)
    try:
        await cq.answer(alert, show_alert=bool(alert))
    except Exception:
        pass


# ───────────────────────── WEB (keep-alive) ─────────────────────────
web = Flask(__name__)


@web.route("/")
def index():
    return "KAROCHI ishlayapti 🔥"


def run_web():
    web.run(host="0.0.0.0", port=PORT)


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi!")
    init_db()
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.set_event_loop(asyncio.new_event_loop())  # Python 3.14 uchun
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("addbrand", cmd_addbrand))
    app.add_handler(CommandHandler("addmodel", cmd_addmodel))
    app.add_handler(CommandHandler("addpromo", cmd_addpromo))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, on_text))
    log.info("KAROCHI ishga tushdi 🔥")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
