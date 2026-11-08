# -*- coding: utf-8 -*-
"""
KAROCHI — TO'LIQ BITTA FAYL (main.py)
Bosh menyu: ⚙️ Tekin nastroyka | 💎 Tekin almaz | 🤖 Murojaat
python-telegram-bot 21.6 | SQLite yoki Neon Postgres | Flask keep-alive | Groq / OpenRouter AI
requirements.txt: python-telegram-bot==21.6, flask, httpx, psycopg2-binary
ENV: BOT_TOKEN, ADMIN_IDS, GROQ_API_KEY, OPENROUTER_API_KEY, DB_PATH, DATABASE_URL,
     BACKUP_CHAT, RENDER_EXTERNAL_URL, PORT
"""
import os, re, html, time, random, string, shutil, sqlite3, asyncio, logging, threading, tempfile
from datetime import datetime, timedelta, timezone

import httpx
from flask import Flask
from telegram import (InlineKeyboardButton as IB, InlineKeyboardMarkup as IM, KeyboardButton,
                      ReplyKeyboardMarkup, Update)
from telegram.constants import ParseMode
from telegram.error import RetryAfter
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, MessageHandler,
                          ContextTypes, filters)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ENV_ADMINS = {int(x) for x in re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))}
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "karochi.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_PG = DATABASE_URL.startswith("postgres")
if IS_PG:
    import psycopg2
PORT = int(os.getenv("PORT", "8080"))
BACKUP_CHAT = os.getenv("BACKUP_CHAT", "").strip()
TZ = timezone(timedelta(hours=5))
HTML = ParseMode.HTML

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("karochi")
logging.getLogger("httpx").setLevel(logging.WARNING)

THEMES = {"olov": ("🔥", "Olov"), "muz": ("❄️", "Muz"), "karochi": ("🌈", "Karochi")}
THEME_ORDER = list(THEMES)

# ───────────────────────── MATNLAR VA SOZLAMALAR ─────────────────────────
D_WELCOME = ("🔥 <b>KAROCHI</b> — Free Fire universal boti!\n\n"
             "⚙️ Tekin nastroyka — telefoningizga ideal sensitivity\n"
             "💎 Tekin almaz — do'st taklif qiling, almaz ishlang, o'yin o'ynang\n"
             "🤖 Murojaat — bot qanday ishlashini so'rang\n\nQuyidagidan birini tanlang 👇")
D_EARN = ("💎 <b>Almaz ishlash</b>\n\nDo'stlaringizni taklif qiling, har bir tasdiqlangan do'st uchun "
          "<b>{reward} almaz</b> olasiz.\n\n👇 Havolangiz:\n{link}")
D_PROMO = ("🎁 <b>PROMO KOD</b>\n\nPromo kodni yuboring va bonus almaz oling.\n"
           "⚡ Ayrim kodlar cheklangan bo'ladi.\n👇 Kodingizni yozing:")
D_PHONE = ("🎯 <b>AI Sensitivity</b>\n\nTelefon modelini yozing, AI sizga General, Red Dot, 2X, 4X, AWM "
           "sozlamalarini beradi.\nMasalan: <code>Redmi Note 13</code>")
D_AI = "🤖 <b>Murojaat</b>\n\nQuyidagilardan birini tanlang 👇"
D_HOW = ("📈 <b>Darajani qanday oshiramiz?</b>\n\n• 👥 Har bir tasdiqlangan do'st uchun <b>+{pts} ball</b>\n"
         "• 🎁 Promo kod va bonus tasklardan foydalaning\n• 🔥 Faol bo'ling, ligalar ko'tariladi!")
D_GUIDE = ("ℹ️ <b>Sherik topish — qo'llanma</b>\n\n1️⃣ Pasportni to'ldiring (FF ID, level, mikrofon, izoh).\n"
           "2️⃣ E'lon bering — {hours} soat faol bo'ladi.\n3️⃣ Sherik qidiring va 🤝 taklif yuboring.\n"
           "⚠️ Haqoratli izoh uchun ban beriladi.")
D_SHOP = "🛒 <b>O'yin Do'koni</b>\n\nKategoriyani tanlang 👇"
D_SERVICE = "🎥 <b>Youtuber xizmatlari</b>\n\nXizmatlardan birini tanlang 👇"
D_SUB = "📣 <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>"
D_BAN = "🚫 Siz botdan foydalanishdan chetlatilgansiz."
D_MAINT = "🛠 Botda texnik ishlar olib borilmoqda. Birozdan so'ng urinib ko'ring."
D_NAST = ("⚙️ <b>Tekin nastroyka</b>\n\nTelefon brendingizni tanlang. Keyin modelni va paketni tanlaysiz.\n"
          "Paket referral yoki almaz bilan ochiladi.")
D_NHELP = ("🆘 <b>Yordam</b>\n\n1️⃣ Brendni tanlang\n2️⃣ Modelni tanlang\n3️⃣ Paketni tanlang\n"
           "4️⃣ Referral yoki almaz bilan to'lang\n5️⃣ Maxfiy kodni supportga yuboring.")
D_CHARS = ("Alok|Sho'x va energiyali DJ, musiqa va ritm haqida gapiradi\n"
           "Chrono|Jiddiy strateg, qisqa va aniq gapiradi\n"
           "K|Xotirjam professor, ilmiy tushuntiradi\n"
           "Kelly|Tez va jasur sprinter, shiddatli gapiradi\n"
           "Jota|Hazilkash ovchi, hazil bilan gapiradi\n"
           "Moco|Sirli xaker, jumboqlar bilan gapiradi")
D_SYS = ("Sen Free Fire bo'yicha professional Pro Coach san. Faqat o'zbek tilida (lotin) javob ber. "
         "Qisqa, aniq va amaliy maslahat ber: taktika, qurollar, xarita, rotatsiya, aim, jamoaviy o'yin.")
D_HELP_SYS = ("Sen KAROCHI botining yordamchisisan. Faqat o'zbek tilida (lotin) qisqa va aniq javob ber. "
              "Bot tuzilishi: Bosh menyuda 3 ta tugma bor. ⚙️ Tekin nastroyka: brend, model, paket tanlanadi, "
              "paket referral yoki almaz bilan ochiladi, maxfiy kod chiqadi va uni supportga yuborasiz. "
              "💎 Tekin almaz: do'st taklif qilib almaz ishlash, promo kod, spin, quti va zar o'yinlari, "
              "sherik topish, do'kon, reyting, Qorong'u dunyo. 🤖 Murojaat: shu yerda savol berasiz.")

# key: (default, label, type)  type: bool | int | text
S = {
    "bot_enabled": ("1", "🔌 Bot yoqilgan", "bool"),
    "captcha_on": ("1", "🤖 Captcha", "bool"),
    "phone_on": ("1", "📱 Telefon tasdiqlash", "bool"),
    "phone_prefix": ("998", "🌍 Telefon prefiksi (bo'sh=hammasi)", "text"),
    "ref_reward": ("7", "💎 Taklif uchun almaz", "int"),
    "ref_points": ("10", "⭐ Taklif uchun ball", "int"),
    "start_bonus": ("0", "🎉 Yangi foydalanuvchi bonusi", "int"),
    "free_spins": ("1", "🆓 Kunlik bepul spin", "int"),
    "paid_spins": ("2", "💰 Kunlik pullik spin", "int"),
    "spin_price": ("5", "💎 Pullik spin narxi", "int"),
    "min_withdraw": ("50", "💳 Minimal yechish (almaz)", "int"),
    "ai_limit": ("30", "🤖 Kunlik AI limit", "int"),
    "ad_hours": ("24", "⏰ Sherik e'loni muddati (soat)", "int"),
    "proofs_url": ("", "📜 Isbotlar havolasi (URL)", "text"),
    "proofs_chat": ("", "📣 Isbotlar kanali (@kanal yoki ID)", "text"),
    "support": ("@ruzvix", "📩 Support", "text"),
    "nast_ref": ("1", "🎁 Nastroyka uchun referral ishlatilsin", "bool"),
    "ai_model_groq": ("llama-3.3-70b-versatile", "🧠 Groq modeli", "text"),
    "ai_model_or": ("meta-llama/llama-3.3-70b-instruct:free", "🧠 OpenRouter modeli", "text"),
    "ai_system": (D_SYS, "🧠 AI Coach system prompt", "text"),
    "help_sys": (D_HELP_SYS, "🧠 Murojaat (yordamchi) prompt", "text"),
    "ai_characters": (D_CHARS, "🎭 AI personajlar (Nom|uslub)", "text"),
    "welcome": (D_WELCOME, "📝 Start matni", "text"),
    "earn_text": (D_EARN, "📝 Almaz ishlash matni", "text"),
    "promo_text": (D_PROMO, "📝 Promo matni", "text"),
    "phone_text": (D_PHONE, "📝 Sensitivity matni", "text"),
    "ai_text": (D_AI, "📝 Murojaat matni", "text"),
    "how_text": (D_HOW, "📝 Daraja matni", "text"),
    "guide_text": (D_GUIDE, "📝 Sherik qo'llanma", "text"),
    "shop_text": (D_SHOP, "📝 Do'kon matni", "text"),
    "service_text": (D_SERVICE, "📝 Xizmatlar matni", "text"),
    "sub_text": (D_SUB, "📝 Obuna matni", "text"),
    "banned_text": (D_BAN, "📝 Ban matni", "text"),
    "maint_text": (D_MAINT, "📝 Texnik ish matni", "text"),
    "nast_text": (D_NAST, "📝 Nastroyka matni", "text"),
    "nast_help": (D_NHELP, "📝 Nastroyka yordam matni", "text"),
}

NBRANDS = {
    "iPhone": ["iPhone 11", "iPhone 12", "iPhone 13", "iPhone 14", "iPhone 15", "iPhone 16", "iPhone 17"],
    "Samsung": ["Galaxy A15", "Galaxy A25", "Galaxy A35", "Galaxy A55", "Galaxy S23 Ultra",
                "Galaxy S24 Ultra", "Galaxy S25 Ultra", "Galaxy Z Fold 6"],
    "Xiaomi": ["Xiaomi 13", "Xiaomi 14", "Xiaomi 14 Pro", "Xiaomi 15", "Xiaomi 15 Ultra"],
    "Redmi": ["Redmi 12", "Redmi 13", "Redmi Note 12", "Redmi Note 13", "Redmi Note 14 Pro"],
    "POCO": ["POCO X5 Pro", "POCO X6", "POCO X7 Pro", "POCO F6", "POCO M6"],
    "Realme": ["Realme 12", "Realme 13", "Realme C67", "Realme GT 6"],
    "Infinix": ["Hot 30", "Hot 40", "Note 30", "Note 40", "GT 20 Pro"],
    "Honor": ["X8", "X9", "90", "200 Pro", "Magic 6 Pro"],
    "Tecno": ["Spark 20", "Spark 30", "Camon 30", "Pova 6"],
    "OPPO": ["A58", "A78", "Reno 11", "Reno 12", "Find X7 Ultra"],
    "Vivo": ["Y36", "Y38", "V30", "V40", "X100"],
}
NPKGS = [("BASE", "🟢", 1, 50), ("PREMIUM", "🟡", 2, 120), ("VIP", "🔴", 3, 250)]
LEAGUES = [("Bronze", "🥉", 0), ("Silver", "🥈", 50), ("Gold", "🥇", 150), ("Platinum", "💠", 400),
           ("Diamond", "💎", 800), ("Heroic", "🔥", 1500), ("Grandmaster", "👑", 3000)]
ITEMS = [
    ("direct", "💎 100 Diamond", "O'yin ichidagi 100 ta diamond FF ID ga yuboriladi.", 100),
    ("direct", "💎 310 Diamond", "O'yin ichidagi 310 ta diamond FF ID ga yuboriladi.", 300),
    ("pack", "🎁 Haftalik obuna", "Haftalik Airdrop obunasi.", 250),
    ("emote", "🕺 Emote: Raqs", "Mashhur emotsiya FF ID ga beriladi.", 150),
    ("skin", "🛡 Stenka: Olov", "Olovli stenka skini.", 120),
    ("service", "📢 Kanalingizni reklama qilish", "Bot foydalanuvchilariga kanal reklamasi.", 100),
    ("service", "🎬 Video montaj", "Free Fire videongiz uchun montaj.", 300),
    ("service", "🖼 Banner / Thumbnail dizayn", "YouTube kanal uchun banner va thumbnail.", 150),
]
PRIZES = [(0, 20), (1, 45), (2, 20), (3, 8), (5, 5), (10, 2)]
BOX_COST = 5
BOX_PRIZES = [(0, 50), (5, 35), (15, 12), (30, 3)]
ZAR_COST = 5
GUESS_COST = 2
GUESS_WIN = 8
FACTS = [
    "🍯 Qadimgi Misr qabrlaridan 3000 yillik asal topilgan, va u hali ham yeyishga yaroqli bo'lgan.",
    "🐙 Oktopusning uchta yuragi bor va qoni ko'k rangda.",
    "🍌 Botanika nuqtai nazaridan banan berry hisoblanadi, qulupnay esa emas.",
    "🪐 Venerada bir kun, bir yildan uzunroq davom etadi.",
    "🧠 Uyqu paytida miya kun davomida to'plangan xotiralarni saralaydi.",
    "🌍 Yer yuzida taxminan 3 trillion daraxt bor — bu Somon yo'lidagi yulduzlar sonidan ko'p.",
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

# ───────────────────────── DATABASE ─────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, name TEXT, phone TEXT,
 verified INTEGER DEFAULT 0, banned INTEGER DEFAULT 0, ref_by INTEGER, balance INTEGER DEFAULT 0,
 earned INTEGER DEFAULT 0, points INTEGER DEFAULT 0, refs INTEGER DEFAULT 0, ff_id TEXT,
 level INTEGER DEFAULT 0, mic TEXT DEFAULT 'Yoq', bio TEXT DEFAULT '', spin_date TEXT,
 free_used INTEGER DEFAULT 0, paid_used INTEGER DEFAULT 0, bonus_spins INTEGER DEFAULT 0,
 bonus_date TEXT, ai_date TEXT, ai_count INTEGER DEFAULT 0, spins_total INTEGER DEFAULT 0,
 joined INTEGER, theme TEXT DEFAULT 'olov');
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, title TEXT, url TEXT);
CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, amount INTEGER, max_uses INTEGER DEFAULT 0,
 used INTEGER DEFAULT 0, expires INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS promo_uses(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, code TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS prizes(id INTEGER PRIMARY KEY AUTOINCREMENT, amount INTEGER, weight REAL);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, url TEXT, chat_id TEXT);
CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, name TEXT, descr TEXT,
 price INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_id INTEGER,
 name TEXT, cat TEXT, price INTEGER, ff_id TEXT, note TEXT, status TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS withdrawals(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
 ff_id TEXT, status TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS leagues(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, emoji TEXT, min_points INTEGER);
CREATE TABLE IF NOT EXISTS partner_ads(user_id INTEGER PRIMARY KEY, mode TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS nbrands(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS nmodels(id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER, name TEXT,
 active INTEGER DEFAULT 1, UNIQUE(brand_id, name));
CREATE TABLE IF NOT EXISTS npackages(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, emoji TEXT,
 refs INTEGER DEFAULT 0, price INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS ncodes(code TEXT PRIMARY KEY, user_id INTEGER, phone TEXT, pkg TEXT, ts INTEGER);
"""
MIGR = ["ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'olov'"]
PGSCHEMA = (SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
            .replace("INTEGER", "BIGINT").replace("REAL", "DOUBLE PRECISION"))
IDTABLES = {"orders", "withdrawals", "prizes", "tasks", "items", "leagues", "channels", "promo_uses",
            "nbrands", "nmodels", "npackages"}
db = None


class Row:
    def __init__(self, keys, vals):
        self._v = list(vals)
        self._m = dict(zip(keys, self._v))

    def __getitem__(self, i):
        return self._v[i] if isinstance(i, int) else self._m[i]


class Cur:
    def __init__(self, out=None, lastrowid=None):
        self._r = out or []
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._r[0] if self._r else None

    def fetchall(self):
        return self._r


class PGDB:
    """sqlite3 ga o'xshash Postgres qobig'i (Neon)."""

    def __init__(self, url):
        self.url = url
        self.conn = None
        self._open()

    def _open(self):
        self.conn = psycopg2.connect(self.url, connect_timeout=20)
        self.conn.autocommit = True

    def execute(self, sql, args=()):
        sql = sql.replace("?", "%s")
        m = re.match(r"\s*INSERT INTO (\w+)", sql, re.I)
        ret = bool(m and m.group(1).lower() in IDTABLES and "returning" not in sql.lower())
        if ret:
            sql += " RETURNING id"
        for attempt in (0, 1):
            try:
                cur = self.conn.cursor()
                cur.execute(sql, tuple(args))
                break
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                if attempt:
                    raise
                try:
                    self.conn.close()
                except Exception:
                    pass
                self._open()
        out = []
        if cur.description:
            keys = [d[0] for d in cur.description]
            out = [Row(keys, r) for r in cur.fetchall()]
        cur.close()
        lid = None
        if ret and out:
            lid, out = out[0]["id"], []
        return Cur(out, lid)

    def commit(self):
        pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


def connect():
    global db
    if IS_PG:
        if db is None:
            db = PGDB(DATABASE_URL)
        for stmt in PGSCHEMA.split(";"):
            if stmt.strip():
                db.execute(stmt)
    else:
        db = sqlite3.connect(DB_PATH, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
    for m in MIGR:
        try:
            db.execute(m)
        except Exception:
            pass
    if not db.execute("SELECT 1 FROM settings WHERE k='_seeded'").fetchone():
        for r in PRIZES:
            db.execute("INSERT INTO prizes(amount,weight) VALUES(?,?)", r)
        for r in LEAGUES:
            db.execute("INSERT INTO leagues(name,emoji,min_points) VALUES(?,?,?)", r)
        for r in ITEMS:
            db.execute("INSERT INTO items(cat,name,descr,price) VALUES(?,?,?,?)", r)
        db.execute("INSERT INTO settings(k,v) VALUES('_seeded','1')")
    if not db.execute("SELECT 1 FROM settings WHERE k='_nseeded'").fetchone():
        for brand, models in NBRANDS.items():
            db.execute("INSERT INTO nbrands(name) VALUES(?) ON CONFLICT DO NOTHING", (brand,))
            bid = db.execute("SELECT id FROM nbrands WHERE name=?", (brand,)).fetchone()[0]
            for mname in models:
                db.execute("INSERT INTO nmodels(brand_id,name) VALUES(?,?) ON CONFLICT DO NOTHING", (bid, mname))
        for p in NPKGS:
            db.execute("INSERT INTO npackages(name,emoji,refs,price) VALUES(?,?,?,?)", p)
        db.execute("INSERT INTO settings(k,v) VALUES('_nseeded','1')")
    db.commit()


def ex(sql, a=()):
    c = db.execute(sql, a)
    db.commit()
    return c


def one(sql, a=()):
    return db.execute(sql, a).fetchone()


def rows(sql, a=()):
    return db.execute(sql, a).fetchall()


def st(k):
    r = one("SELECT v FROM settings WHERE k=?", (k,))
    return r["v"] if r else S[k][0]


def sti(k):
    try:
        return int(float(st(k)))
    except Exception:
        return int(float(S[k][0]))


def stb(k):
    return st(k) == "1"


def set_st(k, v):
    ex("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))


# ───────────────────────── YORDAMCHILAR ─────────────────────────
def now():
    return datetime.now(TZ)


def today():
    return now().strftime("%Y-%m-%d")


def ts():
    return int(time.time())


def esc(s):
    return html.escape(str(s if s is not None else ""))


def fmt_sec(sec):
    h, rem = divmod(max(0, int(sec)), 3600)
    m = rem // 60
    return f"{h} soat {m} daqiqa" if h else f"{m} daqiqa"


def admin_ids():
    return set(ENV_ADMINS) | {r["id"] for r in rows("SELECT id FROM admins")}


def is_admin(uid):
    return uid in ENV_ADMINS or bool(one("SELECT 1 FROM admins WHERE id=?", (uid,)))


def get_user(uid):
    return one("SELECT * FROM users WHERE id=?", (uid,))


def upd(uid, **kw):
    ex("UPDATE users SET " + ",".join(f"{k}=?" for k in kw) + " WHERE id=?", (*kw.values(), uid))


def credit(uid, n):
    ex("UPDATE users SET balance=balance+?, earned=earned+? WHERE id=?", (n, max(n, 0), uid))


def tag(r):
    return "@" + esc(r["username"]) if r["username"] else f"ID:{r['id']}"


def mention(r):
    return f'<a href="tg://user?id={r["id"]}">{esc(r["name"] or r["id"])}</a>'


def theme_emoji(r):
    return THEMES[r["theme"] or "olov"][0]


def ensure_user(u, ref=None):
    r = get_user(u.id)
    name = (u.full_name or "")[:60]
    if r is None:
        rb = ref if ref and ref != u.id and get_user(ref) else None
        ex("INSERT INTO users(id,username,name,ref_by,joined,theme) VALUES(?,?,?,?,?,'olov')",
           (u.id, u.username, name, rb, ts()))
    elif r["username"] != u.username or r["name"] != name:
        ex("UPDATE users SET username=?,name=? WHERE id=?", (u.username, name, u.id))
    return get_user(u.id)


async def say(update, text, kb=None, plain=False, preview=False):
    m = update.effective_message
    parts = [text[i:i + 4000] for i in range(0, len(text), 4000)] or ["."]
    for i, p in enumerate(parts):
        k = kb if i == len(parts) - 1 else None
        try:
            await m.reply_text(p, parse_mode=None if plain else HTML, reply_markup=k,
                               disable_web_page_preview=not preview)
        except Exception as e:
            if "parse" in str(e).lower():
                await m.reply_text(p, reply_markup=k, disable_web_page_preview=True)
            else:
                raise


async def aedit(update, text, kb=None):
    q = update.callback_query
    try:
        await q.message.edit_text(text, parse_mode=HTML, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        if "not modified" not in str(e).lower():
            await q.message.reply_text(text, parse_mode=HTML, reply_markup=kb, disable_web_page_preview=True)


def setst(ctx, name, **kw):
    ctx.user_data["st"] = {"n": name, **kw}


def getst(ctx):
    return ctx.user_data.get("st")


def clrst(ctx):
    ctx.user_data.pop("st", None)


async def notify_admins(ctx, text, kb=None):
    for i in admin_ids():
        try:
            await ctx.bot.send_message(i, text, parse_mode=HTML, reply_markup=kb)
        except Exception:
            pass


BOT = {"username": ""}


def share_link(uid):
    return f"https://t.me/{BOT['username']}?start=ref_{uid}"


def tb(label):
    """Inline tugma: bosilganda matn xabari kabi ishlaydi (t:<matn>)."""
    return IB(label, callback_data="t:" + label)


# Pastki tugmalar ranglari: qizil, yashil, ko'k navbatma-navbat (har bir tugma boshqa rangda)
RK_COLORS = ["danger", "success", "primary"]


def rk(*rws):
    """Pastki (reply) klaviatura. Har bir tugma boshqa rangda chiqadi."""
    out, i = [], 0
    for row in rws:
        r = []
        for text in row:
            r.append(KeyboardButton(text, api_kwargs={"style": RK_COLORS[i % len(RK_COLORS)]}))
            i += 1
        out.append(r)
    return ReplyKeyboardMarkup(out, resize_keyboard=True)


def back(cb="a:home"):
    return [IB("⬅️ Orqaga", callback_data=cb)]


# ───────────────────────── BOSH MENYU (3 TA TUGMA) ─────────────────────────
B_BACK = "⬅️ Orqaga"
B_NAST = "⚙️ Tekin nastroyka"
B_ALMAZ = "💎 Tekin almaz"
B_AI = "🤖 Murojaat"
B_ADMIN = "👑 Admin panel"

B_EARN = "💎 Almaz ishlash"
B_PROMO = "🎁 Promo kod"
B_SPIN = "🎰 Spin"
B_BOXMENU = "🎲 Quti o'yini"
B_ZAR = "🎲 Zar o'yini"
B_GUESS = "🔢 Son tanlash"
B_PARTNER = "🤝 Sherik Topish"
B_TOP = "🏆 Reyting"
B_PROF = "📊 Profilim"
B_LVL = "🥇 Mening darajam"
B_SHOP = "🛒 O'yin Do'koni"
B_YT = "🎥 Youtuber Xizmatlari"
B_HORROR = "👻 Qorong'u dunyo"

L_SPIN, L_MYSPIN, L_BONUS = "🎰 Spin qilish", "📊 Mening spinlarim", "🎁 Bonus spin olish"
L_PHIST = "📜 Mening promo tarixim"
L_FIND, L_AD, L_PASS, L_GUIDE = "🔍 Sherik Qidirish", "📢 E'lon Berish", "👤 Mening Pasportim", "ℹ️ Qo'llanma"
L_HELP = "❓ Bot qanday ishlaydi"
L_AICHAT, L_AICHAR, L_AINICK = "🤖 AI Suhbat", "🎭 Personaj Ovozida AI", "✨ Nickname Yaratish"
L_AISENS = "🎯 AI Sensitivity"
L_SVC, L_MYORD = "📺 Xizmatlar ro'yxati", "📰 Mening Buyurtmalarim"
L_FACT, L_STORY, L_CURSE = "🤯 Dahshat fakt", "👻 Qo'rqinchli hikoya", "🔮 Qarg'ish"
CATS = {"direct": "💎 To'g'ridan-to'g'ri yechish", "pack": "🎁 Naborlar", "emote": "🕺 Emotsiyalar",
        "skin": "🛡 Stenkalar & Skinlar", "service": "🎥 Youtuber xizmatlari"}
MODES = ["BR-Ranked", "CS-Ranked", "Ultimatum"]


def main_kb(uid=0):
    rws = [[B_NAST], [B_ALMAZ], [B_AI]]
    if is_admin(uid):
        rws.append([B_ADMIN])
    return rk(*rws)


def almaz_kb():
    return rk([B_EARN, B_PROMO], [B_SPIN, B_BOXMENU], [B_ZAR, B_GUESS], [B_PARTNER, B_TOP],
              [B_PROF, B_LVL], [B_SHOP, B_YT], [B_HORROR], [B_BACK])


async def home(update, ctx):
    clrst(ctx)
    await say(update, st("welcome"), main_kb(update.effective_user.id))


# ───────────────────────── CAPTCHA / TELEFON / OBUNA ─────────────────────────
SUBC = {}


async def missing_subs(ctx, uid):
    chs = rows("SELECT * FROM channels")
    if not chs or SUBC.get(uid, 0) > time.time():
        return []
    miss = []
    for c in chs:
        try:
            m = await ctx.bot.get_chat_member(c["chat_id"], uid)
            if m.status in ("left", "kicked"):
                miss.append(c)
        except Exception as e:
            log.warning("sub check %s: %s", c["chat_id"], e)
    if not miss:
        SUBC[uid] = time.time() + 120
    return miss


async def verify_step(update, ctx, r):
    if stb("captcha_on") and not ctx.user_data.get("cap_ok"):
        a, b = random.randint(2, 9), random.randint(2, 9)
        opts = {a + b}
        while len(opts) < 4:
            opts.add(random.randint(4, 18))
        opts = random.sample(sorted(opts), 4)
        ctx.user_data["cap"] = a + b
        await say(update, f"🤖 <b>Captcha</b>\n\nRobot emasligingizni tasdiqlang:\n<b>{a} + {b} = ?</b>",
                  IM([[IB(str(o), callback_data=f"cap:{o}") for o in opts]]))
        return
    if stb("phone_on") and not r["phone"]:
        kb = ReplyKeyboardMarkup([[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]],
                                 resize_keyboard=True, one_time_keyboard=True)
        await say(update, "📱 <b>Telefon raqamingizni tasdiqlang</b>\n\nPastdagi tugmani bosing 👇", kb)
        return
    await finish_verify(update, ctx)


async def gate(update, ctx):
    u = update.effective_user
    r = ensure_user(u)
    if is_admin(u.id):
        return True
    if r["banned"]:
        await say(update, st("banned_text"))
        return False
    if not stb("bot_enabled"):
        await say(update, st("maint_text"))
        return False
    if not r["verified"]:
        await verify_step(update, ctx, r)
        return False
    miss = await missing_subs(ctx, u.id)
    if miss:
        kb = [[IB(f"📣 {c['title']}", url=c["url"])] for c in miss if c["url"]]
        kb.append([IB("✅ Tekshirish", callback_data="sub:check")])
        await say(update, st("sub_text"), IM(kb))
        return False
    return True


async def finish_verify(update, ctx):
    u = update.effective_user
    r = get_user(u.id)
    if not r["verified"]:
        upd(u.id, verified=1)
        if sti("start_bonus"):
            credit(u.id, sti("start_bonus"))
        ref = r["ref_by"]
        rr = get_user(ref) if ref else None
        if rr and not rr["banned"]:
            credit(ref, sti("ref_reward"))
            ex("UPDATE users SET points=points+?, refs=refs+1 WHERE id=?", (sti("ref_points"), ref))
            try:
                await ctx.bot.send_message(
                    ref, f"🎉 Do'stingiz <b>{esc(u.full_name)}</b> tasdiqlandi!\n"
                         f"💎 +{sti('ref_reward')} Almaz hisobingizga qo'shildi.", parse_mode=HTML)
            except Exception:
                pass
    if await gate(update, ctx):
        await say(update, st("welcome"), main_kb(u.id))


async def start(update, ctx):
    ref = None
    if ctx.args and ctx.args[0].startswith("ref_"):
        try:
            ref = int(ctx.args[0][4:])
        except ValueError:
            pass
    ensure_user(update.effective_user, ref)
    clrst(ctx)
    if await gate(update, ctx):
        await say(update, st("welcome"), main_kb(update.effective_user.id))


async def on_contact(update, ctx):
    u, c = update.effective_user, update.message.contact
    ensure_user(u)
    if c.user_id != u.id:
        return await say(update, "❌ Faqat o'zingizning raqamingizni yuboring.")
    phone = re.sub(r"\D", "", c.phone_number or "")
    pre = re.sub(r"\D", "", st("phone_prefix"))
    if pre and not phone.startswith(pre):
        return await say(update, f"❌ Faqat +{pre} raqamlari qabul qilinadi.")
    if one("SELECT 1 FROM users WHERE phone=? AND id!=?", (phone, u.id)):
        return await say(update, "❌ Bu raqam boshqa akkauntga bog'langan.")
    upd(u.id, phone=phone)
    await finish_verify(update, ctx)


async def cb_cap(update, ctx, a):
    q = update.callback_query
    if str(ctx.user_data.get("cap")) == a[1]:
        ctx.user_data["cap_ok"] = True
        await q.answer("✅ To'g'ri!")
    else:
        await q.answer("❌ Noto'g'ri, qayta urinib ko'ring", show_alert=True)
    try:
        await q.message.delete()
    except Exception:
        pass
    await verify_step(update, ctx, get_user(q.from_user.id))


async def cb_sub(update, ctx, a):
    q = update.callback_query
    SUBC.pop(q.from_user.id, None)
    if await missing_subs(ctx, q.from_user.id):
        return await q.answer("❌ Hali hamma kanalga a'zo bo'lmadingiz", show_alert=True)
    await q.answer("✅ Rahmat!")
    try:
        await q.message.delete()
    except Exception:
        pass
    await say(update, st("welcome"), main_kb(q.from_user.id))


# ───────────────────────── 🤖 MUROJAAT (AI) ─────────────────────────
async def ask_ai(messages, max_tokens=900):
    async with httpx.AsyncClient(timeout=60) as c:
        for url, key, model in (
            ("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY, st("ai_model_groq")),
            ("https://openrouter.ai/api/v1/chat/completions", OR_KEY, st("ai_model_or")),
        ):
            if not key:
                continue
            try:
                r = await c.post(url, headers={"Authorization": f"Bearer {key}"},
                                 json={"model": model, "messages": messages,
                                       "max_tokens": max_tokens, "temperature": 0.7})
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"].strip()
                log.warning("AI %s -> %s %s", model, r.status_code, r.text[:200])
            except Exception as e:
                log.warning("AI error: %s", e)
    return None


async def ai_quota(update):
    uid = update.effective_user.id
    if is_admin(uid):
        return True
    r = get_user(uid)
    if r["ai_date"] != today():
        ex("UPDATE users SET ai_date=?, ai_count=0 WHERE id=?", (today(), uid))
        r = get_user(uid)
    if r["ai_count"] >= sti("ai_limit"):
        await say(update, f"⛔ Bugungi AI limitingiz tugadi ({sti('ai_limit')} ta). Ertaga qaytib keling!")
        return False
    ex("UPDATE users SET ai_count=ai_count+1 WHERE id=?", (uid,))
    return True


async def ai_run(update, system, history, text, max_tokens=900):
    await update.effective_chat.send_action("typing")
    msgs = [{"role": "system", "content": system}] + history[-8:] + [{"role": "user", "content": text}]
    ans = await ask_ai(msgs, max_tokens)
    if not ans:
        await say(update, "⚠️ AI hozircha javob bera olmadi. Birozdan so'ng urinib ko'ring.")
        return None
    await say(update, ans, plain=True)
    return ans


async def ai_menu(update, ctx):
    clrst(ctx)
    await say(update, st("ai_text"),
              rk([L_HELP], [L_AICHAT], [L_AICHAR], [L_AINICK], [L_AISENS], [B_BACK]))


async def help_start(update, ctx):
    setst(ctx, "ai_help", h=[])
    await say(update, "❓ <b>Bot qanday ishlaydi?</b>\n\nSavolingizni yozing, AI javob beradi 👇", rk([B_BACK]))


async def st_ai_help(update, ctx, s, t):
    if not await ai_quota(update):
        return
    ans = await ai_run(update, st("help_sys"), s["h"], t, 500)
    if ans:
        s["h"] += [{"role": "user", "content": t}, {"role": "assistant", "content": ans}]
        s["h"][:] = s["h"][-10:]


async def ai_chat_start(update, ctx):
    setst(ctx, "ai_chat", h=[])
    await say(update, "🤖 <b>Pro Coach</b> tayyor! Free Fire bo'yicha savolingizni yozing 👇", rk([B_BACK]))


async def st_ai_chat(update, ctx, s, t):
    if not await ai_quota(update):
        return
    ans = await ai_run(update, st("ai_system"), s["h"], t)
    if ans:
        s["h"] += [{"role": "user", "content": t}, {"role": "assistant", "content": ans}]
        s["h"][:] = s["h"][-12:]


def chars():
    return [l.split("|", 1) for l in st("ai_characters").splitlines() if "|" in l]


async def ai_char_start(update, ctx):
    cs = chars()
    if not cs:
        return await say(update, "Hozircha personajlar yo'q.")
    names = [c[0].strip() for c in cs]
    setst(ctx, "ai_charpick")
    kb = [names[i:i + 2] for i in range(0, len(names), 2)] + [[B_BACK]]
    await say(update, "🎭 <b>Qaysi personaj ovozida gaplashamiz?</b>", rk(*kb))


async def st_ai_charpick(update, ctx, s, t):
    for n, style in chars():
        if n.strip() == t:
            sysmsg = (f"Sen Free Fire qahramoni {n.strip()} sifatida gapirasan. Uslubing: {style.strip()}. "
                      "O'zbek tilida (lotin) qisqa va qiziqarli javob ber, personajdan chiqma.")
            setst(ctx, "ai_char", sys=sysmsg, h=[], name=n.strip())
            return await say(update, f"🎭 <b>{esc(n.strip())}</b> ovozida gaplashing! Xabar yozing 👇", rk([B_BACK]))
    await say(update, "Personajni tugmalardan tanlang 👇")


async def st_ai_char(update, ctx, s, t):
    if not await ai_quota(update):
        return
    ans = await ai_run(update, s["sys"], s["h"], t, 500)
    if ans:
        s["h"] += [{"role": "user", "content": t}, {"role": "assistant", "content": ans}]
        s["h"][:] = s["h"][-10:]


async def ai_nick_start(update, ctx):
    setst(ctx, "ai_nick")
    await say(update, "✨ <b>Nickname yaratish</b>\n\nIsmingiz yoki uslubni yozing (masalan: <code>Akmal olov</code>):",
              rk([B_BACK]))


async def st_ai_nick(update, ctx, s, t):
    if not await ai_quota(update):
        return
    await ai_run(update, "Sen Free Fire uchun stilli nickname yaratuvchisan. Foydalanuvchi so'ziga qarab 10 ta "
                         "noyob, chiroyli nik taklif qil (maxsus belgilar bilan). Faqat ro'yxat ber, har biri alohida qatorda.",
                 [], t, 400)


async def phone_menu(update, ctx):
    setst(ctx, "phone")
    await say(update, st("phone_text"), rk([B_BACK]))


async def st_phone(update, ctx, s, t):
    if not await ai_quota(update):
        return
    sysmsg = ("Sen Free Fire sensitivity mutaxassisisan. O'zbek tilida (lotin) javob ber. Berilgan telefon modeli uchun "
              "General, Red Dot, 2X Scope, 4X Scope, AWM Scope (0-100 raqamlarda), DPI tavsiyasi, "
              "otish tugmasi o'lchami (%) va lagni kamaytirish maslahatlarini ber. Oxirida: 'Bu taxminiy sozlama, "
              "o'zingizga moslab sozlang' deb qo'sh.")
    await ai_run(update, sysmsg, [], f"Telefon modeli: {t}", 1000)


# ───────────────────────── ⚙️ TEKIN NASTROYKA ─────────────────────────
def nast_kb():
    bs = rows("SELECT id,name FROM nbrands WHERE active=1 ORDER BY id")
    btn = [IB(f"📱 {b['name']}", callback_data=f"nb:{b['id']}") for b in bs]
    k = [btn[i:i + 2] for i in range(0, len(btn), 2)]
    k += [[IB("🎁 Referral", callback_data="nref"), IB("🆘 Yordam", callback_data="nhelp")],
          [IB("⚙️ Maxsus", callback_data="ncust")],
          [tb(B_BACK)]]
    return IM(k)


async def nast_menu(update, ctx):
    clrst(ctx)
    await say(update, st("nast_text"), nast_kb())


async def cb_nst(update, ctx, a):
    await aedit(update, st("nast_text"), nast_kb())


async def cb_nb(update, ctx, a):
    q = update.callback_query
    bid = int(a[1])
    b = one("SELECT name FROM nbrands WHERE id=? AND active=1", (bid,))
    if not b:
        return await q.answer("Brend topilmadi", show_alert=True)
    ms = rows("SELECT id,name FROM nmodels WHERE brand_id=? AND active=1 ORDER BY id", (bid,))
    k = [[IB(f"📱 {m['name']}", callback_data=f"nm:{m['id']}") for m in ms[i:i + 2]]
         for i in range(0, len(ms), 2)]
    k.append([IB("⬅️ Brendlar", callback_data="nst")])
    text = f"📱 <b>{esc(b['name'])}</b>\n\nModelingizni tanlang 👇"
    if not ms:
        text += "\n\n<i>Hozircha model yo'q.</i>"
    await aedit(update, text, IM(k))


async def cb_nm(update, ctx, a):
    uid = update.callback_query.from_user.id
    mid = int(a[1])
    m = one("SELECT m.id, m.name, m.brand_id, b.name AS bn FROM nmodels m JOIN nbrands b ON b.id=m.brand_id "
            "WHERE m.id=? AND m.active=1 AND b.active=1", (mid,))
    if not m:
        return await update.callback_query.answer("Model topilmadi", show_alert=True)
    r = get_user(uid)
    ref_on = st("nast_ref") == "1"
    pk = rows("SELECT id,name,emoji,refs,price FROM npackages WHERE active=1 ORDER BY id")
    lines = []
    for p in pk:
        refs_txt = f"{p['refs']} referral yoki " if ref_on and p["refs"] > 0 else ""
        lines.append(f"{p['emoji']} <b>{esc(p['name'])}</b> — {refs_txt}{p['price']} 💎")
    text = (f"📱 <b>{esc(m['bn'])} {esc(m['name'])}</b>\n\nSozlama paketini tanlang:\n\n" + "\n".join(lines) +
            f"\n\n👥 Referral: <b>{r['refs']}</b> | 💎 Balans: <b>{r['balance']}</b>")
    k = [[IB(f"{p['emoji']} {p['name']}", callback_data=f"np:{mid}:{p['id']}")] for p in pk]
    k.append([IB("⬅️ Orqaga", callback_data=f"nb:{m['brand_id']}")])
    await aedit(update, text, IM(k))


async def cb_np(update, ctx, a):
    q = update.callback_query
    uid = q.from_user.id
    mid, pid = int(a[1]), int(a[2])
    m = one("SELECT m.name, b.name AS bn FROM nmodels m JOIN nbrands b ON b.id=m.brand_id WHERE m.id=?", (mid,))
    p = one("SELECT * FROM npackages WHERE id=? AND active=1", (pid,))
    if not m or not p:
        return await q.answer("Ma'lumot topilmadi", show_alert=True)
    r = get_user(uid)
    ref_on = st("nast_ref") == "1"
    if ref_on and p["refs"] > 0 and r["refs"] >= p["refs"]:
        ex("UPDATE users SET refs=refs-? WHERE id=?", (p["refs"], uid))
        how = f"{p['refs']} referral"
    elif r["balance"] >= p["price"]:
        ex("UPDATE users SET balance=balance-? WHERE id=?", (p["price"], uid))
        how = f"{p['price']} 💎 almaz"
    else:
        need_a = max(0, p["price"] - r["balance"])
        lines = [f"🔐 <b>Yetarli emas</b>\n\n📱 {esc(m['bn'])} {esc(m['name'])}\n{p['emoji']} {esc(p['name'])} paketi\n"]
        if ref_on and p["refs"] > 0:
            lines.append(f"👥 Yana <b>{max(0, p['refs'] - r['refs'])}</b> ta referral kerak yoki")
        lines.append(f"💎 Yana <b>{need_a}</b> almaz kerak")
        kb = IM([[IB("🎁 Referral", callback_data="nref")], [IB("⬅️ Orqaga", callback_data=f"nm:{mid}")]])
        await aedit(update, "\n".join(lines), kb)
        return await q.answer()
    code = "NST-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    ex("INSERT INTO ncodes(code,user_id,phone,pkg,ts) VALUES(?,?,?,?,?)",
       (code, uid, f"{m['bn']} {m['name']}", p["name"], ts()))
    await notify_admins(ctx, f"🔐 <b>Yangi nastroyka kodi</b>\n👤 {mention(r)} ({tag(r)})\n"
                              f"📱 {esc(m['bn'])} {esc(m['name'])}\n📦 {esc(p['name'])} — {how}\n🔑 <code>{code}</code>")
    text = ("🎉 <b>So'rov tasdiqlandi!</b>\n\n"
            f"📱 {esc(m['bn'])} {esc(m['name'])}\n{p['emoji']} {esc(p['name'])} paketi\n💸 Sarflandi: {how}\n\n"
            f"🔐 <b>Maxfiy kod:</b>\n<code>{code}</code>\n\n"
            f"⚠️ Kod bir martalik. Supportga yuboring: <b>{esc(st('support'))}</b>")
    await aedit(update, text, IM([[IB("⬅️ Brendlar", callback_data="nst")]]))
    return await q.answer("✅ Kod yaratildi")


async def cb_nref(update, ctx, a):
    uid = update.callback_query.from_user.id
    r = get_user(uid)
    link = share_link(uid)
    text = ("🎁 <b>Referral markazi</b>\n\n"
            f"👥 Sizning referral: <b>{r['refs']}</b>\n\n🔗 <b>Shaxsiy havolangiz:</b>\n<code>{link}</code>\n\n"
            "⚡ Referral faqat yangi foydalanuvchi majburiy obunani bajargandan keyin hisoblanadi.")
    kb = IM([[IB("📤 Ulashish", url=f"https://t.me/share/url?url={link}&text=KAROCHI%20bot")],
             [IB("⬅️ Brendlar", callback_data="nst")]])
    await aedit(update, text, kb)


async def cb_nhelp(update, ctx, a):
    await aedit(update, st("nast_help"), IM([[IB("⬅️ Brendlar", callback_data="nst")]]))


async def cb_ncust(update, ctx, a):
    await aedit(update, "⚙️ <b>Maxsus sozlama</b>\n\nTelefon yoki model ro'yxatda bo'lmasa, supportga yozing.\n"
                        f"📩 Support: <b>{esc(st('support'))}</b>", IM([[IB("⬅️ Brendlar", callback_data="nst")]]))


async def cb_nai(update, ctx, a):
    await phone_menu(update, ctx)


# Admin: tekin nastroyka boshqaruvi
async def cb_na(update, ctx, a):
    q = update.callback_query
    s = a[1] if len(a) > 1 else "l"
    await q.answer()
    if s == "l":
        bs = rows("SELECT id,name,active FROM nbrands ORDER BY id")
        k = [[IB(f"{'🟢' if b['active'] else '🔴'} {b['name']}", callback_data=f"na:bm:{b['id']}"),
              IB("🔁", callback_data=f"na:bt:{b['id']}")] for b in bs]
        k += [[IB("➕ Brend", callback_data="na:ab"), IB("➕ Model", callback_data="na:am")],
              [IB("📦 Paketlar", callback_data="na:p"), IB("🔐 Kodlar", callback_data="na:codes")],
              back("a:home")]
        return await aedit(update, "📱 <b>Tekin nastroyka boshqaruvi</b>\n\nBrendni bosib modellarini boshqaring.", IM(k))
    if s == "bt":
        ex("UPDATE nbrands SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (int(a[2]),))
        return await cb_na(update, ctx, ["na", "l"])
    if s == "bm":
        bid = int(a[2])
        b = one("SELECT name FROM nbrands WHERE id=?", (bid,))
        if not b:
            return
        ms = rows("SELECT id,name,active FROM nmodels WHERE brand_id=? ORDER BY id", (bid,))
        k = [[IB(f"{'🟢' if m['active'] else '🔴'} {m['name']}", callback_data=f"na:mt:{m['id']}:{bid}")] for m in ms]
        k.append([IB("⬅️ Brendlar", callback_data="na:l")])
        return await aedit(update, f"📱 <b>{esc(b['name'])}</b> — modellar", IM(k))
    if s == "mt":
        mid, bid = int(a[2]), int(a[3])
        ex("UPDATE nmodels SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (mid,))
        return await cb_na(update, ctx, ["na", "bm", str(bid)])
    if s == "ab":
        setst(ctx, "adm_nbrand")
        return await aedit(update, "➕ Yangi brend nomini yuboring:", IM([back("na:l")]))
    if s == "am":
        setst(ctx, "adm_nmodel")
        return await aedit(update, "➕ Format: <code>Brend | Model</code>", IM([back("na:l")]))
    if s == "p":
        ps = rows("SELECT * FROM npackages ORDER BY id")
        k = [[IB(f"{'🟢' if p['active'] else '🔴'} {p['emoji']} {p['name']} • {p['refs']}ref • {p['price']}💎",
                 callback_data=f"na:pe:{p['id']}")] for p in ps]
        k += [[IB("➕ Paket", callback_data="na:ap")], back("na:l")]
        return await aedit(update, "📦 <b>Paketlar</b>\n\nPaketni bosib tahrirlang.", IM(k))
    if s == "pe":
        p = one("SELECT * FROM npackages WHERE id=?", (int(a[2]),))
        if not p:
            return
        text = (f"{p['emoji']} <b>{esc(p['name'])}</b>\n\n👥 Referral: {p['refs']}\n💎 Narx: {p['price']}\n"
                f"🟢 Holat: {'yoqilgan' if p['active'] else 'o‘chirilgan'}")
        k = [[IB("✏️ Referral/narx", callback_data=f"na:pedit:{p['id']}")],
             [IB("🔁 Yoqish/o'chirish", callback_data=f"na:pt:{p['id']}")], back("na:p")]
        return await aedit(update, text, IM(k))
    if s == "pedit":
        setst(ctx, "adm_npedit", id=int(a[2]))
        return await aedit(update, "✏️ Yangi qiymatlar: <code>REFERRAL NARX</code>\nMasalan: <code>2 120</code>",
                           IM([back(f"na:pe:{a[2]}")]))
    if s == "pt":
        ex("UPDATE npackages SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (int(a[2]),))
        return await cb_na(update, ctx, ["na", "pe", a[2]])
    if s == "ap":
        setst(ctx, "adm_npadd")
        return await aedit(update, "➕ Format: <code>Nom | emoji | referral | narx</code>", IM([back("na:p")]))
    if s == "codes":
        cs = rows("SELECT code,phone,pkg,user_id FROM ncodes ORDER BY ts DESC LIMIT 20")
        lines = [f"<code>{esc(c['code'])}</code> • {esc(c['phone'])} • {esc(c['pkg'])} • 👤 {c['user_id']}" for c in cs]
        return await aedit(update, "🔐 <b>Nastroyka kodlari</b>\n\n" + ("\n".join(lines) or "Hozircha yo'q"),
                           IM([back("na:l")]))


async def st_adm_nbrand(update, ctx, s, t):
    name = t.strip()
    if len(name) < 2 or len(name) > 40:
        return await say(update, "❌ Brend nomini to'g'ri yuboring.")
    ex("INSERT INTO nbrands(name) VALUES(?) ON CONFLICT DO NOTHING", (name,))
    clrst(ctx)
    await say(update, f"✅ <b>{esc(name)}</b> qo'shildi.", IM([[IB("📱 Nastroyka", callback_data="na:l")]]))


async def st_adm_nmodel(update, ctx, s, t):
    parts = [x.strip() for x in t.split("|")]
    if len(parts) != 2 or not parts[1]:
        return await say(update, "❌ Format: Brend | Model")
    b = one("SELECT id FROM nbrands WHERE LOWER(name)=LOWER(?)", (parts[0],))
    if not b:
        return await say(update, "❌ Brend topilmadi. Avval brend qo'shing.")
    ex("INSERT INTO nmodels(brand_id,name) VALUES(?,?) ON CONFLICT DO NOTHING", (b["id"], parts[1]))
    clrst(ctx)
    await say(update, f"✅ <b>{esc(parts[1])}</b> qo'shildi.", IM([[IB("📱 Nastroyka", callback_data="na:l")]]))


async def st_adm_npadd(update, ctx, s, t):
    parts = [x.strip() for x in t.split("|")]
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        return await say(update, "❌ Format: Nom | emoji | referral | narx")
    ex("INSERT INTO npackages(name,emoji,refs,price) VALUES(?,?,?,?)",
       (parts[0], parts[1], int(parts[2]), int(parts[3])))
    clrst(ctx)
    await say(update, "✅ Paket qo'shildi.", IM([[IB("📦 Paketlar", callback_data="na:p")]]))


async def st_adm_npedit(update, ctx, s, t):
    m = re.fullmatch(r"(\d+)\s+(\d+)", t.strip())
    if not m:
        return await say(update, "❌ Format: REFERRAL NARX (masalan: 2 120)")
    ex("UPDATE npackages SET refs=?, price=? WHERE id=?", (int(m.group(1)), int(m.group(2)), s["id"]))
    clrst(ctx)
    await say(update, "✅ Paket saqlandi.", IM([[IB("📦 Paketlar", callback_data="na:p")]]))


# ───────────────────────── 💎 TEKIN ALMAZ ─────────────────────────
async def almaz_menu(update, ctx):
    clrst(ctx)
    r = get_user(update.effective_user.id)
    await say(update, f"💎 <b>Tekin almaz</b>\n\n💰 Balans: <b>{r['balance']}</b> 💎\n"
                      f"👥 Takliflar: {r['refs']}\n\nBo'limni tanlang 👇", almaz_kb())


async def earn(update, ctx):
    clrst(ctx)
    uid = update.effective_user.id
    link = share_link(uid)
    text = st("earn_text").replace("{reward}", str(sti("ref_reward"))).replace("{link}", link)
    share = f"https://t.me/share/url?url={link}&text=KAROCHI%20bepul%20almaz%20%F0%9F%92%8E"
    await say(update, text, IM([[IB("📤 Do'stlarga ulashish", url=share)]]), preview=True)


async def promo_menu(update, ctx):
    setst(ctx, "promo")
    await say(update, st("promo_text"), rk([L_PHIST], [B_BACK]))


async def promo_hist(update, ctx):
    rs = rows("SELECT u.code,u.ts,p.amount FROM promo_uses u LEFT JOIN promos p ON p.code=u.code "
              "WHERE u.user_id=? ORDER BY u.id DESC LIMIT 15", (update.effective_user.id,))
    if not rs:
        return await say(update, "📜 Siz hali promo kod ishlatmagansiz.")
    ln = [f"• <code>{esc(r['code'])}</code> — 💎 {r['amount'] or '?'} — "
          f"{datetime.fromtimestamp(r['ts'], TZ):%d.%m.%Y}" for r in rs]
    await say(update, "📜 <b>Promo tarixim:</b>\n\n" + "\n".join(ln))


async def st_promo(update, ctx, s, t):
    uid = update.effective_user.id
    code = t.strip().upper()
    p = one("SELECT * FROM promos WHERE code=?", (code,))
    if not p:
        return await say(update, "❌ Bunday promo kod topilmadi.")
    if p["expires"] and p["expires"] < ts():
        return await say(update, "⏰ Bu promo kodning muddati tugagan.")
    if p["max_uses"] and p["used"] >= p["max_uses"]:
        return await say(update, "😔 Bu promo kod limiti tugagan.")
    if one("SELECT 1 FROM promo_uses WHERE user_id=? AND code=?", (uid, code)):
        return await say(update, "⚠️ Siz bu promo kodni allaqachon ishlatgansiz.")
    ex("UPDATE promos SET used=used+1 WHERE code=?", (code,))
    ex("INSERT INTO promo_uses(user_id,code,ts) VALUES(?,?,?)", (uid, code, ts()))
    credit(uid, p["amount"])
    await say(update, f"🎉 Promo kod faollashtirildi!\n💎 +{p['amount']} Almaz\n💰 Balans: {get_user(uid)['balance']} 💎")


# Spin
def spin_info(uid):
    r = get_user(uid)
    if r["spin_date"] != today():
        ex("UPDATE users SET spin_date=?, free_used=0, paid_used=0 WHERE id=?", (today(), uid))
        r = get_user(uid)
    return (max(0, sti("free_spins") - r["free_used"]), max(0, sti("paid_spins") - r["paid_used"]),
            r["bonus_spins"], r["balance"])


def spin_kb(uid):
    f, p, b, _ = spin_info(uid)
    k = []
    if f:
        k.append([IB(f"🆓 Bepul spin ({f} ta)", callback_data="spin:free")])
    if p:
        k.append([IB(f"💰 Pullik spin ({p} ta) - {sti('spin_price')} 💎", callback_data="spin:paid")])
    if b:
        k.append([IB(f"🎁 Bonus spin ({b} ta)", callback_data="spin:bonus")])
    k.append([IB("⬅️ Orqaga", callback_data="spin:back")])
    return IM(k)


async def spin_menu(update, ctx):
    clrst(ctx)
    f, p, b, bal = spin_info(update.effective_user.id)
    await say(update, f"🎰 <b>Spin Tizimi</b>\n\n📊 <b>Bugungi holat:</b>\n🆓 Bepul spin: {f} ta\n"
                      f"💰 Pullik spin: {p} ta (har biri {sti('spin_price')} 💎)\n🎁 Bonus spin: {b} ta\n\n"
                      f"💎 Balans: {bal}\n\n⚠️ Bonus spin uchun avval 🎁 <b>Bonus spin olish</b> tugmasini bosing!",
              rk([L_SPIN], [L_MYSPIN], [L_BONUS], [B_BOXMENU], [B_BACK]))


async def spin_choose(update, ctx):
    uid = update.effective_user.id
    f, p, b, bal = spin_info(uid)
    await say(update, f"🎰 <b>Spin tanlang</b>\n\n🆓 Bepul: {f} ta\n💰 Pullik: {p} ta — har biri {sti('spin_price')} 💎\n"
                      f"🎁 Bonus: {b} ta\n\n💎 Balans: {bal}", spin_kb(uid))


async def my_spins(update, ctx):
    f, p, b, bal = spin_info(update.effective_user.id)
    await say(update, f"📊 <b>Qolgan spinlar:</b>\n🆓 Bepul: {f}\n💰 Pullik: {p}\n🎁 Bonus: {b}\n\n💎 Balans: {bal}",
              spin_kb(update.effective_user.id))


async def cb_spin(update, ctx, a):
    q = update.callback_query
    uid, kind = q.from_user.id, a[1]
    if kind == "back":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return
    f, p, b, bal = spin_info(uid)
    if (kind == "free" and f <= 0) or (kind == "paid" and p <= 0) or (kind == "bonus" and b <= 0):
        return await q.answer("❌ Bu turdagi spin qolmagan", show_alert=True)
    if kind == "paid":
        if bal < sti("spin_price"):
            return await q.answer("❌ Almaz yetarli emas", show_alert=True)
        ex("UPDATE users SET balance=balance-?, paid_used=paid_used+1 WHERE id=?", (sti("spin_price"), uid))
    elif kind == "free":
        ex("UPDATE users SET free_used=free_used+1 WHERE id=?", (uid,))
    else:
        ex("UPDATE users SET bonus_spins=bonus_spins-1 WHERE id=?", (uid,))
    pr = rows("SELECT * FROM prizes")
    total = sum(x["weight"] for x in pr) or 1
    x, acc, win = random.uniform(0, total), 0, pr[-1]
    for pz in pr:
        acc += pz["weight"]
        if x <= acc:
            win = pz
            break
    amount, prob = win["amount"], win["weight"] / total * 100
    if amount:
        credit(uid, amount)
    ex("UPDATE users SET spins_total=spins_total+1 WHERE id=?", (uid,))
    await q.answer()
    try:
        await q.message.edit_text("🎰 Spin aylanmoqda... 🍒🍋🔔")
        await asyncio.sleep(1.2)
        if amount:
            res = f"🎉 <b>TABRIKLAYMIZ!</b>\n\n🎰 Yutdingiz: <b>{amount}</b> 💎!\n📊 Ehtimollik: {prob:.1f}%"
        else:
            res = f"😔 <b>Bu safar omad kelmadi...</b>\n\n📊 Ehtimollik: {prob:.1f}%\nYana urinib ko'ring!"
        await q.message.edit_text(res, parse_mode=HTML)
    except Exception:
        pass
    f, p, b, bal = spin_info(uid)
    await q.message.reply_text(f"📊 <b>Qolgan spinlar:</b>\n🆓 Bepul: {f}\n💰 Pullik: {p}\n🎁 Bonus: {b}\n\n"
                               f"💎 Yangi balans: {bal}", parse_mode=HTML, reply_markup=spin_kb(uid))


async def bonus_menu(update, ctx):
    uid = update.effective_user.id
    if get_user(uid)["bonus_date"] == today():
        return await say(update, "✅ Bugungi bonus spinni allaqachon olgansiz. Ertaga yana urinib ko'ring!")
    tk = rows("SELECT * FROM tasks")
    if not tk:
        ex("UPDATE users SET bonus_spins=bonus_spins+1, bonus_date=? WHERE id=?", (today(), uid))
        return await say(update, "🎁 Bonus spin berildi! 🎰 Spin bo'limiga o'ting.")
    kb = [[IB(f"📌 {t['title']}", url=t["url"])] for t in tk if t["url"]] + [[IB("✅ Tekshirish", callback_data="bonus:check")]]
    await say(update, "🎁 <b>Bonus spin olish</b>\n\nTasklarni bajaring va <b>✅ Tekshirish</b> ni bosing:", IM(kb))


async def cb_bonus(update, ctx, a):
    q = update.callback_query
    uid = q.from_user.id
    if get_user(uid)["bonus_date"] == today():
        return await q.answer("Bugun bonus olgansiz", show_alert=True)
    for t in rows("SELECT * FROM tasks WHERE chat_id!='' AND chat_id IS NOT NULL"):
        try:
            m = await ctx.bot.get_chat_member(t["chat_id"], uid)
            if m.status in ("left", "kicked"):
                return await q.answer(f"❌ Bajarilmadi: {t['title']}", show_alert=True)
        except Exception:
            pass
    ex("UPDATE users SET bonus_spins=bonus_spins+1, bonus_date=? WHERE id=?", (today(), uid))
    await q.answer("🎁 Bonus spin berildi!", show_alert=True)
    await aedit(update, "✅ Tasklar bajarildi! 🎁 Bonus spin qo'shildi. 🎰 Spin bo'limiga o'ting.")


# Quti o'yini
def box_kb():
    return IM([[IB("📦", callback_data="bx:0"), IB("📦", callback_data="bx:1"), IB("📦", callback_data="bx:2")],
               [tb(B_BACK)]])


async def box_menu(update, ctx):
    clrst(ctx)
    await say(update, f"🎲 <b>Quti o'yini</b>\n\nHar o'yin narxi: <b>{BOX_COST} 💎</b>\nQutini tanlang 👇", box_kb())


async def cb_bx(update, ctx, a):
    q = update.callback_query
    uid = q.from_user.id
    if a[1] == "again":
        await q.answer()
        return await aedit(update, f"🎲 <b>Quti o'yini</b>\n\nHar o'yin narxi: <b>{BOX_COST} 💎</b>\nQutini tanlang 👇", box_kb())
    r = get_user(uid)
    if r["balance"] < BOX_COST:
        return await q.answer(f"❌ Almaz yetarli emas (kerak: {BOX_COST} 💎)", show_alert=True)
    ex("UPDATE users SET balance=balance-? WHERE id=?", (BOX_COST, uid))
    prize = random.choices([x for x, _ in BOX_PRIZES], weights=[w for _, w in BOX_PRIZES])[0]
    if prize:
        credit(uid, prize)
    res = f"🎉 <b>+{prize} 💎</b>" if prize else "💀 Bo'sh quti!"
    await q.answer()
    await aedit(update, f"📦 {int(a[1]) + 1}-quti ochildi: {res}\n\n💎 Balans: <b>{get_user(uid)['balance']}</b>",
                IM([[IB("🔁 Yana o'ynash", callback_data="bx:again")], [tb(B_BACK)]]))


# Zar o'yini
async def zar_menu(update, ctx):
    clrst(ctx)
    await say(update, f"🎲 <b>Zar o'yini</b>\n\nHar tashlash: <b>{ZAR_COST} 💎</b>\n"
                      f"Sizniki botnikidan katta bo'lsa — +{ZAR_COST * 2} 💎, teng bo'lsa stavka qaytadi.",
              IM([[IB(f"🎲 Tashla ({ZAR_COST} 💎)", callback_data="zt")], [tb(B_BACK)]]))


async def cb_zt(update, ctx, a):
    uid = update.callback_query.from_user.id
    r = get_user(uid)
    if r["balance"] < ZAR_COST:
        return await update.callback_query.answer(f"❌ Kerak: {ZAR_COST} 💎", show_alert=True)
    me, bot_ = random.randint(1, 6), random.randint(1, 6)
    ex("UPDATE users SET balance=balance-? WHERE id=?", (ZAR_COST, uid))
    if me > bot_:
        credit(uid, 2 * ZAR_COST)
        res = f"🎉 Yutdingiz! +{ZAR_COST} 💎"
    elif me == bot_:
        credit(uid, ZAR_COST)
        res = "🤝 Durang, stavka qaytdi."
    else:
        res = f"😔 Yutqazdingiz. -{ZAR_COST} 💎"
    await aedit(update, f"🎲 Siz: <b>{me}</b> | Bot: <b>{bot_}</b>\n\n{res}\n💎 Balans: <b>{get_user(uid)['balance']}</b>",
                IM([[IB("🎲 Yana", callback_data="zt")], [tb(B_BACK)]]))
    return None


# Son tanlash
def guess_kb():
    btns = [IB(str(n), callback_data=f"gs:{n}") for n in range(1, 6)]
    return IM([btns, [tb(B_BACK)]])


async def guess_menu(update, ctx):
    clrst(ctx)
    await say(update, f"🔢 <b>Son tanlash</b>\n\nBot 1 dan 5 gacha bitta son o'yladi.\n"
                      f"Urinish: {GUESS_COST} 💎. To'g'ri topsangiz +{GUESS_WIN} 💎!", guess_kb())


async def cb_gm(update, ctx, a):
    await update.callback_query.answer()
    await aedit(update, f"🔢 <b>Son tanlash</b>\n\nBot 1 dan 5 gacha bitta son o'yladi.\n"
                        f"Urinish: {GUESS_COST} 💎. To'g'ri topsangiz +{GUESS_WIN} 💎!", guess_kb())


async def cb_gs(update, ctx, a):
    uid = update.callback_query.from_user.id
    n = int(a[1])
    r = get_user(uid)
    if r["balance"] < GUESS_COST:
        return await update.callback_query.answer(f"❌ Kerak: {GUESS_COST} 💎", show_alert=True)
    ex("UPDATE users SET balance=balance-? WHERE id=?", (GUESS_COST, uid))
    secret = random.randint(1, 5)
    if n == secret:
        credit(uid, GUESS_WIN)
        res = f"🎉 To'g'ri! Bot {secret} deb o'ylagan edi. +{GUESS_WIN} 💎"
    else:
        res = f"😔 Noto'g'ri. Bot {secret} deb o'ylagan edi."
    await aedit(update, f"🔢 {res}\n💎 Balans: <b>{get_user(uid)['balance']}</b>",
                IM([[IB("🔁 Yana", callback_data="gm")], [tb(B_BACK)]]))
    return None


# Reyting / daraja / profil
async def top(update, ctx):
    rs = rows("SELECT id,username,name,earned FROM users WHERE banned=0 AND verified=1 ORDER BY earned DESC LIMIT 10")
    ln = []
    for r in rs:
        who = "@" + esc(r["username"]) if r["username"] else esc(r["name"] or ("ID " + str(r["id"])))
        ln.append(f"⭐ {who} — 💎 {r['earned']}")
    kb = None
    if st("proofs_url").startswith("http"):
        kb = IM([[IB("📜 Isbotlar", url=st("proofs_url"))]])
    await say(update, "🏆 <b>Top 10 (topilgan almaz bo'yicha):</b>\n\n" + ("\n".join(ln) or "Hozircha bo'sh"), kb)


def league_of(pts):
    cur = nxt = None
    for l in rows("SELECT * FROM leagues ORDER BY min_points"):
        if l["min_points"] <= pts:
            cur = l
        elif nxt is None:
            nxt = l
    return cur, nxt


def lg_name(l):
    return f"{l['emoji']} {l['name']} liga" if l else "—"


async def profile(update, ctx):
    clrst(ctx)
    r = get_user(update.effective_user.id)
    cur, _ = league_of(r["points"])
    th = THEMES[r["theme"] or "olov"]
    await say(update, f"👤 <b>Profilingiz</b> {th[0]}\n\n👤 Username: {tag(r)}\n🎮 Free Fire ID: "
                      f"<code>{esc(r['ff_id']) or 'Kiritilmagan'}</code>\n🥇 Liga: <b>{lg_name(cur)}</b>\n"
                      f"📊 Reyting ballari: {r['points']}\n💎 Almaz: <b>{r['balance']}</b>\n"
                      f"🤝 Tasdiqlangan takliflar: {r['refs']}\n🎨 Mavzu: {th[1]}",
              IM([[IB("💳 Almazni yechish", callback_data="prof:wd"), IB("🆔 FF ID", callback_data="prof:ff")],
                  [IB("📈 Statistika", callback_data="prof:stat"), IB("🎨 Mavzu", callback_data="prof:theme")],
                  [tb(B_BACK)]]))


async def cb_prof(update, ctx, a):
    q, uid = update.callback_query, update.callback_query.from_user.id
    r = get_user(uid)
    await q.answer()
    if a[1] == "theme":
        nxt = THEME_ORDER[(THEME_ORDER.index(r["theme"] or "olov") + 1) % len(THEME_ORDER)]
        ex("UPDATE users SET theme=? WHERE id=?", (nxt, uid))
        return await profile(update, ctx)
    if a[1] == "ff":
        setst(ctx, "ff_id")
        await say(update, "🆔 Free Fire ID raqamingizni yuboring (faqat raqam):", rk([B_BACK]))
    elif a[1] == "wd":
        if not r["ff_id"]:
            setst(ctx, "ff_id")
            return await say(update, "🆔 Avval Free Fire ID raqamingizni yuboring:", rk([B_BACK]))
        mn = sti("min_withdraw")
        if r["balance"] < mn:
            return await say(update, f"❌ Minimal yechish: <b>{mn} 💎</b>\nBalansingiz: {r['balance']} 💎")
        setst(ctx, "wd_amount")
        await say(update, f"💳 Qancha almaz yechmoqchisiz?\n\nMinimal: {mn} 💎 | Balans: {r['balance']} 💎\n"
                          f"FF ID: <code>{esc(r['ff_id'])}</code>", rk([B_BACK]))
    elif a[1] == "stat":
        sp = one("SELECT COUNT(*) FROM promo_uses WHERE user_id=?", (uid,))[0]
        od = one("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,))[0]
        await say(update, f"📈 <b>Statistika</b>\n\n👥 Takliflar: {r['refs']}\n💎 Jami topilgan: {r['earned']}\n"
                          f"🎰 Spinlar: {r['spins_total']}\n🎁 Promo kodlar: {sp}\n🛒 Buyurtmalar: {od}\n"
                          f"📅 Qo'shilgan: {datetime.fromtimestamp(r['joined'], TZ):%d.%m.%Y}")


async def st_ff_id(update, ctx, s, t):
    if not re.fullmatch(r"\d{5,15}", t.strip()):
        return await say(update, "❌ FF ID faqat raqamlardan iborat bo'lishi kerak (5-15 ta).")
    upd(update.effective_user.id, ff_id=t.strip())
    clrst(ctx)
    await say(update, "✅ FF ID saqlandi!", main_kb(update.effective_user.id))


async def st_wd(update, ctx, s, t):
    uid = update.effective_user.id
    r = get_user(uid)
    if not t.strip().isdigit():
        return await say(update, "❌ Faqat raqam yuboring.")
    n = int(t)
    if n < sti("min_withdraw") or n > r["balance"]:
        return await say(update, f"❌ Miqdor {sti('min_withdraw')} dan {r['balance']} gacha bo'lishi kerak.")
    ex("UPDATE users SET balance=balance-? WHERE id=?", (n, uid))
    wid = ex("INSERT INTO withdrawals(user_id,amount,ff_id,status,ts) VALUES(?,?,?,'pending',?)",
             (uid, n, r["ff_id"], ts())).lastrowid
    clrst(ctx)
    await say(update, f"✅ So'rov #{wid} yuborildi! Admin tekshirgach almazlar FF ID ga yuboriladi.", main_kb(uid))
    await notify_admins(ctx, wd_text(wid), wd_kb(wid))


def wd_text(wid):
    w = one("SELECT * FROM withdrawals WHERE id=?", (wid,))
    u = get_user(w["user_id"])
    return (f"💳 <b>Yechish #{wid}</b>\n👤 {mention(u)} ({tag(u)})\n💎 {w['amount']}\n"
            f"🆔 FF ID: <code>{esc(w['ff_id'])}</code>\n📌 {w['status']}")


def wd_kb(wid):
    return IM([[IB("✅ Bajarildi", callback_data=f"wd:ok:{wid}"), IB("❌ Rad etish", callback_data=f"wd:no:{wid}")]])


async def cb_wd(update, ctx, a):
    q = update.callback_query
    w = one("SELECT * FROM withdrawals WHERE id=?", (int(a[2]),))
    if not w or w["status"] != "pending":
        return await q.answer("Allaqachon ko'rib chiqilgan", show_alert=True)
    if a[1] == "ok":
        ex("UPDATE withdrawals SET status='done' WHERE id=?", (w["id"],))
        msg, mark = f"✅ Yechish #{w['id']} bajarildi! 💎 {w['amount']} FF ID ga yuborildi.", "✅ BAJARILDI"
        pc = st("proofs_chat").strip()
        if pc:
            u = get_user(w["user_id"])
            try:
                await ctx.bot.send_message(pc if not pc.lstrip("-").isdigit() else int(pc),
                                           f"✅ <b>Yangi to'lov!</b>\n👤 {tag(u)}\n💎 {w['amount']} Almaz yechildi",
                                           parse_mode=HTML)
            except Exception as e:
                log.warning("proof: %s", e)
    else:
        ex("UPDATE withdrawals SET status='rejected' WHERE id=?", (w["id"],))
        ex("UPDATE users SET balance=balance+? WHERE id=?", (w["amount"], w["user_id"]))
        msg, mark = f"❌ Yechish #{w['id']} rad etildi. 💎 {w['amount']} balansingizga qaytarildi.", "❌ RAD ETILDI"
    await q.answer("Bajarildi")
    await aedit(update, wd_text(w["id"]) + f"\n\n<b>{mark}</b>")
    try:
        await ctx.bot.send_message(w["user_id"], msg)
    except Exception:
        pass


async def level_menu(update, ctx):
    clrst(ctx)
    r = get_user(update.effective_user.id)
    cur, nxt = league_of(r["points"])
    nx = (f"🎯 <b>Keyingi liga:</b> {nxt['name']}\nUnga yana <b>{nxt['min_points'] - r['points']}</b> ball kerak."
          if nxt else "🏆 Siz eng yuqori ligadasiz!")
    await say(update, f"🥇 <b>Mening darajam</b>\n\n⭐ Joriy liga: <b>{lg_name(cur)}</b>\n📊 Ball: {r['points']}\n"
                      f"📌 Takliflar: {r['refs']}\n💎 Balans: {r['balance']}\n\n{nx}",
              IM([[IB("Darajani qanday oshiramiz ❓", callback_data="lvl:how")], [tb(B_BACK)]]))


async def cb_lvl(update, ctx, a):
    await update.callback_query.answer()
    await say(update, st("how_text").replace("{pts}", str(sti("ref_points"))))


# ───────────────────────── 🤝 SHERIK TOPISH ─────────────────────────
INV = {}


async def partner_menu(update, ctx):
    clrst(ctx)
    await say(update, "⚔️ <b>Sherik topish (Beta)</b>\n\nQuyidagilardan birini tanlang:",
              rk([L_FIND], [L_AD], [L_PASS], [L_GUIDE], [B_BACK]))


async def guide(update, ctx):
    await say(update, st("guide_text").replace("{hours}", str(sti("ad_hours"))))


def card(r, mode):
    return (f"👤 {tag(r)} | 🆙 Lvl: <b>{r['level'] or '?'}</b>\n🎮 {esc(mode)} | 🎙 {esc(r['mic'])}\n"
            f"💬 <i>{esc(r['bio']) or '—'}</i>")


def pick_ad(uid, seen):
    ids = ",".join(str(int(x)) for x in seen) or "0"
    return one(f"SELECT a.mode, u.* FROM partner_ads a JOIN users u ON u.id=a.user_id WHERE a.user_id!=? AND a.ts>? "
               f"AND u.banned=0 AND a.user_id NOT IN ({ids}) ORDER BY RANDOM() LIMIT 1",
               (uid, ts() - sti("ad_hours") * 3600))


def ad_kb(tid):
    return IM([[IB("🤝 Taklif yuborish", callback_data=f"ptr:inv:{tid}"), IB("➡️ Keyingisi", callback_data="ptr:next")],
               [IB("❌ Chiqish", callback_data="ptr:exit")]])


async def partner_find(update, ctx):
    clrst(ctx)
    uid = update.effective_user.id
    ctx.user_data["seen"] = []
    r = pick_ad(uid, [])
    if not r:
        return await say(update, "😔 Hozircha e'lonlar yo'q.\n📢 <b>E'lon bering</b> — sherik chiqsa xabar beramiz!")
    ctx.user_data["seen"].append(r["id"])
    await say(update, card(r, r["mode"]), ad_kb(r["id"]))


async def cb_ptr(update, ctx, a):
    q, uid = update.callback_query, update.callback_query.from_user.id
    me = get_user(uid)
    act = a[1]
    if act == "exit":
        await q.answer()
        return await q.message.delete()
    if act == "next":
        seen = ctx.user_data.setdefault("seen", [])
        r = pick_ad(uid, seen)
        await q.answer()
        if not r:
            ctx.user_data["seen"] = []
            return await aedit(update, "😔 Boshqa e'lon yo'q. Keyinroq qayta urinib ko'ring.")
        seen.append(r["id"])
        return await aedit(update, card(r, r["mode"]), ad_kb(r["id"]))
    if act == "inv":
        tid = int(a[2])
        my = one("SELECT mode FROM partner_ads WHERE user_id=?", (uid,))
        if INV.get((uid, tid), 0) > time.time():
            return await q.answer("⏳ Bu foydalanuvchiga yaqinda taklif yuborgansiz", show_alert=True)
        INV[(uid, tid)] = time.time() + 600
        try:
            await ctx.bot.send_message(tid, f"🤝 <b>Sizga sherik taklifi!</b>\n\n{card(me, my['mode'] if my else '—')}",
                                       parse_mode=HTML,
                                       reply_markup=IM([[IB("✅ Qabul qilish", callback_data=f"ptr:acc:{uid}"),
                                                         IB("❌ Rad etish", callback_data=f"ptr:rej:{uid}")]]))
        except Exception:
            return await q.answer("❌ Foydalanuvchiga xabar yuborib bo'lmadi", show_alert=True)
        await q.answer()
        return await q.message.reply_text("📨 Taklif yuborildi, javob kutilmoqda...")
    if act in ("acc", "rej"):
        sid = int(a[2])
        s = get_user(sid)
        await q.answer()
        if act == "acc":
            await aedit(update, f"✅ Taklif qabul qilindi!\nSherigingiz: {mention(s)} {tag(s)}")
            try:
                await ctx.bot.send_message(sid, f"🎉 Taklifingiz qabul qilindi!\nSherigingiz: {mention(me)} {tag(me)}",
                                           parse_mode=HTML)
            except Exception:
                pass
        else:
            await aedit(update, "❌ Taklif rad etildi.")
            try:
                await ctx.bot.send_message(sid, "😔 Taklifingiz rad etildi. Boshqa sherik qidirib ko'ring.")
            except Exception:
                pass


async def ad_start(update, ctx):
    setst(ctx, "ad_mode")
    await say(update, "🎮 <b>Qaysi rejimda e'lon berasiz?</b>", rk(MODES[:2], [MODES[2]], [B_BACK]))


async def st_ad_mode(update, ctx, s, t):
    uid = update.effective_user.id
    if t not in MODES:
        return await say(update, "Rejimni tugmalardan tanlang 👇")
    ex("INSERT INTO partner_ads(user_id,mode,ts) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE "
       "SET mode=excluded.mode, ts=excluded.ts", (uid, t, ts()))
    clrst(ctx)
    await say(update, "✅ <b>E'loningiz joylandi!</b>\nSherik chiqsa xabar beramiz.",
              rk([L_FIND], [L_AD], [L_PASS], [L_GUIDE], [B_BACK]))
    asyncio.create_task(notify_ad(ctx, uid, t))


async def notify_ad(ctx, uid, mode):
    me = get_user(uid)
    for r in rows("SELECT a.user_id FROM partner_ads a JOIN users u ON u.id=a.user_id WHERE a.mode=? AND a.user_id!=? "
                  "AND a.ts>? AND u.banned=0 ORDER BY RANDOM() LIMIT 8", (mode, uid, ts() - sti("ad_hours") * 3600)):
        try:
            await ctx.bot.send_message(r["user_id"], f"🔔 <b>Yangi sherik e'loni!</b>\n\n{card(me, mode)}",
                                       parse_mode=HTML,
                                       reply_markup=IM([[IB("🤝 Taklif yuborish", callback_data=f"ptr:inv:{uid}")]]))
        except Exception:
            pass
        await asyncio.sleep(0.05)


def pass_kb(r):
    return IM([[IB("🆙 Level", callback_data="pp:level"), IB(f"🎙 Mikrofon: {r['mic']}", callback_data="pp:mic")],
               [IB("💬 Izoh", callback_data="pp:bio"), IB("🎮 FF ID", callback_data="pp:ff")]])


def pass_text(r):
    ad = one("SELECT mode FROM partner_ads WHERE user_id=?", (r["id"],))
    return (f"👤 <b>Mening pasportim</b>\n\n🆔 FF ID: <code>{esc(r['ff_id']) or '—'}</code>\n"
            f"🆙 Level: {r['level'] or '—'}\n🎙 Mikrofon: {esc(r['mic'])}\n💬 Izoh: {esc(r['bio']) or '—'}\n"
            f"📢 E'lon: {ad['mode'] if ad else 'yo‘q'}")


async def passport(update, ctx):
    clrst(ctx)
    r = get_user(update.effective_user.id)
    await say(update, pass_text(r), pass_kb(r))


async def cb_pp(update, ctx, a):
    q, uid = update.callback_query, update.callback_query.from_user.id
    await q.answer()
    if a[1] == "mic":
        r = get_user(uid)
        upd(uid, mic="Yoq" if r["mic"] == "Bor" else "Bor")
        r = get_user(uid)
        return await aedit(update, pass_text(r), pass_kb(r))
    setst(ctx, {"level": "pp_level", "bio": "pp_bio", "ff": "ff_id"}[a[1]])
    await say(update, {"level": "🆙 Levelingizni yuboring (1-100):", "bio": "💬 Qisqa izoh yozing (max 80 belgi):",
                       "ff": "🆔 FF ID yuboring:"}[a[1]], rk([B_BACK]))


async def st_pp_level(update, ctx, s, t):
    if not t.isdigit() or not 1 <= int(t) <= 100:
        return await say(update, "❌ 1 dan 100 gacha raqam yuboring.")
    upd(update.effective_user.id, level=int(t))
    clrst(ctx)
    await say(update, "✅ Level saqlandi!", rk([L_FIND], [L_AD], [L_PASS], [L_GUIDE], [B_BACK]))


async def st_pp_bio(update, ctx, s, t):
    upd(update.effective_user.id, bio=t.strip()[:80])
    clrst(ctx)
    await say(update, "✅ Izoh saqlandi!", rk([L_FIND], [L_AD], [L_PASS], [L_GUIDE], [B_BACK]))


# ───────────────────────── 🛒 DO'KON VA XIZMATLAR ─────────────────────────
async def shop_menu(update, ctx):
    clrst(ctx)
    await say(update, st("shop_text"), rk([CATS["direct"]], [CATS["pack"], CATS["emote"]], [CATS["skin"]],
                                          [L_MYORD], [B_BACK]))


async def yt_menu(update, ctx):
    clrst(ctx)
    await say(update, st("service_text"), rk([L_SVC], [L_MYORD], [B_BACK]))


async def show_cat(update, ctx, cat, edit=False):
    its = rows("SELECT * FROM items WHERE cat=? AND active=1 ORDER BY price", (cat,))
    kb = IM([[IB(f"{i['name']} — {i['price']} 💎", callback_data=f"it:{i['id']}")] for i in its]) if its else None
    text = f"<b>{CATS[cat]}</b>\n\nMahsulotni tanlang 👇" if its else f"<b>{CATS[cat]}</b>\n\nHozircha mahsulot yo'q."
    if edit:
        await aedit(update, text, kb)
    else:
        await say(update, text, kb)


def cat_handler(cat):
    async def h(update, ctx):
        clrst(ctx)
        await show_cat(update, ctx, cat)
    return h


async def cb_cat(update, ctx, a):
    await update.callback_query.answer()
    await show_cat(update, ctx, a[1], edit=True)


async def cb_item(update, ctx, a):
    q = update.callback_query
    i = one("SELECT * FROM items WHERE id=? AND active=1", (int(a[1]),))
    if not i:
        return await q.answer("Topilmadi", show_alert=True)
    await q.answer()
    await aedit(update, f"<b>{esc(i['name'])}</b>\n\n{esc(i['descr'])}\n\n💎 Narxi: <b>{i['price']}</b> Almaz",
                IM([[IB("🛒 Sotib olish", callback_data=f"buy:{i['id']}")],
                    [IB("⬅️ Orqaga", callback_data=f"cat:{i['cat']}")]]))


async def cb_buy(update, ctx, a):
    q, uid = update.callback_query, update.callback_query.from_user.id
    i = one("SELECT * FROM items WHERE id=? AND active=1", (int(a[1]),))
    if not i:
        return await q.answer("Topilmadi", show_alert=True)
    r = get_user(uid)
    if r["balance"] < i["price"]:
        return await q.answer(f"❌ Almaz yetarli emas. Kerak: {i['price']} 💎, sizda: {r['balance']} 💎", show_alert=True)
    await q.answer()
    if i["cat"] == "service":
        setst(ctx, "svc_note", id=i["id"])
        return await say(update, "📝 Buyurtma tafsilotlarini yozing (havola, talablar, bog'lanish uchun username):", rk([B_BACK]))
    if not r["ff_id"]:
        setst(ctx, "shop_ffid", id=i["id"])
        return await say(update, "🆔 Free Fire ID raqamingizni yuboring:", rk([B_BACK]))
    await confirm_buy(update, i, r["ff_id"])


async def confirm_buy(update, i, ff):
    await say(update, f"🛒 <b>Tasdiqlaysizmi?</b>\n\n📦 {esc(i['name'])}\n💎 {i['price']} Almaz\n🆔 FF ID: <code>{esc(ff)}</code>",
              IM([[IB("✅ Tasdiqlash", callback_data=f"buyok:{i['id']}"), IB("❌ Bekor", callback_data="x:0")]]))


async def cb_x(update, ctx, a):
    await update.callback_query.answer()
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass


async def create_order(ctx, uid, i, ff, note):
    r = get_user(uid)
    if r["balance"] < i["price"]:
        return None
    ex("UPDATE users SET balance=balance-? WHERE id=?", (i["price"], uid))
    oid = ex("INSERT INTO orders(user_id,item_id,name,cat,price,ff_id,note,status,ts) VALUES(?,?,?,?,?,?,?,'pending',?)",
             (uid, i["id"], i["name"], i["cat"], i["price"], ff, note, ts())).lastrowid
    await notify_admins(ctx, ord_text(oid), ord_kb(oid))
    return oid


def ord_text(oid):
    o = one("SELECT * FROM orders WHERE id=?", (oid,))
    u = get_user(o["user_id"])
    return (f"🧾 <b>Buyurtma #{oid}</b>\n👤 {mention(u)} ({tag(u)})\n📦 {esc(o['name'])} [{o['cat']}]\n💎 {o['price']}\n"
            f"🆔 FF ID: <code>{esc(o['ff_id']) or '—'}</code>\n📝 {esc(o['note']) or '—'}\n📌 {o['status']}")


def ord_kb(oid):
    return IM([[IB("✅ Bajarildi", callback_data=f"ord:ok:{oid}"), IB("❌ Rad etish", callback_data=f"ord:no:{oid}")]])


async def cb_buyok(update, ctx, a):
    q, uid = update.callback_query, update.callback_query.from_user.id
    i = one("SELECT * FROM items WHERE id=? AND active=1", (int(a[1]),))
    r = get_user(uid)
    if not i or not r["ff_id"]:
        return await q.answer("Xatolik", show_alert=True)
    oid = await create_order(ctx, uid, i, r["ff_id"], "")
    if oid is None:
        return await q.answer("❌ Almaz yetarli emas", show_alert=True)
    await q.answer("✅ Buyurtma qabul qilindi")
    await aedit(update, f"✅ <b>Buyurtma #{oid} qabul qilindi!</b>\nAdmin tez orada bajaradi.")


async def st_shop_ffid(update, ctx, s, t):
    if not re.fullmatch(r"\d{5,15}", t.strip()):
        return await say(update, "❌ FF ID faqat raqam (5-15 ta).")
    upd(update.effective_user.id, ff_id=t.strip())
    i = one("SELECT * FROM items WHERE id=?", (s["id"],))
    clrst(ctx)
    if i:
        await confirm_buy(update, i, t.strip())


async def st_svc_note(update, ctx, s, t):
    i = one("SELECT * FROM items WHERE id=? AND active=1", (s["id"],))
    uid = update.effective_user.id
    clrst(ctx)
    if not i:
        return await say(update, "❌ Xizmat topilmadi.", main_kb(uid))
    oid = await create_order(ctx, uid, i, get_user(uid)["ff_id"] or "", t.strip()[:500])
    if oid is None:
        return await say(update, "❌ Almaz yetarli emas.", main_kb(uid))
    await say(update, f"✅ <b>Buyurtma #{oid} qabul qilindi!</b>\nAdmin siz bilan bog'lanadi.", main_kb(uid))


async def my_orders(update, ctx):
    clrst(ctx)
    rs = rows("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 15", (update.effective_user.id,))
    if not rs:
        return await say(update, "📰 Sizda hali buyurtmalar yo'q.")
    em = {"pending": "⏳ Kutilmoqda", "done": "✅ Bajarildi", "rejected": "❌ Rad etildi"}
    await say(update, "📰 <b>Mening buyurtmalarim:</b>\n\n" + "\n".join(
        f"#{o['id']} • {esc(o['name'])} • 💎{o['price']} • {em.get(o['status'], o['status'])}" for o in rs))


async def cb_ord(update, ctx, a):
    q = update.callback_query
    o = one("SELECT * FROM orders WHERE id=?", (int(a[2]),))
    if not o or o["status"] != "pending":
        return await q.answer("Allaqachon ko'rib chiqilgan", show_alert=True)
    if a[1] == "ok":
        ex("UPDATE orders SET status='done' WHERE id=?", (o["id"],))
        msg, mark = f"✅ Buyurtma #{o['id']} ({o['name']}) bajarildi!", "✅ BAJARILDI"
    else:
        ex("UPDATE orders SET status='rejected' WHERE id=?", (o["id"],))
        ex("UPDATE users SET balance=balance+? WHERE id=?", (o["price"], o["user_id"]))
        msg, mark = f"❌ Buyurtma #{o['id']} rad etildi. 💎 {o['price']} qaytarildi.", "❌ RAD ETILDI"
    await q.answer("Bajarildi")
    await aedit(update, ord_text(o["id"]) + f"\n\n<b>{mark}</b>")
    try:
        await ctx.bot.send_message(o["user_id"], msg)
    except Exception:
        pass


# ───────────────────────── 👻 QORONG'U DUNYO ─────────────────────────
async def horror_menu(update, ctx):
    clrst(ctx)
    await say(update, "👻 <b>Qorong'u dunyo</b>\n\nTanlang... ehtiyot bo'ling 👁",
              rk([L_FACT], [L_STORY], [L_CURSE], [B_BACK]))


async def fact_send(update, ctx):
    await say(update, f"🤯 <b>Dahshat fakt:</b>\n\n{random.choice(FACTS)}")


async def story_send(update, ctx):
    await say(update, random.choice(STORIES))


async def curse_send(update, ctx):
    await say(update, random.choice(CURSES))


# ───────────────────────── 👑 ADMIN PANEL ─────────────────────────
TASKS = set()


def adm_kb():
    return IM([
        [IB("📊 Statistika", callback_data="a:stats"), IB("📢 Xabar yuborish", callback_data="a:bc")],
        [IB("👥 Foydalanuvchi", callback_data="a:usr"), IB("⚙️ Sozlamalar", callback_data="as:l:0")],
        [IB("📣 Majburiy obuna", callback_data="ac:l"), IB("🎁 Promo kodlar", callback_data="ap:l")],
        [IB("🎰 Spin sovrinlari", callback_data="ar:l"), IB("✅ Bonus tasklar", callback_data="at:l")],
        [IB("🛒 Do'kon / Xizmatlar", callback_data="ae:l"), IB("🧾 Buyurtmalar", callback_data="a:od")],
        [IB("📱 Tekin nastroyka", callback_data="na:l"), IB("🏅 Ligalar", callback_data="al:l")],
        [IB("🛡 Adminlar", callback_data="aa:l")],
        [IB("💾 Backup", callback_data="a:bk"), IB("♻️ Restore", callback_data="a:rs")],
    ])


async def admin_panel(update, ctx):
    if not is_admin(update.effective_user.id):
        return
    clrst(ctx)
    await say(update, "👑 <b>Admin panel</b>\n\nBotni boshqarish markazi 👇", adm_kb())


async def admin_cmd(update, ctx):
    await admin_panel(update, ctx)


async def crud_list(update, title, lines, dels, addcb, backcb="a:home"):
    kb = [[IB(f"🗑 {l}"[:60], callback_data=d)] for l, d in dels] + [[IB("➕ Qo'shish", callback_data=addcb)], back(backcb)]
    await aedit(update, f"{title}\n\n" + "\n".join(lines or ["<i>Hozircha bo'sh</i>"]), IM(kb))


async def cb_a(update, ctx, a):
    q, s = update.callback_query, a[1]
    if s == "home":
        clrst(ctx)
        await aedit(update, "👑 <b>Admin panel</b>\n\nBotni boshqarish markazi 👇", adm_kb())
    elif s == "stats":
        n = lambda sql, p=(): one(sql, p)[0]
        day0 = int(now().replace(hour=0, minute=0, second=0).timestamp())
        act = ts() - sti("ad_hours") * 3600
        PEND_O = "SELECT COUNT(*) FROM orders WHERE status='pending'"
        PEND_W = "SELECT COUNT(*) FROM withdrawals WHERE status='pending'"
        txt = ("📊 <b>Statistika</b>\n\n"
               f"👥 Foydalanuvchilar: {n('SELECT COUNT(*) FROM users')} (tasdiqlangan: {n('SELECT COUNT(*) FROM users WHERE verified=1')})\n"
               f"🆕 Bugun qo'shilgan: {n('SELECT COUNT(*) FROM users WHERE joined>?', (day0,))}\n"
               f"🚫 Banlangan: {n('SELECT COUNT(*) FROM users WHERE banned=1')}\n"
               f"💎 Jami balans: {n('SELECT COALESCE(SUM(balance),0) FROM users')} | Jami topilgan: {n('SELECT COALESCE(SUM(earned),0) FROM users')}\n"
               f"🎰 Spinlar: {n('SELECT COALESCE(SUM(spins_total),0) FROM users')}\n"
               f"🔐 Nastroyka kodlari: {n('SELECT COUNT(*) FROM ncodes')}\n"
               f"🧾 Kutilayotgan buyurtma: {n(PEND_O)}\n"
               f"💳 Kutilayotgan yechish: {n(PEND_W)}\n"
               f"📢 Faol sherik e'lonlari: {n('SELECT COUNT(*) FROM partner_ads WHERE ts>?', (act,))}")
        await q.answer()
        await aedit(update, txt, IM([back()]))
    elif s == "bc":
        setst(ctx, "adm_bc")
        await q.answer()
        await aedit(update, "📢 <b>Xabar yuborish</b>\n\nHammaga yuboriladigan xabarni yuboring (matn, rasm, video...):", IM([back()]))
    elif s == "bcgo":
        d = ctx.user_data.pop("bc", None)
        await q.answer()
        if not d:
            return
        await aedit(update, "📢 Yuborish boshlandi... Tugagach xabar beraman.", IM([back()]))
        t = asyncio.create_task(do_broadcast(ctx, q.message.chat_id, d[0], d[1]))
        TASKS.add(t)
        t.add_done_callback(TASKS.discard)
    elif s == "usr":
        setst(ctx, "adm_usr")
        await q.answer()
        await aedit(update, "👥 Foydalanuvchi ID yoki @username yuboring:", IM([back()]))
    elif s == "od":
        await q.answer()
        os_ = rows("SELECT id FROM orders WHERE status='pending' ORDER BY id LIMIT 10")
        ws = rows("SELECT id FROM withdrawals WHERE status='pending' ORDER BY id LIMIT 10")
        if not os_ and not ws:
            return await aedit(update, "🧾 Kutilayotgan buyurtma va yechishlar yo'q ✅", IM([back()]))
        await aedit(update, f"🧾 Kutilayotgan: {len(os_)} buyurtma, {len(ws)} yechish (pastda)", IM([back()]))
        for o in os_:
            await q.message.reply_text(ord_text(o["id"]), parse_mode=HTML, reply_markup=ord_kb(o["id"]))
        for w in ws:
            await q.message.reply_text(wd_text(w["id"]), parse_mode=HTML, reply_markup=wd_kb(w["id"]))
    elif s == "bk" and IS_PG:
        await q.answer("✅ Postgres (Neon) ishlatilmoqda — ma'lumotlar doim saqlanadi.", show_alert=True)
    elif s == "rs" and IS_PG:
        await q.answer("Postgres rejimida restore kerak emas.", show_alert=True)
    elif s == "bk":
        await q.answer("Tayyorlanmoqda...")
        path = tempfile.mktemp(suffix=".db")
        dst = sqlite3.connect(path)
        db.backup(dst)
        dst.close()
        with open(path, "rb") as f:
            await q.message.reply_document(f, filename=f"backup_{today()}.db", caption="💾 Baza nusxasi")
        os.remove(path)
    elif s == "rs":
        setst(ctx, "adm_rs")
        await q.answer()
        await aedit(update, "♻️ <b>Restore</b>\n\nOldin olingan <code>.db</code> faylni yuboring.\n⚠️ Joriy baza almashtiriladi!", IM([back()]))


async def do_broadcast(ctx, admin_chat, src_chat, src_msg):
    ok = bad = 0
    for r in rows("SELECT id FROM users WHERE banned=0 AND verified=1"):
        for _ in range(2):
            try:
                await ctx.bot.copy_message(r["id"], src_chat, src_msg)
                ok += 1
                break
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except Exception:
                bad += 1
                break
        await asyncio.sleep(0.05)
    await ctx.bot.send_message(admin_chat, f"📢 <b>Yuborish tugadi</b>\n✅ {ok} | ❌ {bad}", parse_mode=HTML)


async def adm_media(update, ctx, s):
    m = update.message
    if s["n"] == "adm_bc":
        ctx.user_data["bc"] = (m.chat_id, m.message_id)
        clrst(ctx)
        await say(update, "👆 Shu xabar hammaga yuborilsinmi?",
                  IM([[IB("✅ Yuborish", callback_data="a:bcgo"), IB("❌ Bekor", callback_data="a:home")]]))
    elif s["n"] == "adm_rs":
        if not m.document:
            return await say(update, "❌ .db fayl yuboring.")
        tmp = DB_PATH + ".new"
        f = await m.document.get_file()
        await f.download_to_drive(tmp)
        try:
            t = sqlite3.connect(tmp)
            t.execute("SELECT COUNT(*) FROM users")
            t.close()
        except Exception:
            os.remove(tmp)
            return await say(update, "❌ Noto'g'ri baza fayli.")
        db.close()
        shutil.move(tmp, DB_PATH)
        connect()
        clrst(ctx)
        await say(update, "✅ Baza tiklandi!", main_kb(update.effective_user.id))


def ucard(r):
    nm = esc(r["name"])
    un = "@" + esc(r["username"]) if r["username"] else "—"
    jd = datetime.fromtimestamp(r["joined"] or 0, TZ).strftime("%d.%m.%Y")
    return (f"👤 <b>{nm}</b> {un}\n🆔 <code>{r['id']}</code>\n📱 {r['phone'] or '—'}\n"
            f"💎 Balans: <b>{r['balance']}</b> (jami: {r['earned']})\n⭐ Ball: {r['points']} | 👥 Takliflar: {r['refs']}\n"
            f"🎮 FF ID: {esc(r['ff_id']) or '—'}\n🚫 Ban: {'ha' if r['banned'] else 'yoq'} | ✔️ Tasdiq: {'ha' if r['verified'] else 'yoq'}\n"
            f"📅 {jd} | Taklif qilgan: {r['ref_by'] or '—'}")


def ukb(r):
    uid = r["id"]
    return IM([[IB("✅ Unban" if r["banned"] else "🚫 Ban", callback_data=f"au:ban:{uid}"),
                IB("✉️ Xabar", callback_data=f"au:msg:{uid}")],
               [IB("💎 Almaz ±", callback_data=f"au:bal:{uid}"), IB("⭐ Ball ±", callback_data=f"au:pts:{uid}")],
               back()])


async def cb_au(update, ctx, a):
    q, act, uid = update.callback_query, a[1], int(a[2])
    r = get_user(uid)
    if not r:
        return await q.answer("Topilmadi", show_alert=True)
    if act == "ban":
        upd(uid, banned=0 if r["banned"] else 1)
        await q.answer("Bajarildi")
        r = get_user(uid)
        return await aedit(update, ucard(r), ukb(r))
    await q.answer()
    setst(ctx, "adm_umsg" if act == "msg" else "adm_uval", uid=uid, f=act)
    await say(update, "✉️ Xabar matnini yuboring:" if act == "msg" else "🔢 Qo'shish/ayirish miqdori (masalan: 50 yoki -20):")


async def st_adm_usr(update, ctx, s, t):
    t = t.strip().lstrip("@")
    r = get_user(int(t)) if t.isdigit() else one("SELECT * FROM users WHERE LOWER(username)=?", (t.lower(),))
    if not r:
        return await say(update, "❌ Foydalanuvchi topilmadi.")
    clrst(ctx)
    await say(update, ucard(r), ukb(r))


async def st_adm_uval(update, ctx, s, t):
    if not re.fullmatch(r"-?\d+", t.strip()):
        return await say(update, "❌ Butun son yuboring.")
    n = int(t)
    if s["f"] == "bal":
        credit(s["uid"], n)
    else:
        ex("UPDATE users SET points=CASE WHEN points+?<0 THEN 0 ELSE points+? END WHERE id=?", (n, n, s["uid"]))
    clrst(ctx)
    r = get_user(s["uid"])
    await say(update, "✅ Bajarildi\n\n" + ucard(r), ukb(r))


async def st_adm_umsg(update, ctx, s, t):
    clrst(ctx)
    try:
        await ctx.bot.send_message(s["uid"], t)
        await say(update, "✅ Yuborildi.")
    except Exception as e:
        await say(update, f"❌ Yuborilmadi: {esc(e)}")


async def cb_as(update, ctx, a):
    q, s = update.callback_query, a[1]
    keys = list(S.keys())
    if s == "l":
        pg = int(a[2])
        await q.answer()
        part = keys[pg * 8:pg * 8 + 8]
        kb = []
        for k in part:
            d, lab, tp = S[k]
            v = st(k)
            show = ("✅" if v == "1" else "❌") if tp == "bool" else (re.sub(r"<[^>]+>|\s+", " ", v)[:18] or "—")
            kb.append([IB(f"{lab}: {show}"[:60], callback_data=f"as:e:{k}")])
        nav = []
        if pg > 0:
            nav.append(IB("◀️", callback_data=f"as:l:{pg - 1}"))
        nav.append(IB(f"{pg + 1}/{(len(keys) + 7) // 8}", callback_data="as:l:0"))
        if (pg + 1) * 8 < len(keys):
            nav.append(IB("▶️", callback_data=f"as:l:{pg + 1}"))
        kb += [nav, back()]
        await aedit(update, "⚙️ <b>Sozlamalar</b>\nO'zgartirish uchun tanlang:", IM(kb))
    elif s == "e":
        k = a[2]
        d, lab, tp = S[k]
        if tp == "bool":
            set_st(k, "0" if stb(k) else "1")
            await q.answer("O'zgartirildi")
            return await cb_as(update, ctx, ["as", "l", str(keys.index(k) // 8)])
        await q.answer()
        setst(ctx, "adm_set", k=k)
        cur = st(k)
        await aedit(update, f"✏️ <b>{lab}</b>\n\nHozirgi qiymat:\n<code>{esc(cur[:2500])}</code>\n\n"
                            f"Yangi qiymatni yuboring.\n<i>Tozalash: -  | Asl holiga qaytarish: /default</i>",
                    IM([back(f"as:l:{keys.index(k) // 8}")]))


async def st_adm_set(update, ctx, s, t):
    k = s["k"]
    d, lab, tp = S[k]
    if t.strip() == "/default":
        ex("DELETE FROM settings WHERE k=?", (k,))
    else:
        v = "" if t.strip() == "-" else t
        if tp == "int" and not re.fullmatch(r"-?\d+", v.strip()):
            return await say(update, "❌ Butun son yuboring.")
        set_st(k, v.strip() if tp == "int" else v)
    clrst(ctx)
    await say(update, "✅ Saqlandi!", IM([[IB("⚙️ Sozlamalarga", callback_data=f"as:l:{list(S.keys()).index(k) // 8}")]]))


async def cb_ac(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "del":
        ex("DELETE FROM channels WHERE id=?", (int(a[2]),))
        SUBC.clear()
    if s == "add":
        setst(ctx, "adm_ch")
        return await aedit(update, "📣 Kanal @username yoki ID yuboring.\n⚠️ Bot kanalda <b>admin</b> bo'lishi shart!",
                           IM([back("ac:l")]))
    ch = rows("SELECT * FROM channels")
    await crud_list(update, "📣 <b>Majburiy obuna kanallari</b>",
                    [f"{c['id']}. {esc(c['title'])} — <code>{esc(c['chat_id'])}</code>" for c in ch],
                    [(c["title"], f"ac:del:{c['id']}") for c in ch], "ac:add")


async def st_adm_ch(update, ctx, s, t):
    t = t.strip()
    cid = int(t) if re.fullmatch(r"-?\d+", t) else (t if t.startswith("@") else "@" + t)
    try:
        chat = await ctx.bot.get_chat(cid)
    except Exception as e:
        return await say(update, f"❌ Kanal topilmadi: {esc(e)}")
    url = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
    if not url:
        try:
            url = await ctx.bot.export_chat_invite_link(chat.id)
        except Exception:
            url = ""
    ex("INSERT INTO channels(chat_id,title,url) VALUES(?,?,?)", (str(chat.id), chat.title or str(chat.id), url or ""))
    SUBC.clear()
    clrst(ctx)
    await say(update, f"✅ Qo'shildi: {esc(chat.title)}", IM([[IB("📣 Kanallar", callback_data="ac:l")]]))


async def cb_ap(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "del":
        ex("DELETE FROM promos WHERE code=?", (a[2],))
    if s == "add":
        setst(ctx, "adm_promo")
        return await aedit(update, "🎁 Format: <code>KOD MIQDOR LIMIT KUN</code>\nMasalan: <code>FF2026 10 100 7</code>\n"
                                   "(LIMIT 0 = cheksiz, KUN 0 = muddatsiz)", IM([back("ap:l")]))
    ps = rows("SELECT * FROM promos ORDER BY code LIMIT 30")
    ln = [f"<code>{esc(p['code'])}</code> — 💎{p['amount']} — {p['used']}/{p['max_uses'] or '∞'}"
          + (f" — {datetime.fromtimestamp(p['expires'], TZ):%d.%m}" if p["expires"] else "") for p in ps]
    await crud_list(update, "🎁 <b>Promo kodlar</b>", ln, [(p["code"], f"ap:del:{p['code']}") for p in ps], "ap:add")


async def st_adm_promo(update, ctx, s, t):
    m = re.fullmatch(r"(\S+)\s+(\d+)\s+(\d+)\s+(\d+)", t.strip())
    if not m:
        return await say(update, "❌ Format: KOD MIQDOR LIMIT KUN")
    code, amt, lim, days = m.group(1).upper(), int(m.group(2)), int(m.group(3)), int(m.group(4))
    ex("INSERT INTO promos(code,amount,max_uses,used,expires) VALUES(?,?,?,0,?) ON CONFLICT(code) DO UPDATE SET "
       "amount=excluded.amount, max_uses=excluded.max_uses, used=0, expires=excluded.expires",
       (code, amt, lim, ts() + days * 86400 if days else 0))
    clrst(ctx)
    await say(update, f"✅ Promo yaratildi: <code>{esc(code)}</code>", IM([[IB("🎁 Promolar", callback_data="ap:l")]]))


async def cb_ar(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "del":
        ex("DELETE FROM prizes WHERE id=?", (int(a[2]),))
    if s == "add":
        setst(ctx, "adm_prize")
        return await aedit(update, "🎰 Format: <code>MIQDOR VAZN</code>\nMasalan: <code>5 10</code>", IM([back("ar:l")]))
    ps = rows("SELECT * FROM prizes ORDER BY amount")
    tot = sum(p["weight"] for p in ps) or 1
    await crud_list(update, "🎰 <b>Spin sovrinlari</b>",
                    [f"💎 {p['amount']} — vazn {p['weight']:g} ({p['weight'] / tot * 100:.1f}%)" for p in ps],
                    [(f"{p['amount']} 💎 ({p['weight']:g})", f"ar:del:{p['id']}") for p in ps], "ar:add")


async def st_adm_prize(update, ctx, s, t):
    m = re.fullmatch(r"(\d+)\s+(\d+(?:\.\d+)?)", t.strip())
    if not m:
        return await say(update, "❌ Format: MIQDOR VAZN")
    ex("INSERT INTO prizes(amount,weight) VALUES(?,?)", (int(m.group(1)), float(m.group(2))))
    clrst(ctx)
    await say(update, "✅ Qo'shildi", IM([[IB("🎰 Sovrinlar", callback_data="ar:l")]]))


async def cb_at(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "del":
        ex("DELETE FROM tasks WHERE id=?", (int(a[2]),))
    if s == "add":
        setst(ctx, "adm_task")
        return await aedit(update, "✅ Format: <code>Sarlavha | URL | @kanal (ixtiyoriy)</code>", IM([back("at:l")]))
    ts_ = rows("SELECT * FROM tasks")
    await crud_list(update, "✅ <b>Bonus tasklar</b>", [f"{t['id']}. {esc(t['title'])} — {esc(t['url'])}" for t in ts_],
                    [(t["title"], f"at:del:{t['id']}") for t in ts_], "at:add")


async def st_adm_task(update, ctx, s, t):
    p = [x.strip() for x in t.split("|")]
    if len(p) < 2 or not p[1].startswith("http"):
        return await say(update, "❌ Format: Sarlavha | https://... | @kanal")
    ex("INSERT INTO tasks(title,url,chat_id) VALUES(?,?,?)", (p[0], p[1], p[2] if len(p) > 2 else ""))
    clrst(ctx)
    await say(update, "✅ Task qo'shildi", IM([[IB("✅ Tasklar", callback_data="at:l")]]))


async def cb_ae(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "l":
        return await aedit(update, "🛒 <b>Do'kon / Xizmatlar</b>\nKategoriyani tanlang:",
                           IM([[IB(v, callback_data=f"ae:c:{k}")] for k, v in CATS.items()] + [back()]))
    if s == "c":
        cat = a[2]
        its = rows("SELECT * FROM items WHERE cat=? ORDER BY id", (cat,))
        kb = [[IB(f"{'✅' if i['active'] else '🚫'} {i['name']} — {i['price']}💎"[:60], callback_data=f"ae:v:{i['id']}")]
              for i in its]
        return await aedit(update, f"<b>{CATS[cat]}</b>",
                           IM(kb + [[IB("➕ Qo'shish", callback_data=f"ae:add:{cat}")], back("ae:l")]))
    if s == "add":
        setst(ctx, "adm_item_add", cat=a[2])
        return await aedit(update, "➕ Format: <code>Nomi | Narx | Tavsif</code>", IM([back(f"ae:c:{a[2]}")]))
    i = one("SELECT * FROM items WHERE id=?", (int(a[2]),)) if len(a) > 2 and a[2].isdigit() else None
    if s == "v" and i:
        return await aedit(update, f"<b>{esc(i['name'])}</b>\n\n{esc(i['descr'])}\n\n💎 {i['price']} | "
                                   f"{'faol' if i['active'] else 'o‘chiq'}\nKategoriya: {CATS[i['cat']]}",
                           IM([[IB("✏️ Nomi", callback_data=f"ae:ed:name:{i['id']}"),
                                IB("✏️ Narx", callback_data=f"ae:ed:price:{i['id']}")],
                               [IB("✏️ Tavsif", callback_data=f"ae:ed:descr:{i['id']}"),
                                IB("👁 Yoq/O'ch", callback_data=f"ae:tog:{i['id']}")],
                               [IB("🗑 O'chirish", callback_data=f"ae:del:{i['id']}")], back(f"ae:c:{i['cat']}")]))
    if s == "tog" and i:
        ex("UPDATE items SET active=1-active WHERE id=?", (i["id"],))
        return await cb_ae(update, ctx, ["ae", "v", str(i["id"])])
    if s == "del" and i:
        ex("DELETE FROM items WHERE id=?", (i["id"],))
        return await cb_ae(update, ctx, ["ae", "c", i["cat"]])
    if s == "ed":
        setst(ctx, "adm_item_ed", f=a[2], id=int(a[3]))
        await say(update, "✏️ Yangi qiymatni yuboring:")


async def st_adm_item_add(update, ctx, s, t):
    p = [x.strip() for x in t.split("|")]
    if len(p) < 2 or not p[1].isdigit():
        return await say(update, "❌ Format: Nomi | Narx | Tavsif")
    ex("INSERT INTO items(cat,name,descr,price) VALUES(?,?,?,?)",
       (s["cat"], p[0], p[2] if len(p) > 2 else "", int(p[1])))
    clrst(ctx)
    await say(update, "✅ Qo'shildi", IM([[IB("🛒 Ro'yxat", callback_data=f"ae:c:{s['cat']}")]]))


async def st_adm_item_ed(update, ctx, s, t):
    f = s["f"]
    if f == "price":
        if not t.strip().isdigit():
            return await say(update, "❌ Raqam yuboring.")
        ex("UPDATE items SET price=? WHERE id=?", (int(t), s["id"]))
    else:
        ex(f"UPDATE items SET {'name' if f == 'name' else 'descr'}=? WHERE id=?", (t.strip(), s["id"]))
    clrst(ctx)
    await say(update, "✅ Saqlandi", IM([[IB("📦 Mahsulot", callback_data=f"ae:v:{s['id']}")]]))


async def cb_al(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "del":
        ex("DELETE FROM leagues WHERE id=?", (int(a[2]),))
    if s == "add":
        setst(ctx, "adm_lg")
        return await aedit(update, "🏅 Format: <code>Nom | emoji | minimal ball</code>", IM([back("al:l")]))
    ls = rows("SELECT * FROM leagues ORDER BY min_points")
    await crud_list(update, "🏅 <b>Ligalar</b>", [f"{l['emoji']} {esc(l['name'])} — {l['min_points']} ball" for l in ls],
                    [(l["name"], f"al:del:{l['id']}") for l in ls], "al:add")


async def st_adm_lg(update, ctx, s, t):
    p = [x.strip() for x in t.split("|")]
    if len(p) != 3 or not p[2].isdigit():
        return await say(update, "❌ Format: Nom | emoji | ball")
    ex("INSERT INTO leagues(name,emoji,min_points) VALUES(?,?,?)", (p[0], p[1], int(p[2])))
    clrst(ctx)
    await say(update, "✅ Qo'shildi", IM([[IB("🏅 Ligalar", callback_data="al:l")]]))


async def cb_aa(update, ctx, a):
    q, s = update.callback_query, a[1]
    await q.answer()
    if s == "del":
        ex("DELETE FROM admins WHERE id=?", (int(a[2]),))
    if s == "add":
        setst(ctx, "adm_adm")
        return await aedit(update, "🛡 Yangi admin Telegram ID sini yuboring:", IM([back("aa:l")]))
    ad = rows("SELECT id FROM admins")
    ln = [f"👑 <code>{i}</code> (asosiy)" for i in sorted(ENV_ADMINS)] + [f"🛡 <code>{r['id']}</code>" for r in ad]
    await crud_list(update, "🛡 <b>Adminlar</b>", ln, [(str(r["id"]), f"aa:del:{r['id']}") for r in ad], "aa:add")


async def st_adm_adm(update, ctx, s, t):
    if not t.strip().isdigit():
        return await say(update, "❌ Faqat raqamli ID.")
    ex("INSERT INTO admins(id) VALUES(?) ON CONFLICT DO NOTHING", (int(t),))
    clrst(ctx)
    await say(update, "✅ Admin qo'shildi", IM([[IB("🛡 Adminlar", callback_data="aa:l")]]))


# ───────────────────────── ROUTER ─────────────────────────
MENU = {
    B_NAST: nast_menu, B_ALMAZ: almaz_menu, B_AI: ai_menu, B_ADMIN: admin_panel,
    B_EARN: earn, B_PROMO: promo_menu, B_SPIN: spin_menu, B_BOXMENU: box_menu, B_ZAR: zar_menu,
    B_GUESS: guess_menu, B_PARTNER: partner_menu, B_TOP: top, B_PROF: profile, B_LVL: level_menu,
    B_SHOP: shop_menu, B_YT: yt_menu, B_HORROR: horror_menu,
    L_SPIN: spin_choose, L_MYSPIN: my_spins, L_BONUS: bonus_menu, L_PHIST: promo_hist,
    L_FIND: partner_find, L_AD: ad_start, L_PASS: passport, L_GUIDE: guide,
    L_HELP: help_start, L_AICHAT: ai_chat_start, L_AICHAR: ai_char_start,
    L_AINICK: ai_nick_start, L_AISENS: phone_menu,
    L_SVC: cat_handler("service"), L_MYORD: my_orders,
    L_FACT: fact_send, L_STORY: story_send, L_CURSE: curse_send,
}
for _k, _v in CATS.items():
    if _k != "service":
        MENU[_v] = cat_handler(_k)

STATES = {
    "promo": st_promo, "phone": st_phone, "ai_chat": st_ai_chat, "ai_help": st_ai_help,
    "ai_charpick": st_ai_charpick, "ai_char": st_ai_char, "ai_nick": st_ai_nick,
    "pp_level": st_pp_level, "pp_bio": st_pp_bio, "ff_id": st_ff_id, "ad_mode": st_ad_mode,
    "wd_amount": st_wd, "svc_note": st_svc_note, "shop_ffid": st_shop_ffid, "adm_usr": st_adm_usr,
    "adm_uval": st_adm_uval, "adm_umsg": st_adm_umsg, "adm_set": st_adm_set, "adm_ch": st_adm_ch,
    "adm_promo": st_adm_promo, "adm_prize": st_adm_prize, "adm_task": st_adm_task,
    "adm_item_add": st_adm_item_add, "adm_item_ed": st_adm_item_ed, "adm_lg": st_adm_lg,
    "adm_adm": st_adm_adm, "adm_nbrand": st_adm_nbrand, "adm_nmodel": st_adm_nmodel,
    "adm_npadd": st_adm_npadd, "adm_npedit": st_adm_npedit,
}

CB = {"cap": cb_cap, "sub": cb_sub, "spin": cb_spin, "bonus": cb_bonus, "ptr": cb_ptr, "pp": cb_pp,
      "prof": cb_prof, "lvl": cb_lvl, "it": cb_item, "cat": cb_cat, "buy": cb_buy, "buyok": cb_buyok,
      "x": cb_x, "ord": cb_ord, "wd": cb_wd, "a": cb_a, "as": cb_as, "ac": cb_ac, "ap": cb_ap,
      "ar": cb_ar, "at": cb_at, "ae": cb_ae, "al": cb_al, "aa": cb_aa, "au": cb_au,
      "bx": cb_bx, "zt": cb_zt, "gs": cb_gs, "gm": cb_gm,
      "nst": cb_nst, "nb": cb_nb, "nm": cb_nm, "np": cb_np, "nref": cb_nref, "nhelp": cb_nhelp,
      "ncust": cb_ncust, "nai": cb_nai, "na": cb_na}
ADMIN_CB = {"ord", "wd", "a", "as", "ac", "ap", "ar", "at", "ae", "al", "aa", "au", "na"}


async def route_text(update, ctx, t):
    """Pastki tugmalar va matnli xabarlar shu yerda ishlaydi."""
    uid = update.effective_user.id
    if not await gate(update, ctx):
        return
    if t == B_BACK:
        return await home(update, ctx)
    s = getst(ctx)
    if t in MENU:
        if t == B_ADMIN and not is_admin(uid):
            return
        clrst(ctx)
        return await MENU[t](update, ctx)
    if s and s["n"] in STATES:
        if s["n"].startswith("adm_") and not is_admin(uid):
            return clrst(ctx)
        return await STATES[s["n"]](update, ctx, s, t)
    await say(update, "Menyudan tanlang 👇", main_kb(uid))


async def on_msg(update, ctx):
    m = update.effective_message
    if m is None or update.effective_user is None:
        return
    uid = update.effective_user.id
    if m.contact:
        return await on_contact(update, ctx)
    s = getst(ctx)
    if s and s["n"] in ("adm_bc", "adm_rs") and is_admin(uid):
        return await adm_media(update, ctx, s)
    if m.text:
        return await route_text(update, ctx, m.text)


async def on_cb(update, ctx):
    q = update.callback_query
    data = q.data or ""
    if data.startswith("t:"):
        await q.answer()
        try:
            ensure_user(q.from_user)
            await route_text(update, ctx, data[2:])
        except Exception:
            log.exception("tugma xato: %s", data)
        return
    a = data.split(":")
    h = CB.get(a[0])
    uid = q.from_user.id
    if not h:
        return await q.answer()
    try:
        if a[0] in ADMIN_CB and not is_admin(uid):
            return await q.answer("⛔ Ruxsat yo'q", show_alert=True)
        if a[0] not in ("cap", "sub") and not is_admin(uid):
            r = get_user(uid)
            if not r or r["banned"] or not r["verified"] or not stb("bot_enabled"):
                return await q.answer("⛔ Avval /start bosing", show_alert=True)
        await h(update, ctx, a)
    except Exception:
        log.exception("callback xatosi: %s", data)
    try:
        await q.answer()
    except Exception:
        pass


async def menu_cmd(update, ctx):
    if await gate(update, ctx):
        await home(update, ctx)


async def on_error(update, ctx):
    log.error("Xato: %s", ctx.error, exc_info=ctx.error)


# ───────────────────────── AVTO-BACKUP (Telegram kanal) ─────────────────────────
_bk = {"ok": False, "changes": -1, "msg": None}


def _bcid():
    return int(BACKUP_CHAT) if BACKUP_CHAT.lstrip("-").isdigit() else BACKUP_CHAT


async def make_backup(bot, force=False):
    if not BACKUP_CHAT or not _bk["ok"] or IS_PG:
        return
    ch = db.total_changes
    if not force and ch == _bk["changes"]:
        return
    path = tempfile.mktemp(suffix=".db")
    try:
        dst = sqlite3.connect(path)
        db.backup(dst)
        dst.close()
        with open(path, "rb") as f:
            m = await bot.send_document(_bcid(), f, filename=f"backup_{now():%Y%m%d_%H%M}.db",
                                        caption="💾 Avto-backup", disable_notification=True)
        try:
            await bot.pin_chat_message(_bcid(), m.message_id, disable_notification=True)
        except Exception as e:
            log.warning("pin xatosi (botga pin huquqi bering): %s", e)
        if _bk["msg"]:
            try:
                await bot.delete_message(_bcid(), _bk["msg"])
            except Exception:
                pass
        _bk.update(changes=ch, msg=m.message_id)
    except Exception as e:
        log.warning("backup xatosi: %s", e)
    finally:
        if os.path.exists(path):
            os.remove(path)


async def try_restore(bot):
    """True = tayyor. False = xato, qayta uriniladi."""
    try:
        chat = await bot.get_chat(_bcid())
        pm = chat.pinned_message
        if not pm or not pm.document:
            return True
        if one("SELECT COUNT(*) FROM users")[0] > 0:
            _bk["msg"] = pm.message_id
            return True
        tmp = DB_PATH + ".new"
        f = await pm.document.get_file()
        await f.download_to_drive(tmp)
        t = sqlite3.connect(tmp)
        t.execute("SELECT COUNT(*) FROM users")
        t.close()
        db.close()
        shutil.move(tmp, DB_PATH)
        connect()
        _bk["msg"] = pm.message_id
        log.info("Baza Telegram backupdan tiklandi")
        return True
    except Exception as e:
        log.warning("restore xatosi: %s", e)
        return False


async def backup_loop(app):
    while True:
        if not _bk["ok"]:
            _bk["ok"] = await try_restore(app.bot)
        await make_backup(app.bot)
        await asyncio.sleep(300)


async def post_init(app):
    me = await app.bot.get_me()
    BOT["username"] = me.username or ""
    if IS_PG:
        log.info("Postgres (Neon) ishlatilmoqda — ma'lumotlar doimiy.")
        return
    if not BACKUP_CHAT:
        log.warning("BACKUP_CHAT berilmagan — redeployda baza o'chadi!")
        return
    _bk["ok"] = await try_restore(app.bot)
    app.bot_data["bk_task"] = asyncio.create_task(backup_loop(app))


async def post_stop(app):
    await make_backup(app.bot, force=True)


# ───────────────────────── WEB (Render keep-alive) ─────────────────────────
web = Flask(__name__)


@web.route("/")
def index():
    return "KAROCHI ishlayapti 🔥"


def run_web():
    web.run(host="0.0.0.0", port=PORT)


def keepalive():
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        time.sleep(600)
        try:
            httpx.get(url, timeout=20)
        except Exception:
            pass


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi!")
    connect()
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keepalive, daemon=True).start()
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())  # Python 3.14 uchun
    app = (Application.builder().token(BOT_TOKEN)
           .connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)
           .get_updates_connect_timeout(30).get_updates_read_timeout(30)
           .get_updates_write_timeout(30).get_updates_pool_timeout(30)
           .post_init(post_init).post_stop(post_stop).build())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, on_msg))
    app.add_error_handler(on_error)
    log.info("KAROCHI ishga tushdi 🔥")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
