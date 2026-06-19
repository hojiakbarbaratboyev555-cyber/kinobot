import asyncio
import random
import logging
import os

import aiosqlite
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Update

# ================= CONFIG =================

BOT_TOKEN = "8759475620:AAGYtzehxNQlFGPXBS_nfu76vbunbDmG9R0"

GROUP_ID = -5587260606
CHANNEL_ID = -1003869575908  # majburiy obuna kanal

WEBHOOK_HOST = "https://kinobot-0yka.onrender.com"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

DB = "bot.db"
PORT = int(os.environ.get("PORT", 10000))

# ================= INIT =================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# vaqtincha serial storage
serial_temp = {}

# ================= DB =================

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS content (
            code TEXT PRIMARY KEY,
            message_id INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
        """)
        await db.commit()

async def add_user(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
        await db.commit()

async def get_users():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT user_id FROM users")
        return await cur.fetchall()

# ================= SUB CHECK =================

async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= START =================

@dp.message(F.text == "/start")
async def start(m: types.Message):
    await add_user(m.from_user.id)

    if not await check_sub(m.from_user.id):
        return await m.answer(
            "📢 Kanalga obuna bo‘ling!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📢 Kanal", url="https://t.me/yourchannel")],
                [types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check")]
            ])
        )

    await m.answer("🎬 Kino botga xush kelibsiz!\nKod yuboring.")

# ================= CHECK BUTTON =================

@dp.callback_query(F.data == "check")
async def check(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Obuna tasdiqlandi!\nKod yuboring.")
    else:
        await call.answer("❌ Obuna yo‘q", show_alert=True)

# ================= GROUP HANDLER =================

@dp.message(F.chat.id == GROUP_ID)
async def group(m: types.Message):

    if not m.reply_to_message:
        return

    text = m.text or ""

    # 🎬 KINO
    if text == "/kino":
        code = str(random.randint(1000, 9999))

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO content VALUES(?,?)",
                (code, m.reply_to_message.message_id)
            )
            await db.commit()

        await m.reply(f"🎬 Kod: {code}")

    # 📺 SERIAL START
    elif text == "/serial":
        code = str(random.randint(1000, 9999))

        serial_temp[m.from_user.id] = {
            "code": code,
            "start_id": m.reply_to_message.message_id
        }

        await m.reply(f"📺 Serial boshlandi: {code}")

    # 📺 SERIAL END
    elif text == "/end":
        data = serial_temp.get(m.from_user.id)

        if not data:
            return await m.reply("❌ Serial topilmadi")

        code = data["code"]

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO content VALUES(?,?)",
                (code, data["start_id"])
            )
            await db.commit()

        serial_temp.pop(m.from_user.id, None)

        await m.reply(f"✅ Serial yakunlandi!\n📺 Kod: {code}")

    # ➕ SERIAL EXTEND
    elif text.startswith("/serial "):
        code = text.split()[1]

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE content SET message_id=? WHERE code=?",
                (m.reply_to_message.message_id, code)
            )
            await db.commit()

        await m.reply(f"➕ Serial davom etdi: {code}")

    # ❌ DELETE
    elif text.startswith("/unkino"):
        code = text.split()[1]

        async with aiosqlite.connect(DB) as db:
            await db.execute("DELETE FROM content WHERE code=?", (code,))
            await db.commit()

        await m.reply("❌ O‘chirildi")

    # 📣 ALL
    elif text == "/all":
        users = await get_users()

        for u in users:
            try:
                await bot.copy_message(
                    u[0],
                    GROUP_ID,
                    m.reply_to_message.message_id,
                    protect_content=True
                )
            except:
                pass

    # 👤 SEND TO USER
    elif text.startswith("/"):
        try:
            uid = int(text.replace("/", ""))
            await bot.copy_message(
                uid,
                GROUP_ID,
                m.reply_to_message.message_id,
                protect_content=True
            )
        except:
            pass

# ================= USER SEND CODE =================

@dp.message()
async def send(m: types.Message):

    if not m.text:
        return

    if not await check_sub(m.from_user.id):
        return await m.answer("📢 Kanalga obuna bo‘ling!")

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT message_id FROM content WHERE code=?",
            (m.text.strip(),)
        )
        row = await cur.fetchone()

    if row:
        await bot.copy_message(
            m.chat.id,
            GROUP_ID,
            row[0],
            protect_content=True
        )
    else:
        await m.answer("❌ Kod topilmadi")

# ================= FASTAPI =================

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/")
async def home():
    return {"status": "running"}

# ================= RUN =================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
